# MotoRain Mobile App

## Overview
iOS mobile application that automatically checks for rain conditions during your commute hours and sends push notifications.

## Features
- ⏰ **Commute Schedule**: Configure work days and commute hours
- 🌧️ **Automatic Rain Checks**: Background checks before commute times
- 📱 **Push Notifications**: Green tick (no rain) or red alert (rain expected)
- 🏠 **Location Management**: Set home and work addresses
- 🔄 **Background Sync**: Integrates with existing MotoRain backend API

## Architecture

### Frontend (iOS App)
- **Framework**: React Native or Swift
- **State Management**: Redux/Context API or SwiftUI
- **Background Tasks**: iOS Background App Refresh
- **Push Notifications**: Apple Push Notification Service (APNs)
- **Location Services**: Core Location framework

### Backend Integration
- **API Endpoint**: `http://your-backend-url:8000/check_rain/`
- **Scheduling Service**: iOS Background Processing
- **Data Storage**: Core Data or SQLite for user settings

## Development Phases

### Phase 1: Core App Structure
- [ ] Set up React Native or Swift project
- [ ] Create basic navigation and UI
- [ ] Implement user settings screen

### Phase 2: Commute Configuration
- [ ] Commute days selection (Mon-Fri, custom)
- [ ] Commute hours configuration (morning/evening)
- [ ] Home/work address setup

### Phase 3: Background Processing
- [ ] Background task scheduling
- [ ] API integration for rain checking
- [ ] Local notification system

### Phase 4: Push Notifications
- [ ] Apple Push Notification setup
- [ ] Server-side notification service
- [ ] Notification scheduling logic

### Phase 5: App Store Deployment
- [ ] App Store Connect configuration
- [ ] App review and submission
- [ ] Production deployment

## Technical Requirements

### iOS Capabilities Needed
- Background App Refresh
- Push Notifications
- Location Services
- Background Processing
- Local Notifications

### Backend Modifications Needed
- Scheduled job endpoint
- User management system
- Notification service integration
- Database for user preferences

## Getting Started

1. Choose development framework (React Native vs Swift)
2. Set up development environment
3. Create basic app structure
4. Implement core features incrementally
5. Test with existing backend API
6. Deploy to App Store

## Next Steps
- [ ] Decide on React Native vs Swift
- [ ] Set up development environment
- [ ] Create initial app structure
- [ ] Implement user settings
