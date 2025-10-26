import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './TabBar.css';

const TabBar = () => {
  const location = useLocation();

  const tabs = [
    { path: '/', icon: '🏠', label: 'Home' },
    { path: '/weather', icon: '☁️', label: 'Weather' },
    { path: '/commute', icon: '⏰', label: 'Commute' },
    { path: '/settings', icon: '⚙️', label: 'Settings' }
  ];

  return (
    <div className="tab-bar">
      {tabs.map((tab) => (
        <Link
          key={tab.path}
          to={tab.path}
          className={`tab-item ${location.pathname === tab.path ? 'active' : ''}`}
        >
          <div className="tab-icon">{tab.icon}</div>
          <div className="tab-label">{tab.label}</div>
        </Link>
      ))}
    </div>
  );
};

export default TabBar;
