import React, { useState } from 'react';
import './HomeScreen.css';

const HomeScreen = ({ userSettings, lastCheckTime, updateLastCheck }) => {
  const [isChecking, setIsChecking] = useState(false);

  const checkRainNow = async () => {
    setIsChecking(true);
    
    // Simulate API call
    setTimeout(() => {
      setIsChecking(false);
      updateLastCheck();
      
      // Show notification
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('MotoRain', {
          body: 'Weather check completed! Check the Weather tab for details.',
          icon: '/favicon.ico'
        });
      }
      
      // Redirect to weather screen
      window.location.href = '/weather';
    }, 2000);
  };

  const requestNotificationPermission = () => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  };

  const formatLastCheck = () => {
    const now = new Date();
    const diffMinutes = Math.floor((now - lastCheckTime) / (1000 * 60));
    
    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes} minutes ago`;
    if (diffMinutes < 1440) return `${Math.floor(diffMinutes / 60)} hours ago`;
    return lastCheckTime.toLocaleDateString();
  };

  return (
    <div className="home-screen">
      <div className="header">
        <h1>MotoRain</h1>
        <p>Never get caught in the rain</p>
      </div>
      
      <div className="main-content">
        <div className="card status-card">
          <h3>Last Check</h3>
          <p>{formatLastCheck()}</p>
        </div>
        
        <div className="card">
          <button 
            className={`button success ${isChecking ? 'loading' : ''}`}
            onClick={checkRainNow}
            disabled={isChecking}
          >
            {isChecking ? (
              <>
                <span className="loading-spinner"></span>
                Checking...
              </>
            ) : (
              '🌤️ Check Rain Now'
            )}
          </button>
        </div>

        <div className="card">
          <h3>Quick Setup</h3>
          <p>Set your commute schedule in the Commute tab to get automatic rain alerts before your daily commute.</p>
          <button className="button secondary" onClick={() => window.location.href = '/commute'}>
            Configure Commute
          </button>
        </div>

        {Notification.permission === 'default' && (
          <div className="card notification-card">
            <h3>🔔 Enable Notifications</h3>
            <p>Get rain alerts for your commute times</p>
            <button className="button secondary" onClick={requestNotificationPermission}>
              Enable Notifications
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default HomeScreen;
