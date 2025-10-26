#!/bin/bash

# MotoRain Mobile App - Xcode Sideloading Setup Script
# This script automates the setup process for sideloading the MotoRain app

set -e

echo "🚀 MotoRain Mobile App - Xcode Sideloading Setup"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script requires macOS to run Xcode"
    exit 1
fi

# Check if Xcode is installed
if ! command -v xcodebuild &> /dev/null; then
    print_error "Xcode is not installed. Please install Xcode from the Mac App Store."
    exit 1
fi

print_success "Xcode is installed"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_warning "Node.js is not installed. Installing via Homebrew..."
    if ! command -v brew &> /dev/null; then
        print_error "Homebrew is not installed. Please install Homebrew first."
        exit 1
    fi
    brew install node
fi

print_success "Node.js is installed"

# Check if React Native CLI is installed
if ! command -v react-native &> /dev/null; then
    print_warning "React Native CLI is not installed. Installing..."
    npm install -g react-native-cli
fi

print_success "React Native CLI is installed"

# Check if CocoaPods is installed
if ! command -v pod &> /dev/null; then
    print_warning "CocoaPods is not installed. Installing..."
    sudo gem install cocoapods
fi

print_success "CocoaPods is installed"

# Navigate to mobile app directory
if [ ! -d "mobile-app" ]; then
    print_error "mobile-app directory not found. Please run this script from the project root."
    exit 1
fi

cd mobile-app
print_status "Navigated to mobile-app directory"

# Install npm dependencies
print_status "Installing npm dependencies..."
npm install

# Install iOS dependencies
print_status "Installing iOS dependencies..."
cd ios
pod install
cd ..

print_success "Dependencies installed successfully"

# Check React Native setup
print_status "Checking React Native setup..."
npx react-native doctor

# Create Xcode project configuration
print_status "Configuring Xcode project..."

# Backup original Info.plist
if [ -f "ios/MotoRainMobile/Info.plist" ]; then
    cp ios/MotoRainMobile/Info.plist ios/MotoRainMobile/Info.plist.backup
    print_success "Backed up Info.plist"
fi

# Update Bundle Identifier to be unique
BUNDLE_ID="com.$(whoami).motorain"
print_status "Setting Bundle Identifier to: $BUNDLE_ID"

# Update Info.plist with unique bundle identifier
if [ -f "ios/MotoRainMobile/Info.plist" ]; then
    # This would require more complex plist manipulation
    print_warning "Please manually update Bundle Identifier in Xcode to: $BUNDLE_ID"
fi

# Create rebuild script
print_status "Creating rebuild script..."
cat > rebuild.sh << 'EOF'
#!/bin/bash

echo "🔄 Rebuilding MotoRain for iPhone..."

# Navigate to mobile app directory
cd "$(dirname "$0")"

# Clean previous build
echo "Cleaning previous build..."
cd ios
xcodebuild clean -workspace MotoRainMobile.xcworkspace -scheme MotoRainMobile

# Build and install
echo "Building and installing app..."
xcodebuild -workspace MotoRainMobile.xcworkspace -scheme MotoRainMobile -destination 'generic/platform=iOS' build

echo "✅ Build complete! App ready for installation."
echo "📱 Open Xcode and run the app on your connected iPhone."
EOF

chmod +x rebuild.sh
print_success "Created rebuild.sh script"

# Create weekly rebuild cron job
print_status "Setting up weekly rebuild reminder..."
cat > setup_cron.sh << 'EOF'
#!/bin/bash

# Add weekly rebuild reminder to crontab
(crontab -l 2>/dev/null; echo "0 9 * * 1 echo '🔄 Time to rebuild MotoRain app!' | terminal-notifier -title 'MotoRain Rebuild Reminder' -message 'Your app expires in 7 days. Run ./rebuild.sh to rebuild.'") | crontab -

echo "✅ Weekly rebuild reminder set up!"
echo "📅 You'll get a notification every Monday at 9 AM"
EOF

chmod +x setup_cron.sh

# Create device check script
print_status "Creating device check script..."
cat > check_devices.sh << 'EOF'
#!/bin/bash

echo "📱 Checking connected iOS devices..."

# List connected devices
xcrun devicectl list devices

echo ""
echo "💡 To build and run on your iPhone:"
echo "1. Make sure your iPhone is connected via USB"
echo "2. Trust the computer on your iPhone"
echo "3. Run: open ios/MotoRainMobile.xcworkspace"
echo "4. In Xcode, select your iPhone as the target"
echo "5. Press Cmd+R to build and run"
EOF

chmod +x check_devices.sh

print_success "Created device check script"

# Final instructions
echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Next steps:"
echo "1. 📱 Connect your iPhone to your Mac via USB"
echo "2. 🔒 Trust the computer on your iPhone"
echo "3. 🛠️  Open Xcode: open ios/MotoRainMobile.xcworkspace"
echo "4. ⚙️  In Xcode:"
echo "   - Select your iPhone as the target device"
echo "   - Go to Signing & Capabilities"
echo "   - Select your Apple ID as the Team"
echo "   - Change Bundle Identifier to: com.$(whoami).motorain"
echo "5. ▶️  Press Cmd+R to build and run"
echo ""
echo "📋 Useful commands:"
echo "   ./check_devices.sh    - Check connected devices"
echo "   ./rebuild.sh         - Rebuild the app"
echo "   ./setup_cron.sh      - Set up weekly rebuild reminder"
echo ""
echo "📖 For detailed instructions, see: DEVELOPER_SIDELOADING_GUIDE.md"
echo ""
print_success "MotoRain mobile app is ready for sideloading! 🚀"
