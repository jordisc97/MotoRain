# MotoRain Web App - React Native Web

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build
```

## 📱 Features

- **Modern Mobile-First Design**: Optimized for mobile devices
- **Progressive Web App**: Can be installed on mobile devices
- **Real-time Weather Checking**: Connect to your MotoRain backend
- **Commute Scheduling**: Set up automatic rain alerts
- **Push Notifications**: Browser notifications for weather alerts
- **Offline Support**: Works offline with cached data

## 🌐 Deployment

### Netlify (Recommended)
1. Connect your GitHub repository to Netlify
2. Set build command: `npm run build`
3. Set publish directory: `build`
4. Deploy!

### Vercel
1. Import project from GitHub
2. Framework: Create React App
3. Deploy!

### Manual Deployment
1. Run `npm run build`
2. Upload `build` folder to any web hosting service

## 🔧 Configuration

Update the API URL in your components to point to your MotoRain backend:

```javascript
const API_BASE_URL = 'https://your-backend-url.com';
```

## 📱 PWA Features

- **Installable**: Users can install the app on their mobile devices
- **Offline Support**: Basic functionality works without internet
- **Push Notifications**: Weather alerts via browser notifications
- **Mobile Optimized**: Designed for mobile-first experience

## 🎯 Next Steps

1. **Deploy to web hosting** (Netlify/Vercel)
2. **Test on mobile devices**
3. **Configure push notifications**
4. **Connect to your backend API**
5. **Gather user feedback**
6. **Iterate and improve**

This web app provides the same functionality as the mobile app but runs in any modern browser!
