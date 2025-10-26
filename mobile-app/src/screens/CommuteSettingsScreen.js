import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  Switch,
  Platform,
  PermissionsAndroid,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import PushNotification from 'react-native-push-notification';
import { Calendar } from 'react-native-calendar-picker';
import DateTimePicker from '@react-native-community/datetimepicker';

const CommuteSettingsScreen = () => {
  const [commuteDays, setCommuteDays] = useState({
    monday: true,
    tuesday: true,
    wednesday: true,
    thursday: true,
    friday: true,
    saturday: false,
    sunday: false,
  });

  const [morningCommute, setMorningCommute] = useState({
    enabled: true,
    time: new Date(2024, 0, 1, 8, 0), // 8:00 AM default
  });

  const [eveningCommute, setEveningCommute] = useState({
    enabled: true,
    time: new Date(2024, 0, 1, 17, 30), // 5:30 PM default
  });

  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [homeAddress, setHomeAddress] = useState('');
  const [workAddress, setWorkAddress] = useState('');

  const [showMorningPicker, setShowMorningPicker] = useState(false);
  const [showEveningPicker, setShowEveningPicker] = useState(false);

  useEffect(() => {
    loadSettings();
    requestNotificationPermission();
  }, []);

  const loadSettings = async () => {
    try {
      const settings = await AsyncStorage.getItem('commuteSettings');
      if (settings) {
        const parsedSettings = JSON.parse(settings);
        setCommuteDays(parsedSettings.commuteDays || commuteDays);
        setMorningCommute(parsedSettings.morningCommute || morningCommute);
        setEveningCommute(parsedSettings.eveningCommute || eveningCommute);
        setNotificationsEnabled(parsedSettings.notificationsEnabled !== false);
        setHomeAddress(parsedSettings.homeAddress || '');
        setWorkAddress(parsedSettings.workAddress || '');
      }
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  const saveSettings = async () => {
    try {
      const settings = {
        commuteDays,
        morningCommute,
        eveningCommute,
        notificationsEnabled,
        homeAddress,
        workAddress,
      };
      await AsyncStorage.setItem('commuteSettings', JSON.stringify(settings));
      Alert.alert('Success', 'Settings saved successfully!');
    } catch (error) {
      console.error('Error saving settings:', error);
      Alert.alert('Error', 'Failed to save settings');
    }
  };

  const requestNotificationPermission = async () => {
    if (Platform.OS === 'android') {
      try {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS,
        );
        if (granted === PermissionsAndroid.RESULTS.GRANTED) {
          console.log('Notification permission granted');
        }
      } catch (err) {
        console.warn(err);
      }
    }

    PushNotification.configure({
      onRegister: function (token) {
        console.log('TOKEN:', token);
      },
      onNotification: function (notification) {
        console.log('NOTIFICATION:', notification);
      },
      permissions: {
        alert: true,
        badge: true,
        sound: true,
      },
      popInitialNotification: true,
      requestPermissions: true,
    });
  };

  const toggleDay = (day) => {
    setCommuteDays(prev => ({
      ...prev,
      [day]: !prev[day]
    }));
  };

  const formatTime = (date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const scheduleRainCheck = async () => {
    // This will be implemented to schedule background rain checks
    // before each commute time
    console.log('Scheduling rain checks for commute times...');
    
    const morningTime = morningCommute.time;
    const eveningTime = eveningCommute.time;
    
    // Schedule morning check (30 minutes before commute)
    if (morningCommute.enabled) {
      const morningCheckTime = new Date(morningTime);
      morningCheckTime.setMinutes(morningCheckTime.getMinutes() - 30);
      
      // Schedule notification
      PushNotification.localNotificationSchedule({
        message: "Checking rain conditions for your morning commute...",
        date: morningCheckTime,
        repeatType: 'week',
        repeatTime: morningCheckTime,
      });
    }
    
    // Schedule evening check (30 minutes before commute)
    if (eveningCommute.enabled) {
      const eveningCheckTime = new Date(eveningTime);
      eveningCheckTime.setMinutes(eveningCheckTime.getMinutes() - 30);
      
      // Schedule notification
      PushNotification.localNotificationSchedule({
        message: "Checking rain conditions for your evening commute...",
        date: eveningCheckTime,
        repeatType: 'week',
        repeatTime: eveningCheckTime,
      });
    }
  };

  const testNotification = () => {
    PushNotification.localNotification({
      title: "MotoRain Test",
      message: "This is a test notification!",
      playSound: true,
      soundName: 'default',
    });
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Commute Settings</Text>
      
      {/* Commute Days */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Work Days</Text>
        {Object.entries(commuteDays).map(([day, enabled]) => (
          <View key={day} style={styles.dayRow}>
            <Text style={styles.dayText}>
              {day.charAt(0).toUpperCase() + day.slice(1)}
            </Text>
            <Switch
              value={enabled}
              onValueChange={() => toggleDay(day)}
              trackColor={{ false: '#767577', true: '#81b0ff' }}
              thumbColor={enabled ? '#f5dd4b' : '#f4f3f4'}
            />
          </View>
        ))}
      </View>

      {/* Morning Commute */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Morning Commute</Text>
        <View style={styles.timeRow}>
          <Switch
            value={morningCommute.enabled}
            onValueChange={(value) => setMorningCommute(prev => ({ ...prev, enabled: value }))}
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={morningCommute.enabled ? '#f5dd4b' : '#f4f3f4'}
          />
          <TouchableOpacity
            style={styles.timeButton}
            onPress={() => setShowMorningPicker(true)}
            disabled={!morningCommute.enabled}
          >
            <Text style={[
              styles.timeText,
              !morningCommute.enabled && styles.disabledText
            ]}>
              {formatTime(morningCommute.time)}
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Evening Commute */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Evening Commute</Text>
        <View style={styles.timeRow}>
          <Switch
            value={eveningCommute.enabled}
            onValueChange={(value) => setEveningCommute(prev => ({ ...prev, enabled: value }))}
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={eveningCommute.enabled ? '#f5dd4b' : '#f4f3f4'}
          />
          <TouchableOpacity
            style={styles.timeButton}
            onPress={() => setShowEveningPicker(true)}
            disabled={!eveningCommute.enabled}
          >
            <Text style={[
              styles.timeText,
              !eveningCommute.enabled && styles.disabledText
            ]}>
              {formatTime(eveningCommute.time)}
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Notifications */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Notifications</Text>
        <View style={styles.dayRow}>
          <Text style={styles.dayText}>Enable Rain Alerts</Text>
          <Switch
            value={notificationsEnabled}
            onValueChange={setNotificationsEnabled}
            trackColor={{ false: '#767577', true: '#81b0ff' }}
            thumbColor={notificationsEnabled ? '#f5dd4b' : '#f4f3f4'}
          />
        </View>
      </View>

      {/* Action Buttons */}
      <View style={styles.buttonContainer}>
        <TouchableOpacity style={styles.saveButton} onPress={saveSettings}>
          <Text style={styles.buttonText}>Save Settings</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.testButton} onPress={testNotification}>
          <Text style={styles.buttonText}>Test Notification</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.scheduleButton} onPress={scheduleRainCheck}>
          <Text style={styles.buttonText}>Schedule Rain Checks</Text>
        </TouchableOpacity>
      </View>

      {/* Date/Time Pickers */}
      {showMorningPicker && (
        <DateTimePicker
          value={morningCommute.time}
          mode="time"
          is24Hour={true}
          display="default"
          onChange={(event, selectedTime) => {
            setShowMorningPicker(false);
            if (selectedTime) {
              setMorningCommute(prev => ({ ...prev, time: selectedTime }));
            }
          }}
        />
      )}

      {showEveningPicker && (
        <DateTimePicker
          value={eveningCommute.time}
          mode="time"
          is24Hour={true}
          display="default"
          onChange={(event, selectedTime) => {
            setShowEveningPicker(false);
            if (selectedTime) {
              setEveningCommute(prev => ({ ...prev, time: selectedTime }));
            }
          }}
        />
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
    color: '#333',
  },
  section: {
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 15,
    marginBottom: 15,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#333',
  },
  dayRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  dayText: {
    fontSize: 16,
    color: '#333',
  },
  timeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  timeButton: {
    backgroundColor: '#e0e0e0',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  timeText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  disabledText: {
    color: '#999',
  },
  buttonContainer: {
    marginTop: 20,
    marginBottom: 40,
  },
  saveButton: {
    backgroundColor: '#4CAF50',
    paddingVertical: 15,
    borderRadius: 10,
    marginBottom: 10,
  },
  testButton: {
    backgroundColor: '#2196F3',
    paddingVertical: 15,
    borderRadius: 10,
    marginBottom: 10,
  },
  scheduleButton: {
    backgroundColor: '#FF9800',
    paddingVertical: 15,
    borderRadius: 10,
    marginBottom: 10,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
});

export default CommuteSettingsScreen;
