# 🚀 Quick Start Guide

## Prerequisites
- Python 3.8+
- Chrome browser
- Windows/Linux/macOS

## 🏃‍♂️ Quick Setup (Windows)

1. **Run the setup script:**
   ```bash
   scripts\setup.bat
   ```

2. **Start the application:**
   ```bash
   scripts\start-all.bat
   ```

3. **Open your browser:**
   Go to `http://localhost:3000`

## 🐧 Linux/macOS Setup

1. **Create virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start backend:**
   ```bash
   python -m uvicorn app:app --host 127.0.0.1 --port 8000
   ```

4. **Start frontend (new terminal):**
   ```bash
   cd frontend
   python -m http.server 3000
   ```

5. **Open browser:**
   Go to `http://localhost:3000`

## 🔧 Manual Configuration

If the automatic setup doesn't work:

1. **Update ChromeDriver path in `backend/app.py`:**
   ```python
   CHROMEDRIVER_PATH = r"../chromedriver/chromedriver.exe"  # Windows
   CHROMEDRIVER_PATH = "../chromedriver/chromedriver"       # Linux/macOS
   ```

2. **Make ChromeDriver executable (Linux/macOS):**
   ```bash
   chmod +x chromedriver/chromedriver
   ```

## 🎯 Usage

1. Enter your name
2. Enter your home address
3. Enter your work address
4. Click "Check Rain Conditions"
5. View the weather analysis and route map

## 🆘 Troubleshooting

- **Backend won't start:** Check virtual environment is activated
- **ChromeDriver error:** Update path in `app.py` and ensure Chrome is installed
- **Frontend can't connect:** Ensure backend is running on port 8000
- **No radar data:** Check internet connection and Meteocat website access

## 📚 More Information

- Full documentation: `README.md`
- API reference: `docs/API.md`
- Project structure: See `README.md` for detailed explanation
