import AsyncStorage from '@react-native-async-storage/async-storage';
import PushNotification from 'react-native-push-notification';

class RainCheckService {
  constructor() {
    this.apiBaseUrl = 'http://your-backend-url:8000'; // Update with your actual backend URL
  }

  async checkRainConditions() {
    try {
      // Load user settings
      const settings = await AsyncStorage.getItem('commuteSettings');
      if (!settings) {
        console.log('No commute settings found');
        return;
      }

      const { homeAddress, workAddress, morningCommute, eveningCommute } = JSON.parse(settings);
      
      if (!homeAddress || !workAddress) {
        console.log('Home or work address not set');
        return;
      }

      // Determine if this is morning or evening check based on current time
      const now = new Date();
      const currentHour = now.getHours();
      const currentMinute = now.getMinutes();
      const currentTime = currentHour * 60 + currentMinute;

      const morningTime = morningCommute.time.getHours() * 60 + morningCommute.time.getMinutes();
      const eveningTime = eveningCommute.time.getHours() * 60 + eveningCommute.time.getMinutes();

      let isMorningCheck = false;
      let isEveningCheck = false;

      // Check if we're within 30 minutes of morning commute
      if (morningCommute.enabled && Math.abs(currentTime - morningTime) <= 30) {
        isMorningCheck = true;
      }

      // Check if we're within 30 minutes of evening commute
      if (eveningCommute.enabled && Math.abs(currentTime - eveningTime) <= 30) {
        isEveningCheck = true;
      }

      if (!isMorningCheck && !isEveningCheck) {
        console.log('Not within commute time window');
        return;
      }

      // Call the backend API
      const response = await fetch(`${this.apiBaseUrl}/check_rain/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user: 'mobile_user', // You can customize this
          home: homeAddress,
          work: workAddress,
          vehicle: 'bike'
        })
      });

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }

      const data = await response.json();
      
      // Send appropriate notification
      this.sendRainNotification(data, isMorningCheck, isEveningCheck);

    } catch (error) {
      console.error('Error checking rain conditions:', error);
      this.sendErrorNotification(error.message);
    }
  }

  sendRainNotification(data, isMorningCheck, isEveningCheck) {
    const { will_rain, weather_condition } = data;
    const commuteType = isMorningCheck ? 'morning' : 'evening';
    
    let title, message, soundName, color;

    if (will_rain) {
      title = '🌧️ Rain Alert!';
      message = `${commuteType.charAt(0).toUpperCase() + commuteType.slice(1)} commute: ${weather_condition}`;
      soundName = 'default';
      color = '#FF5722'; // Red color for rain alert
    } else {
      title = '✅ Clear Weather';
      message = `${commuteType.charAt(0).toUpperCase() + commuteType.slice(1)} commute: No rain expected!`;
      soundName = 'default';
      color = '#4CAF50'; // Green color for clear weather
    }

    PushNotification.localNotification({
      title: title,
      message: message,
      playSound: true,
      soundName: soundName,
      color: color,
      largeIcon: 'ic_launcher',
      smallIcon: 'ic_notification',
      actions: ['View Details', 'Dismiss'],
      invokeApp: true,
    });

    // Schedule a follow-up notification 10 minutes later as a reminder
    const reminderTime = new Date();
    reminderTime.setMinutes(reminderTime.getMinutes() + 10);

    PushNotification.localNotificationSchedule({
      title: `⏰ ${commuteType.charAt(0).toUpperCase() + commuteType.slice(1)} Commute Reminder`,
      message: will_rain ? 'Don\'t forget your rain gear!' : 'Have a great commute!',
      date: reminderTime,
      playSound: true,
      soundName: 'default',
    });
  }

  sendErrorNotification(errorMessage) {
    PushNotification.localNotification({
      title: '⚠️ MotoRain Error',
      message: `Failed to check weather: ${errorMessage}`,
      playSound: true,
      soundName: 'default',
      color: '#FF9800',
    });
  }

  async scheduleBackgroundChecks() {
    try {
      const settings = await AsyncStorage.getItem('commuteSettings');
      if (!settings) return;

      const { commuteDays, morningCommute, eveningCommute } = JSON.parse(settings);
      
      // Clear existing notifications
      PushNotification.cancelAllLocalNotifications();

      // Schedule morning checks
      if (morningCommute.enabled) {
        const morningCheckTime = new Date(morningCommute.time);
        morningCheckTime.setMinutes(morningCheckTime.getMinutes() - 30); // 30 minutes before commute

        // Schedule for each enabled day
        Object.entries(commuteDays).forEach(([day, enabled]) => {
          if (enabled) {
            const dayIndex = this.getDayIndex(day);
            const scheduledTime = new Date(morningCheckTime);
            scheduledTime.setDate(scheduledTime.getDate() + (dayIndex - scheduledTime.getDay() + 7) % 7);

            PushNotification.localNotificationSchedule({
              id: `morning_${day}`,
              title: '🌤️ Checking Morning Weather',
              message: 'Checking rain conditions for your morning commute...',
              date: scheduledTime,
              repeatType: 'week',
              repeatTime: scheduledTime,
              playSound: false, // Silent notification for the check
            });
          }
        });
      }

      // Schedule evening checks
      if (eveningCommute.enabled) {
        const eveningCheckTime = new Date(eveningCommute.time);
        eveningCheckTime.setMinutes(eveningCheckTime.getMinutes() - 30); // 30 minutes before commute

        // Schedule for each enabled day
        Object.entries(commuteDays).forEach(([day, enabled]) => {
          if (enabled) {
            const dayIndex = this.getDayIndex(day);
            const scheduledTime = new Date(eveningCheckTime);
            scheduledTime.setDate(scheduledTime.getDate() + (dayIndex - scheduledTime.getDay() + 7) % 7);

            PushNotification.localNotificationSchedule({
              id: `evening_${day}`,
              title: '🌤️ Checking Evening Weather',
              message: 'Checking rain conditions for your evening commute...',
              date: scheduledTime,
              repeatType: 'week',
              repeatTime: scheduledTime,
              playSound: false, // Silent notification for the check
            });
          }
        });
      }

      console.log('Background rain checks scheduled successfully');
    } catch (error) {
      console.error('Error scheduling background checks:', error);
    }
  }

  getDayIndex(day) {
    const dayMap = {
      sunday: 0,
      monday: 1,
      tuesday: 2,
      wednesday: 3,
      thursday: 4,
      friday: 5,
      saturday: 6,
    };
    return dayMap[day];
  }

  // Method to be called by background task
  async performBackgroundRainCheck() {
    console.log('Performing background rain check...');
    await this.checkRainConditions();
  }
}

export default new RainCheckService();
