# MotoRain Mobile App - Developer Mode + Xcode Sideloading Guide

## 🚀 Overview

This guide shows you how to sideload your MotoRain mobile app directly onto your iPhone using Xcode and a free Apple ID. This is perfect for developers, hobbyists, or anyone who wants to run their own app on their personal iPhone without going through the App Store.

## ✅ Benefits

- **Free**: Uses free Apple ID (no $99/year developer account needed)
- **Personal Use**: Perfect for personal apps or learning
- **Direct Control**: Build and run directly from Xcode
- **No App Store**: Skip the App Store review process
- **7-Day Limit**: App runs for 7 days before needing rebuild (free Apple ID limitation)

## 📋 Prerequisites

### Required Software
- **macOS** (required for Xcode)
- **Xcode** (latest version from Mac App Store)
- **iPhone** (iOS 12.0 or later)
- **USB Cable** (Lightning or USB-C)
- **Free Apple ID** (can use existing iCloud account)

### Required Hardware
- **Mac computer** (MacBook, iMac, Mac mini, etc.)
- **iPhone** (any model that supports iOS 12.0+)
- **USB cable** to connect iPhone to Mac

## 🛠️ Step-by-Step Setup

### Step 1: Prepare Your Development Environment

1. **Install Xcode**:
   ```bash
   # Download from Mac App Store or Apple Developer website
   # Make sure to install Command Line Tools
   xcode-select --install
   ```

2. **Install Node.js and React Native CLI**:
   ```bash
   # Install Node.js (if not already installed)
   brew install node
   
   # Install React Native CLI globally
   npm install -g react-native-cli
   
   # Install CocoaPods (for iOS dependencies)
   sudo gem install cocoapods
   ```

### Step 2: Set Up Your MotoRain Project

1. **Navigate to your mobile app directory**:
   ```bash
   cd mobile-app
   ```

2. **Install dependencies**:
   ```bash
   npm install
   cd ios && pod install && cd ..
   ```

3. **Verify React Native setup**:
   ```bash
   npx react-native doctor
   ```

### Step 3: Configure Xcode for Sideloading

1. **Open Xcode**:
   ```bash
   open ios/MotoRainMobile.xcworkspace
   ```

2. **Select your project** in the navigator (MotoRainMobile)

3. **Go to Signing & Capabilities tab**

4. **Configure Team**:
   - **Team**: Select your Apple ID (free account)
   - **Bundle Identifier**: Change to something unique like `com.yourname.motorain`
   - **Signing Certificate**: "Apple Development" (automatic)

5. **Enable Developer Mode**:
   - **Automatically manage signing**: ✅ Checked
   - **Provisioning Profile**: Should auto-generate

### Step 4: Prepare Your iPhone

1. **Connect iPhone to Mac** with USB cable

2. **Trust the computer** on your iPhone when prompted

3. **Enable Developer Mode** on iPhone:
   - Go to **Settings > Privacy & Security > Developer Mode**
   - Toggle **Developer Mode** ON
   - Restart iPhone when prompted
   - Confirm Developer Mode is enabled

4. **Trust your Apple ID**:
   - Go to **Settings > General > VPN & Device Management**
   - Find your Apple ID under "Developer App"
   - Tap **Trust** and confirm

### Step 5: Build and Run Your App

1. **In Xcode**:
   - Select your **iPhone** as the target device (not simulator)
   - Make sure your iPhone appears in the device list

2. **Build and Run**:
   - Press **Cmd + R** or click the **Play** button
   - Xcode will build the app and install it on your iPhone

3. **First Launch**:
   - On your iPhone, go to **Settings > General > VPN & Device Management**
   - Find "MotoRainMobile" under "Developer App"
   - Tap **Trust** and confirm

4. **Launch the App**:
   - Find MotoRainMobile on your home screen
   - Tap to launch - it should work perfectly!

## 🔄 Managing the 7-Day Limit

