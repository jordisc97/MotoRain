import React, { useState } from 'react';
import './CommuteSettingsScreen.css';

const CommuteSettingsScreen = ({ userSettings, updateSettings }) => {
  const [localSettings, setLocalSettings] = useState(userSettings);

  const handleSave = () => {
    updateSettings(localSettings);
    
    // Show success message
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('MotoRain', {
        body: 'Settings saved successfully!',
        icon: '/favicon.ico'
      });
    }
  };

  const toggleDay = (day) => {
    setLocalSettings(prev => ({
      ...prev,
      commuteDays: {
        ...prev.commuteDays,
        [day]: !prev.commuteDays[day]
      }
    }));
  };

  const toggleCommute = (type) => {
    setLocalSettings(prev => ({
      ...prev,
      [type]: {
        ...prev[type],
        enabled: !prev[type].enabled
      }
    }));
  };

  const changeTime = (type, newTime) => {
    setLocalSettings(prev => ({
      ...prev,
      [type]: {
        ...prev[type],
        time: newTime
      }
    }));
  };

  const updateAddress = (type, value) => {
    setLocalSettings(prev => ({
      ...prev,
      [type]: value
    }));
  };

  return (
    <div className="commute-screen">
      <div className="header">
        <h1>Commute Settings</h1>
        <p>Configure your daily schedule</p>
      </div>
      
      <div className="main-content">
        <div className="card">
          <h3>Work Days</h3>
          <div className="day-selector">
            {Object.entries(localSettings.commuteDays).map(([day, enabled]) => (
              <div
                key={day}
                className={`day-button ${enabled ? 'active' : ''}`}
                onClick={() => toggleDay(day)}
              >
                {day.charAt(0).toUpperCase() + day.slice(1, 3)}
              </div>
            ))}
          </div>
        </div>
        
        <div className="card">
          <h3>Morning Commute</h3>
          <div className="setting-row">
            <span>Enable</span>
            <div 
              className={`switch ${localSettings.morningCommute.enabled ? 'active' : ''}`}
              onClick={() => toggleCommute('morningCommute')}
            />
          </div>
          <div className="setting-row">
            <span>Time</span>
            <input
              type="time"
              value={localSettings.morningCommute.time}
              onChange={(e) => changeTime('morningCommute', e.target.value)}
              disabled={!localSettings.morningCommute.enabled}
            />
          </div>
        </div>
        
        <div className="card">
          <h3>Evening Commute</h3>
          <div className="setting-row">
            <span>Enable</span>
            <div 
              className={`switch ${localSettings.eveningCommute.enabled ? 'active' : ''}`}
              onClick={() => toggleCommute('eveningCommute')}
            />
          </div>
          <div className="setting-row">
            <span>Time</span>
            <input
              type="time"
              value={localSettings.eveningCommute.time}
              onChange={(e) => changeTime('eveningCommute', e.target.value)}
              disabled={!localSettings.eveningCommute.enabled}
            />
          </div>
        </div>
        
        <div className="card">
          <h3>Addresses</h3>
          <div className="input-group">
            <label>Home Address</label>
            <input
              type="text"
              value={localSettings.homeAddress}
              onChange={(e) => updateAddress('homeAddress', e.target.value)}
              placeholder="Enter your home address"
            />
          </div>
          <div className="input-group">
            <label>Work Address</label>
            <input
              type="text"
              value={localSettings.workAddress}
              onChange={(e) => updateAddress('workAddress', e.target.value)}
              placeholder="Enter your work address"
            />
          </div>
        </div>
        
        <div className="card">
          <button className="button" onClick={handleSave}>
            Save Settings
          </button>
          <button 
            className="button secondary"
            onClick={() => {
              if ('Notification' in window && Notification.permission === 'granted') {
                new Notification('MotoRain', {
                  body: 'Commute checks scheduled! You\'ll get alerts 30 minutes before your commute times.',
                  icon: '/favicon.ico'
                });
              }
            }}
          >
            Schedule Checks
          </button>
        </div>
      </div>
    </div>
  );
};

export default CommuteSettingsScreen;
