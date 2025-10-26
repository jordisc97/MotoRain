import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { StatusBar, Platform } from 'react-native';
import PushNotification from 'react-native-push-notification';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Import screens
import CommuteSettingsScreen from './src/screens/CommuteSettingsScreen';
import HomeScreen from './src/screens/HomeScreen';
import WeatherScreen from './src/screens/WeatherScreen';
import SettingsScreen from './src/screens/SettingsScreen';

// Import services
import RainCheckService from './src/services/RainCheckService';

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

// Configure push notifications
PushNotification.configure({
  onRegister: function (token) {
    console.log('TOKEN:', token);
    // Store token for server-side notifications
    AsyncStorage.setItem('pushToken', token.token);
  },

  onNotification: function (notification) {
    console.log('NOTIFICATION:', notification);
    
    // Handle notification actions
    if (notification.action === 'View Details') {
      // Navigate to weather screen
      console.log('User wants to view details');
    }
  },

  onAction: function (notification) {
    console.log('ACTION:', notification.action);
    console.log('NOTIFICATION:', notification);
  },

  onRegistrationError: function(err) {
    console.error(err.message, err);
  },

  permissions: {
    alert: true,
    badge: true,
    sound: true,
  },

  popInitialNotification: true,
  requestPermissions: true,
});

// Background task handler
const backgroundTask = async () => {
  console.log('Background task triggered');
  await RainCheckService.performBackgroundRainCheck();
};

// Main Tab Navigator
function TabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{
        tabBarActiveTintColor: '#2196F3',
        tabBarInactiveTintColor: 'gray',
        headerStyle: {
          backgroundColor: '#2196F3',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      }}
    >
      <Tab.Screen 
        name="Home" 
        component={HomeScreen}
        options={{
          title: 'MotoRain',
          tabBarIcon: ({ color, size }) => (
            <Icon name="home" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen 
        name="Weather" 
        component={WeatherScreen}
        options={{
          title: 'Weather',
          tabBarIcon: ({ color, size }) => (
            <Icon name="cloud" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen 
        name="Commute" 
        component={CommuteSettingsScreen}
        options={{
          title: 'Commute',
          tabBarIcon: ({ color, size }) => (
            <Icon name="clock" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen 
        name="Settings" 
        component={SettingsScreen}
        options={{
          title: 'Settings',
          tabBarIcon: ({ color, size }) => (
            <Icon name="settings" size={size} color={color} />
          ),
        }}
      />
    </Tab.Navigator>
  );
}

// Simple Icon component (you can replace with react-native-vector-icons)
const Icon = ({ name, size, color }) => {
  const iconMap = {
    home: '🏠',
    cloud: '☁️',
    clock: '⏰',
    settings: '⚙️',
  };
  
  return (
    <Text style={{ fontSize: size, color }}>
      {iconMap[name] || '❓'}
    </Text>
  );
};

// Main App Component
export default function App() {
  useEffect(() => {
    // Initialize the app
    initializeApp();
    
    // Set up background task
    if (Platform.OS === 'ios') {
      // iOS background task setup
      PushNotification.getApplicationIconBadgeNumber((badgeCount) => {
        if (badgeCount > 0) {
          PushNotification.setApplicationIconBadgeNumber(0);
        }
      });
    }

    // Schedule initial background checks
    RainCheckService.scheduleBackgroundChecks();

    // Set up notification listeners
    const notificationListener = PushNotification.addEventListener('notification', (notification) => {
      console.log('Notification received:', notification);
    });

    const localNotificationListener = PushNotification.addEventListener('localNotification', (notification) => {
      console.log('Local notification received:', notification);
    });

    return () => {
      notificationListener.remove();
      localNotificationListener.remove();
    };
  }, []);

  const initializeApp = async () => {
    try {
      // Check if this is the first launch
      const isFirstLaunch = await AsyncStorage.getItem('isFirstLaunch');
      
      if (!isFirstLaunch) {
        // First launch - set up default settings
        const defaultSettings = {
          commuteDays: {
            monday: true,
            tuesday: true,
            wednesday: true,
            thursday: true,
            friday: true,
            saturday: false,
            sunday: false,
          },
          morningCommute: {
            enabled: true,
            time: new Date(2024, 0, 1, 8, 0),
          },
          eveningCommute: {
            enabled: true,
            time: new Date(2024, 0, 1, 17, 30),
          },
          notificationsEnabled: true,
          homeAddress: '',
          workAddress: '',
        };

        await AsyncStorage.setItem('commuteSettings', JSON.stringify(defaultSettings));
        await AsyncStorage.setItem('isFirstLaunch', 'false');
        
        console.log('First launch setup completed');
      }
    } catch (error) {
      console.error('Error initializing app:', error);
    }
  };

  return (
    <NavigationContainer>
      <StatusBar barStyle="light-content" backgroundColor="#2196F3" />
      <Stack.Navigator>
        <Stack.Screen 
          name="Main" 
          component={TabNavigator}
          options={{ headerShown: false }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