### Understanding the Limit
- **Free Apple ID**: Apps expire after 7 days
- **Paid Developer Account**: Apps last 1 year
- **Solution**: Rebuild and reinstall before expiration

### Automated Rebuild Process

1. **Create a rebuild script** (`rebuild.sh`):
   ```bash
   #!/bin/bash
   echo "Rebuilding MotoRain for iPhone..."
   
   # Clean previous build
   cd ios
   xcodebuild clean -workspace MotoRainMobile.xcworkspace -scheme MotoRainMobile
   
   # Build and install
   xcodebuild -workspace MotoRainMobile.xcworkspace -scheme MotoRainMobile -destination 'platform=iOS,name=Your iPhone Name' build
   
   echo "Build complete! App installed on iPhone."
   ```

2. **Set up weekly reminder**:
   ```bash
   # Add to crontab for weekly rebuilds
   crontab -e
   # Add: 0 9 * * 1 /path/to/rebuild.sh
   ```

## 🎯 Advanced Configuration

### Custom Bundle Identifier
```bash
# In Xcode, change Bundle Identifier to:
com.yourname.motorain
# Example: com.jordisc97.motorain
```

### App Icon and Display Name
1. **App Icon**: Replace `ios/MotoRainMobile/Images.xcassets/AppIcon.appiconset/` with your icons
2. **Display Name**: Change in `ios/MotoRainMobile/Info.plist`:
   ```xml
   <key>CFBundleDisplayName</key>
   <string>MotoRain</string>
   ```

### Push Notifications (Optional)
```bash
# For push notifications, you'll need:
# 1. Apple Push Notification service (APNs) certificate
# 2. Update Info.plist with notification capabilities
```

## 🐛 Troubleshooting

### Common Issues

1. **"Untrusted Developer" Error**:
   - Go to Settings > General > VPN & Device Management
   - Trust your Apple ID under "Developer App"

2. **Build Fails with Code Signing Error**:
   - Check Bundle Identifier is unique
   - Verify Team is selected correctly
   - Clean build folder: Product > Clean Build Folder

3. **App Crashes on Launch**:
   - Check Xcode console for error messages
   - Verify all dependencies are installed
   - Try running on iOS Simulator first

4. **iPhone Not Detected**:
   - Check USB cable connection
   - Trust computer on iPhone
   - Restart both Mac and iPhone

### Debug Commands
```bash
# Check connected devices
xcrun devicectl list devices

# View device logs
xcrun devicectl device log stream --device [DEVICE_ID]

# Install app manually
xcrun devicectl device install app --device [DEVICE_ID] [APP_PATH]
```

## 📱 App Features Ready for Sideloading

Your MotoRain app includes:
- ✅ **Weather Analysis**: Real-time rain checking
- ✅ **Commute Settings**: Work schedule configuration
- ✅ **Push Notifications**: Rain alerts (with proper setup)
- ✅ **Background Processing**: Automatic weather checks
- ✅ **Modern UI**: iOS-native design
- ✅ **Local Storage**: Persistent settings

## 🔐 Security Considerations

### What This Method Provides
- ✅ **Personal Use**: Perfect for your own iPhone
- ✅ **No App Store**: Skip review process
- ✅ **Full Control**: Complete app functionality
- ✅ **Privacy**: App stays on your device

### Limitations
- ⚠️ **7-Day Limit**: Must rebuild weekly (free Apple ID)
- ⚠️ **Personal Only**: Can't distribute to others easily
- ⚠️ **No App Store**: Not available for public download

## 🚀 Next Steps

1. **Follow the setup guide** above
2. **Test your app** on your iPhone
3. **Set up weekly rebuilds** to avoid expiration
4. **Customize the app** with your preferences
5. **Enjoy your personal MotoRain app!**

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify all prerequisites are installed
3. Ensure iPhone is properly connected and trusted
4. Check Xcode console for specific error messages

---

**Happy sideloading! 🎉 Your personal MotoRain app is ready to keep you dry on your commute!**
