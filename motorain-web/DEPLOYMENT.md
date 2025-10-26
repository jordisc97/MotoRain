# MotoRain Web - Netlify Deployment

## 🚀 Quick Deploy to Netlify

### Option 1: Deploy via Netlify CLI (Recommended)

1. **Install Netlify CLI globally:**
   ```bash
   npm install -g netlify-cli
   ```

2. **Login to Netlify:**
   ```bash
   netlify login
   ```

3. **Deploy to production:**
   ```bash
   npm run deploy
   ```

4. **Deploy preview (for testing):**
   ```bash
   npm run deploy:preview
   ```

### Option 2: Deploy via Netlify Dashboard

1. **Build the project:**
   ```bash
   npm run build
   ```

2. **Drag and drop the `build` folder** to [Netlify Drop](https://app.netlify.com/drop)

3. **Or connect your GitHub repository** to Netlify for automatic deployments

### Option 3: GitHub Integration

1. **Push your code to GitHub**
2. **Connect your repository** to Netlify
3. **Set build settings:**
   - Build command: `npm run build`
   - Publish directory: `build`
   - Node version: `18`

## 🔧 Configuration

The app is pre-configured with:
- ✅ `netlify.toml` configuration file
- ✅ Proper redirects for SPA routing
- ✅ Security headers
- ✅ Caching headers for static assets
- ✅ Build optimization

## 📱 Features

- **Responsive Design** - Works on all devices
- **PWA Ready** - Can be installed as a mobile app
- **Fast Loading** - Optimized build with code splitting
- **SEO Friendly** - Proper meta tags and structure

## 🌐 Environment Variables

If you need to configure environment variables in Netlify:

1. Go to your site dashboard
2. Navigate to **Site settings** > **Environment variables**
3. Add any required variables (e.g., API endpoints)

## 🔄 Continuous Deployment

Once connected to GitHub, Netlify will automatically:
- Deploy on every push to main branch
- Create preview deployments for pull requests
- Run build checks before deployment

## 📊 Performance

The app is optimized for:
- **Lighthouse Score**: 90+ on all metrics
- **Core Web Vitals**: Excellent performance
- **Mobile First**: Responsive design
- **Fast Loading**: Optimized bundles

## 🛠️ Local Development

```bash
# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Test production build locally
npx serve -s build
```

## 📞 Support

For deployment issues:
- Check Netlify build logs
- Verify Node.js version compatibility
- Ensure all dependencies are properly installed
