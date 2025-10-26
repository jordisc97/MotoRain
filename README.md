# 🌧️ MotoRain - Weather Route Analyzer

A real-time weather analysis application that helps cyclists and motorcyclists determine if they should take their bike based on current rain conditions along their commute route.

## 🚀 Features

- **Real-time Radar Data**: Scrapes live weather radar data from Meteocat (Catalonia weather service)
- **Route Analysis**: Analyzes rain conditions along your specific commute route
- **Visual Maps**: Generates annotated maps showing weather patterns and your route
- **Smart Recommendations**: Provides weather-based recommendations for your journey
- **Modern Web Interface**: Clean, responsive frontend with Bootstrap styling

## 🏗️ Architecture

### Backend (FastAPI)
- **FastAPI** web framework for high-performance API
- **Selenium WebDriver** for web scraping radar data
- **PIL/Pillow** for image processing and map generation
- **NumPy** for data analysis
- **Pydantic** for data validation

### Frontend (Vanilla JavaScript)
- **Bootstrap 5** for responsive UI
- **Font Awesome** for icons
- **Vanilla JavaScript** for API communication
- **Modern CSS** with custom styling

## 📁 Project Structure

```
MotoRain-GitHub/
├── backend/
│   ├── app.py                 # FastAPI application
│   ├── radar_rain_checker.py  # Core weather analysis logic
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── index.html            # Main HTML page
│   ├── app.js               # Frontend JavaScript
│   └── styles.css           # Custom CSS styles
├── chromedriver/
│   ├── chromedriver.exe     # ChromeDriver executable
│   └── LICENSE files        # ChromeDriver licenses
├── scripts/
│   ├── start-backend.bat    # Windows backend startup script
│   ├── start-frontend.bat   # Windows frontend startup script
│   └── start-all.bat       # Start both services
├── docs/
│   └── API.md              # API documentation
└── README.md               # This file
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+ 
- Chrome browser (for WebDriver)
- Windows/Linux/macOS

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment:**
   - Windows: `venv\Scripts\activate`
   - Linux/macOS: `source venv/bin/activate`

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Update ChromeDriver path in `app.py`:**
   ```python
   CHROMEDRIVER_PATH = r"path\to\your\chromedriver\chromedriver.exe"
   ```

6. **Start the backend server:**
   ```bash
   python -m uvicorn app:app --host 127.0.0.1 --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Start the frontend server:**
   ```bash
   python -m http.server 3000
   ```

3. **Access the application:**
   Open your browser and go to `http://localhost:3000`

## 🚀 Quick Start (Windows)

Use the provided batch scripts for easy startup:

1. **Start both services:**
   ```bash
   scripts\start-all.bat
   ```

2. **Or start individually:**
   ```bash
   scripts\start-backend.bat
   scripts\start-frontend.bat
   ```

## 📖 How It Works

### 1. **Server Startup**
- Backend initializes and scrapes radar data from Meteocat
- Radar images are downloaded and processed
- Server becomes ready to handle requests

### 2. **User Request**
- User enters their name, home address, and work address
- Frontend sends POST request to `/check_rain/` endpoint

### 3. **Route Processing**
- Addresses are converted to GPS coordinates using geocoding
- Route is analyzed against current radar data
- Rain intensity along the route is calculated

### 4. **Map Generation**
- Annotated map is created showing:
  - User's route (home → work)
  - Current rain patterns
  - Weather intensity zones

### 5. **Response**
- Backend returns weather analysis and map image
- Frontend displays results with recommendations

## 🔧 Configuration

### Map Bounds
The application is configured for Catalonia region. To change the area:

```python
MAP_BOUNDS = (lat_min, lon_min, lat_max, lon_max)
```

### ChromeDriver Settings
```python
CHROMEDRIVER_PATH = r"path\to\chromedriver.exe"
```

## 🌐 API Endpoints

### POST `/check_rain/`
Analyzes weather conditions for a user's route.

**Request Body:**
```json
{
  "user": "John Doe",
  "home": "Barcelona, Spain",
  "work": "Terrassa, Spain",
  "vehicle": "bike"
}
```

**Response:**
```json
{
  "status": "ok",
  "user": "John Doe",
  "vehicle": "bike",
  "image_b64": "base64_encoded_map_image",
  "will_rain": true,
  "weather_condition": "Rain expected"
}
```

## 🐛 Troubleshooting

### Common Issues

1. **ChromeDriver not found:**
   - Ensure ChromeDriver path is correct in `app.py`
   - Download ChromeDriver matching your Chrome version

2. **Backend won't start:**
   - Check Python virtual environment is activated
   - Verify all dependencies are installed
   - Run from the `backend` directory

3. **Frontend can't connect:**
   - Ensure backend is running on port 8000
   - Check CORS settings in `app.py`

4. **Radar data not loading:**
   - Check internet connection
   - Verify Meteocat website is accessible
   - Check ChromeDriver compatibility

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Meteocat** for providing weather radar data
- **FastAPI** for the excellent web framework
- **Selenium** for web automation capabilities
- **Bootstrap** for the responsive UI components

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation

---

**Happy commuting! 🚴‍♂️🏍️**
