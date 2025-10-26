import React, { useState, useEffect } from 'react';
import './SettingsScreen.css';

const SettingsScreen = ({ userSettings, updateSettings }) => {
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [homeAddress, setHomeAddress] = useState('');
  const [workAddress, setWorkAddress] = useState('');
  const [apiUrl, setApiUrl] = useState('http://localhost:8000');
  const [isEditingAddresses, setIsEditingAddresses] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = () => {
    try {
      const settings = localStorage.getItem('commuteSettings');
      if (settings) {
        const parsedSettings = JSON.parse(settings);
        setNotificationsEnabled(parsedSettings.notificationsEnabled !== false);
        setHomeAddress(parsedSettings.homeAddress || '');
        setWorkAddress(parsedSettings.workAddress || '');
      }

      const savedApiUrl = localStorage.getItem('apiUrl');
      if (savedApiUrl) {
        setApiUrl(savedApiUrl);
      }
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  const saveSettings = () => {
    try {
      const settings = {
        notificationsEnabled,
        homeAddress,
        workAddress,
      };
      localStorage.setItem('commuteSettings', JSON.stringify(settings));
      localStorage.setItem('apiUrl', apiUrl);
      
      // Update parent component settings
      updateSettings({
        homeAddress,
        workAddress,
        notificationsEnabled
      });
      
      alert('Settings saved successfully!');
      setIsEditingAddresses(false);
    } catch (error) {
      console.error('Error saving settings:', error);
      alert('Failed to save settings');
    }
  };

  const testNotification = () => {
    if ('Notification' in window) {
      if (Notification.permission === 'granted') {
        new Notification('MotoRain Test', {
          body: 'This is a test notification!',
          icon: '/favicon.ico'
        });
      } else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
          if (permission === 'granted') {
            new Notification('MotoRain Test', {
              body: 'This is a test notification!',
              icon: '/favicon.ico'
            });
          }
        });
      }
    } else {
      alert('Notifications are not supported in this browser');
    }
  };

  const clearAllData = () => {
    if (window.confirm('This will clear all your settings and data. Are you sure?')) {
      try {
        localStorage.clear();
        alert('All data cleared successfully!');
        loadSettings();
      } catch (error) {
        console.error('Error clearing data:', error);
        alert('Failed to clear data');
      }
    }
  };

  const exportSettings = () => {
    try {
      const settings = localStorage.getItem('commuteSettings');
      const apiUrl = localStorage.getItem('apiUrl');
      
      const exportData = {
        commuteSettings: settings ? JSON.parse(settings) : null,
        apiUrl: apiUrl || 'http://localhost:8000',
        exportDate: new Date().toISOString(),
      };

      // Create and download file
      const dataStr = JSON.stringify(exportData, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'motorain-settings.json';
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting settings:', error);
      alert('Failed to export settings');
    }
  };

  return (
    <div className="settings-container">
      <div className="settings-header">
        <h1 className="settings-title">Settings</h1>
        <p className="settings-subtitle">Configure your MotoRain experience</p>
      </div>

      {/* Notifications Section */}
      <div className="settings-section">
        <h2 className="section-title">Notifications</h2>
        <div className="setting-row">
          <label className="setting-label">Enable Rain Alerts</label>
          <label className="switch">
            <input
              type="checkbox"
              checked={notificationsEnabled}
              onChange={(e) => setNotificationsEnabled(e.target.checked)}
            />
            <span className="slider"></span>
          </label>
        </div>
        <button className="test-button" onClick={testNotification}>
          Test Notification
        </button>
      </div>

      {/* Addresses Section */}
      <div className="settings-section">
        <div className="section-header">
          <h2 className="section-title">Addresses</h2>
          <button 
            className="edit-button"
            onClick={() => setIsEditingAddresses(!isEditingAddresses)}
          >
            {isEditingAddresses ? 'Done' : 'Edit'}
          </button>
        </div>
        
        <div className="input-group">
          <label className="input-label">Home Address</label>
          <input
            className="text-input"
            type="text"
            value={homeAddress}
            onChange={(e) => setHomeAddress(e.target.value)}
            placeholder="Enter your home address"
            disabled={!isEditingAddresses}
          />
        </div>
        
        <div className="input-group">
          <label className="input-label">Work Address</label>
          <input
            className="text-input"
            type="text"
            value={workAddress}
            onChange={(e) => setWorkAddress(e.target.value)}
            placeholder="Enter your work address"
            disabled={!isEditingAddresses}
          />
        </div>
      </div>

      {/* API Configuration */}
      <div className="settings-section">
        <h2 className="section-title">API Configuration</h2>
        <div className="input-group">
          <label className="input-label">Backend URL</label>
          <input
            className="text-input"
            type="url"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            placeholder="http://localhost:8000"
          />
        </div>
      </div>

      {/* App Information */}
      <div className="settings-section">
        <h2 className="section-title">App Information</h2>
        <div className="info-row">
          <span className="info-label">Version</span>
          <span className="info-value">1.0.0</span>
        </div>
        <div className="info-row">
          <span className="info-label">Build</span>
          <span className="info-value">2024.1</span>
        </div>
        <div className="info-row">
          <span className="info-label">Last Updated</span>
          <span className="info-value">{new Date().toLocaleDateString()}</span>
        </div>
      </div>

      {/* Actions */}
      <div className="settings-section">
        <h2 className="section-title">Actions</h2>
        <button className="action-button" onClick={saveSettings}>
          Save Settings
        </button>
        
        <button className="export-button" onClick={exportSettings}>
          Export Settings
        </button>
        
        <button className="clear-button" onClick={clearAllData}>
          Clear All Data
        </button>
      </div>

      {/* Footer */}
      <div className="settings-footer">
        <p className="footer-text">
          MotoRain - Never get caught in the rain again! 🌧️
        </p>
        <p className="footer-subtext">
          Made with ❤️ for commuters
        </p>
      </div>
    </div>
  );
};

export default SettingsScreen;
