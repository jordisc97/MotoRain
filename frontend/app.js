// Configuration - Backend server URL
// This must point to where your FastAPI backend is running
const API_BASE_URL = 'http://localhost:8000';

console.log('API Base URL:', API_BASE_URL);
console.log('Frontend URL:', window.location.href);

// DOM Elements
const routeForm = document.getElementById('routeForm');
const loadingElement = document.getElementById('loading');
const resultElement = document.getElementById('result');
const resultContent = document.getElementById('resultContent');
const errorElement = document.getElementById('error');

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    routeForm.addEventListener('submit', handleFormSubmit);
});

// Form Submission Handler
async function handleFormSubmit(e) {
    e.preventDefault();
    
    // Get form values
    const username = document.getElementById('username').value.trim();
    const homeAddress = document.getElementById('homeAddress').value.trim();
    const workAddress = document.getElementById('workAddress').value.trim();
    
    // Validate inputs
    if (!username) {
        showError('Please enter your name');
        return;
    }
    
    if (!homeAddress || !workAddress) {
        showError('Please enter both home and work addresses');
        return;
    }
    
    // Show loading state
    setLoading(true);
    
    try {
        console.log('Sending request to:', `${API_BASE_URL}/check_rain/`);
        console.log('Request payload:', {
            user: username,
            home: homeAddress,
            work: workAddress
        });
        
        // Show loading state with better feedback
        document.getElementById('checkRainBtn').disabled = true;
        document.getElementById('checkRainBtn').innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            Checking...
        `;
        
        // Call the API
        const response = await fetch(`${API_BASE_URL}/check_rain/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user: username,
                home: homeAddress,
                work: workAddress,
                vehicle: 'bike' // Default to bike as per requirements
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to fetch weather data');
        }
        
        const data = await response.json();
        displayResults(data, { username, homeAddress, workAddress });
    } catch (error) {
        console.error('Error:', error);
        let errorMessage = error.message || 'An error occurred while checking the weather';
        
        // More specific error messages
        if (error.message.includes('Failed to fetch')) {
            errorMessage = 'Could not connect to the server. Please make sure the backend is running at ' + API_BASE_URL;
        } else if (error.message.includes('NetworkError')) {
            errorMessage = 'Network error. Please check your internet connection.';
        }
        
        showError(errorMessage);
    } finally {
        setLoading(false);
    }
}

// Display Results
function displayResults(data, formValues) {
    const { username, homeAddress, workAddress } = formValues;
    // Clear previous results
    resultContent.innerHTML = '';
    
    // Create result elements with improved layout
    const resultHeader = document.createElement('div');
    resultHeader.className = 'result-header';
    resultHeader.innerHTML = `
        <h3 class="result-title">Route Analysis</h3>
    `;
    
    const routeInfo = document.createElement('div');
    routeInfo.className = 'route-info';
    routeInfo.innerHTML = `
        <h5><i class="fas fa-route"></i> Your Route</h5>
        <p><i class="fas fa-route"></i> <strong>From:</strong> ${homeAddress} <i class="fas fa-arrow-right"></i> <strong>To:</strong> ${workAddress}</p>
    `;
    
    // Weather information with better icons and styling
    let weatherInfo = '';
    const weatherMessage = data.weather_condition || 'No rain expected on your route.';
    const alertClass = data.weather_condition ? getAlertClass(data.weather_condition) : 'alert-success';
    const alertIcon = getAlertIcon(data.weather_condition);
    
    weatherInfo = `
        <div class="alert ${alertClass}">
            <h5>${alertIcon} Weather Update</h5>
            <p>${weatherMessage}</p>
            ${data.rain_forecast ? `
                <div class="forecast-note mt-2">
                    <i class="fas fa-info-circle"></i>
                    <strong>Forecast:</strong> ${data.rain_forecast}
                </div>
            ` : ''}
        </div>
    `;
    
    // If we have an image, display it
    if (data.image_b64) {
        const img = document.createElement('img');
        img.src = `data:image/png;base64,${data.image_b64}`;
        img.alt = 'Route Map';
        img.className = 'img-fluid rounded mt-3';
        img.style.maxHeight = '500px';
        resultContent.appendChild(img);
    }
    
    // Add debug information
    const debugSection = document.createElement('div');
    debugSection.className = 'mt-4 p-3 bg-light rounded';
    debugSection.innerHTML = `
        <h5><i class="fas fa-bug me-2"></i>Debug Information</h5>
        <div class="mt-2">
            <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#debugResponse">
                Toggle Raw Response
            </button>
            <div class="collapse mt-2" id="debugResponse">
                <pre class="bg-white p-2 border rounded" style="max-height: 200px; overflow: auto;">${JSON.stringify(data, null, 2)}</pre>
            </div>
        </div>
    `;
    resultContent.appendChild(debugSection);
    
    // Add route info and weather info
    resultContent.prepend(routeInfo);
    resultContent.insertAdjacentHTML('beforeend', weatherInfo);
    
        // Show results
    resultElement.classList.remove('d-none');
    resultElement.scrollIntoView({ behavior: 'smooth' });
    
    // Log the full response to console for debugging
    console.log('Backend Response:', data);
}

// Helper Functions
function setLoading(isLoading) {
    const submitBtn = document.getElementById('checkRainBtn');
    if (isLoading) {
        loadingElement.classList.remove('d-none');
        resultElement.classList.add('d-none');
        errorElement.classList.add('d-none');
        submitBtn.disabled = true;
        submitBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            Checking...
        `;
    } else {
        loadingElement.classList.add('d-none');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Check Rain Conditions';
    }
}

function showError(message) {
    errorElement.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-exclamation-triangle me-2"></i>
            <div>${message || 'An error occurred. Please try again.'}</div>
        </div>
    `;
    errorElement.classList.remove('d-none');
    resultElement.classList.add('d-none');
    errorElement.scrollIntoView({ behavior: 'smooth' });
    
    // Reset button state
    const submitBtn = document.getElementById('checkRainBtn');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Try Again';
}

function getAlertClass(condition) {
    if (!condition) return 'alert-success';
    
    const conditionLower = condition.toLowerCase();
    if (conditionLower.includes('heavy')) return 'alert-danger';
    if (conditionLower.includes('light')) return 'alert-warning';
    if (conditionLower.includes('chance')) return 'alert-info';
    return 'alert-secondary';
}

function getAlertIcon(condition) {
    if (!condition) return '<i class="fas fa-sun"></i>';
    
    const conditionLower = condition.toLowerCase();
    if (conditionLower.includes('heavy')) return '<i class="fas fa-cloud-showers-heavy"></i>';
    if (conditionLower.includes('light')) return '<i class="fas fa-cloud-rain"></i>';
    if (conditionLower.includes('chance')) return '<i class="fas fa-cloud-sun-rain"></i>';
    return '<i class="fas fa-cloud"></i>';
}

function getWeatherMessage(condition) {
    if (!condition) {
        return 'Great news! No significant rain is expected on your route. Perfect weather for your journey!';
    }
    
    const conditionLower = condition.toLowerCase();
    
    if (conditionLower.includes('heavy')) {
        return 'Heavy rain is expected! Consider alternative transportation or delay your trip if possible. If you must travel, please take extra precautions.';
    }
    
    if (conditionLower.includes('light')) {
        return 'Light rain is expected. A light rain jacket and waterproof gear are recommended for your journey.';
    }
    
    if (conditionLower.includes('chance')) {
        return 'There\'s a chance of rain. You might want to bring a rain jacket just in case.';
    }
    
    return `Current conditions: ${condition}. Please check the forecast before heading out.`;
}
