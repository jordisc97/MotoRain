import React, { useState } from 'react';
import './WeatherScreen.css';

const WeatherScreen = ({ userSettings, updateLastCheck }) => {
  const [isChecking, setIsChecking] = useState(false);
  const [weatherData, setWeatherData] = useState(null);

  const checkWeather = async () => {
    setIsChecking(true);
    
    setTimeout(() => {
      // Simulate weather data
      const simulatedData = {
        will_rain: Math.random() > 0.5,
        weather_condition: Math.random() > 0.5 ? 'Rain expected' : 'No significant rain expected',
        timestamp: new Date().toISOString()
      };
      
      setWeatherData(simulatedData);
      setIsChecking(false);
      updateLastCheck();
      
      // Show notification
      if ('Notification' in window && Notification.permission === 'granted') {
        const message = simulatedData.will_rain 
          ? '🌧️ Rain Alert! Check your route details.'
          : '✅ Clear Weather! Safe to commute.';
        
        new Notification('MotoRain Weather', {
          body: message,
          icon: '/favicon.ico'
        });
      }
    }, 2000);
  };

  const generateWeatherMap = (willRain) => {
    const canvas = document.createElement('canvas');
    canvas.width = 300;
    canvas.height = 200;
    const ctx = canvas.getContext('2d');
    
    // Draw background
    ctx.fillStyle = willRain ? '#4A90E2' : '#87CEEB';
    ctx.fillRect(0, 0, 300, 200);
    
    // Add weather patterns
    if (willRain) {
      ctx.fillStyle = 'rgba(255,255,255,0.7)';
      for (let i = 0; i < 20; i++) {
        ctx.beginPath();
        ctx.arc(Math.random() * 300, Math.random() * 200, 2, 0, 2 * Math.PI);
        ctx.fill();
      }
    } else {
      ctx.fillStyle = 'rgba(255,255,255,0.8)';
      ctx.beginPath();
      ctx.arc(150, 100, 30, 0, 2 * Math.PI);
      ctx.fill();
    }
    
    // Add route line
    ctx.strokeStyle = '#FF6B6B';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(50, 150);
    ctx.lineTo(250, 50);
    ctx.stroke();
    
    return canvas;
  };

  return (
    <div className="weather-screen">
      <div className="header">
        <h1>Weather Forecast</h1>
        <p>Current conditions for your route</p>
      </div>
      
      <div className="main-content">
        <div className="card">
          <h3>Your Route</h3>
          <div className="route-info">
            <p><strong>From:</strong> {userSettings.homeAddress}</p>
            <p><strong>To:</strong> {userSettings.workAddress}</p>
          </div>
        </div>
        
        <div className="card">
          <button 
            className={`button ${isChecking ? 'loading' : ''}`}
            onClick={checkWeather}
            disabled={isChecking}
          >
            {isChecking ? (
              <>
                <span className="loading-spinner"></span>
                Checking...
              </>
            ) : (
              '🌤️ Check Weather Now'
            )}
          </button>
        </div>
        
        {weatherData && (
          <div className="card weather-result">
            <div className="weather-icon">
              {weatherData.will_rain ? '🌧️' : '☀️'}
            </div>
            <h3 className={`weather-status ${weatherData.will_rain ? 'rain' : 'clear'}`}>
              {weatherData.will_rain ? 'Rain Alert' : 'Clear Weather'}
            </h3>
            <p className="weather-message">
              {weatherData.weather_condition}
            </p>
            
            <div className="weather-map">
              {generateWeatherMap(weatherData.will_rain)}
            </div>
            
            <p className="weather-time">
              Last updated: {new Date(weatherData.timestamp).toLocaleTimeString()}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default WeatherScreen;
