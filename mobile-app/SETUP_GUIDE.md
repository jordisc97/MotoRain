# MotoRain Mobile App - Complete Setup Guide

## 🚀 Overview

This guide will help you transform your existing MotoRain web application into a mobile iOS app that automatically sends rain alerts during your commute hours.

## 📱 What You'll Get

- **Automatic Rain Alerts**: Get notified 30 minutes before your commute
- **Smart Notifications**: ✅ Green tick for clear weather, 🌧️ Red alert for rain
- **Commute Scheduling**: Set your work days and commute times
- **Background Processing**: Works automatically without manual checking
- **App Store Ready**: Complete iOS app ready for submission

## 🛠️ Prerequisites

- macOS with Xcode installed
- Node.js and npm
- React Native CLI
- Your existing MotoRain backend running
- Apple Developer Account (for App Store submission)

## 📋 Step-by-Step Setup

### 1. Install React Native Environment

```bash
# Install React Native CLI
npm install -g react-native-cli

# Install iOS dependencies
cd mobile-app
npm install

# Install iOS pods
cd ios && pod install && cd ..
```

### 2. Configure Backend for Mobile

Update your backend to use the mobile-enhanced version:

```bash
# Backup your current app.py
cp backend/app.py backend/app_web.py

# Use the mobile version
cp backend/app_mobile.py backend/app.py

# Install additional dependencies
pip install asyncio
```

### 3. Update API Configuration

In the mobile app, update the API URL in:
- `src/services/RainCheckService.js` (line 6)
- `src/screens/WeatherScreen.js` (line 35)

Change `http://your-backend-url:8000` to your actual backend URL.

### 4. Configure iOS Permissions

Add these permissions to `ios/MotoRainMobile/Info.plist`:

```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>MotoRain needs location access to manage your home and work addresses.</string>
<key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
<string>MotoRain needs location access to provide accurate weather alerts for your commute route.</string>
<key>UIBackgroundModes</key>
<array>
    <string>background-processing</string>
    <string>background-fetch</string>
</array>
```

### 5. Set Up Push Notifications

1. **Apple Developer Console**:
   - Create App ID with Push Notifications capability
   - Generate APNs certificates
   - Create Provisioning Profile

2. **Configure APNs**:
   - Add your APNs certificate to the backend
   - Update notification service in `backend/app_mobile.py`

### 6. Test the App

```bash
# Start Metro bundler
npm start

# Run on iOS simulator
npm run ios

# Or run on physical device
npm run ios --device
```

## 🎯 Key Features Implemented

### ✅ Commute Configuration
- Set work days (Monday-Friday or custom)
- Configure morning and evening commute times
- Enable/disable notifications
- Set home and work addresses

### ✅ Background Processing
- Automatic weather checks 30 minutes before commute
- Background task scheduling
- iOS Background App Refresh integration
- Battery-optimized processing

### ✅ Smart Notifications
- **Clear Weather**: ✅ Green notification with "No rain expected"
- **Rain Alert**: 🌧️ Red notification with rain warning
- **Follow-up Reminders**: Additional notifications 10 minutes later
- **Test Notifications**: Manual testing capability

### ✅ Weather Integration
- Connects to your existing MotoRain backend
- Uses radar-based weather data
- Provides route-specific weather information
- Shows weather map images

## 📱 App Structure

```
mobile-app/
├── App.js                          # Main app component
├── package.json                    # Dependencies
├── src/
│   ├── screens/
│   │   ├── HomeScreen.js          # Main dashboard
│   │   ├── CommuteSettingsScreen.js # Commute configuration
│   │   ├── WeatherScreen.js       # Weather forecast
│   │   └── SettingsScreen.js      # App settings
│   └── services/
│       └── RainCheckService.js     # Background rain checking
└── ios/                           # iOS-specific files
```

## 🔧 Backend Enhancements

The mobile version includes these new endpoints:

- `POST /schedule_checks/` - Schedule automatic checks
- `POST /send_notification/` - Send push notifications
- `GET /scheduled_checks/{user_id}` - Get user's schedule
- `DELETE /scheduled_checks/{user_id}` - Remove schedule
- `GET /health` - Health check

## 🚀 App Store Submission

### 1. Prepare App Store Assets
- App icon (1024x1024)
- Screenshots for different device sizes
- App description and keywords
- Privacy policy

### 2. App Store Connect Setup
- Create new app in App Store Connect
- Upload app binary
- Fill app information
- Submit for review

### 3. App Review Guidelines
- Clear purpose and functionality
- Proper background processing usage
- Appropriate notification frequency
- Privacy compliance

## 🔒 Privacy & Security

### Data Collection
- Home and work addresses (stored locally)
- Commute schedule preferences
- Push notification tokens
- Weather check timestamps

### Privacy Policy Requirements
- Location data usage explanation
- Background processing disclosure
- Data storage and security measures
- Third-party service integration

## 🎨 Customization Options

### UI Customization
- Modify colors in `styles.js` files
- Update app icon and splash screen
- Customize notification sounds
- Add your branding

### Feature Extensions
- Multiple commute routes
- Weather forecast for multiple days
- Integration with calendar apps
- Social sharing features

## 🐛 Troubleshooting

### Common Issues

1. **Metro bundler not starting**:
   ```bash
   npx react-native start --reset-cache
   ```

2. **iOS build errors**:
   ```bash
   cd ios && pod install && cd ..
   ```

3. **Push notifications not working**:
   - Check APNs certificate configuration
   - Verify device token registration
   - Test with Apple's Push Notification Console

4. **Background tasks not running**:
   - Enable Background App Refresh in iOS Settings
   - Check iOS background execution limits
   - Verify task scheduling implementation

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review React Native documentation
3. Check iOS development guidelines
4. Test with iOS Simulator first

## 🎉 Next Steps

1. **Test thoroughly** on multiple devices
2. **Gather user feedback** during beta testing
3. **Optimize performance** for battery usage
4. **Prepare marketing materials** for App Store
5. **Submit for review** and respond to feedback

---

**Congratulations!** You now have a complete mobile app that will automatically alert you about rain conditions during your commute. The app is designed to work seamlessly in the background and provide timely, accurate weather alerts exactly when you need them.

🌧️ **Never get caught in the rain again!** 🌧️
