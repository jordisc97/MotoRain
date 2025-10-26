import React, { useState, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import HomeScreen from './screens/HomeScreen';
import WeatherScreen from './screens/WeatherScreen';
import CommuteSettingsScreen from './screens/CommuteSettingsScreen';
import SettingsScreen from './screens/SettingsScreen';
import TabBar from './components/TabBar';
import './App.css';

function App() {
  const [userSettings, setUserSettings] = useState({
    homeAddress: '123 Main St, Barcelona',
    workAddress: '456 Business Ave, Barcelona',
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
      time: '8:00 AM'
    },
    eveningCommute: {
      enabled: true,
      time: '5:30 PM'
    },
    notificationsEnabled: true
  });

  const [lastCheckTime, setLastCheckTime] = useState(new Date());

  // Load settings from localStorage on app start
  useEffect(() => {
    const savedSettings = localStorage.getItem('motorainSettings');
    if (savedSettings) {
      setUserSettings(JSON.parse(savedSettings));
    }
  }, []);

  // Save settings to localStorage whenever they change
  const updateSettings = (newSettings) => {
    const updatedSettings = { ...userSettings, ...newSettings };
    setUserSettings(updatedSettings);
    localStorage.setItem('motorainSettings', JSON.stringify(updatedSettings));
  };

  const updateLastCheck = () => {
    const now = new Date();
    setLastCheckTime(now);
  };

  return (
    <div className="App">
      <div className="app-content">
        <Routes>
          <Route path="/" element={<HomeScreen 
            userSettings={userSettings} 
            lastCheckTime={lastCheckTime}
            updateLastCheck={updateLastCheck}
          />} />
          <Route path="/weather" element={<WeatherScreen 
            userSettings={userSettings}
            updateLastCheck={updateLastCheck}
          />} />
          <Route path="/commute" element={<CommuteSettingsScreen 
            userSettings={userSettings}
            updateSettings={updateSettings}
          />} />
          <Route path="/settings" element={<SettingsScreen 
            userSettings={userSettings}
            updateSettings={updateSettings}
          />} />
        </Routes>
      </div>
      <TabBar />
    </div>
  );
}

export default App;
