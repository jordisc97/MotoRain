# MotoRain API Documentation

## Overview

The MotoRain API provides weather analysis for cycling and motorcycling routes. It scrapes real-time radar data and analyzes rain conditions along user-specified routes.

## Base URL

```
http://localhost:8000
```

## Authentication

No authentication required for this API.

## Endpoints

### POST /check_rain/

Analyzes weather conditions for a user's commute route.

#### Request

**URL:** `/check_rain/`

**Method:** `POST`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "user": "string",      // User's name
  "home": "string",      // Home address
  "work": "string",      // Work address  
  "vehicle": "string"    // Optional: "bike" or "motorbike" (default: "bike")
}
```

**Example Request:**
```json
{
  "user": "John Doe",
  "home": "Barcelona, Spain",
  "work": "Terrassa, Spain",
  "vehicle": "bike"
}
```

#### Response

**Success Response (200 OK):**
```json
{
  "status": "ok",
  "user": "John Doe",
  "vehicle": "bike",
  "image_b64": "iVBORw0KGgoAAAANSUhEUgAA...", // Base64 encoded map image
  "will_rain": true,
  "weather_condition": "Rain expected"
}
```

**Error Responses:**

**503 Service Unavailable:**
```json
{
  "detail": "Radar data not available yet. Please try again in a moment."
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Failed to process radar data"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Annotated map not found"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always "ok" for successful responses |
| `user` | string | User's name as provided in request |
| `vehicle` | string | Vehicle type ("bike" or "motorbike") |
| `image_b64` | string | Base64 encoded PNG image of the route map |
| `will_rain` | boolean | True if rain is expected along the route |
| `weather_condition` | string | Human-readable weather description |

## Data Models

### RouteIn

```python
class RouteIn(BaseModel):
    user: str
    home: str  # address string
    work: str  # address string
    vehicle: Optional[str] = "bike"  # "bike" or "motorbike"
```

## Error Handling

The API uses standard HTTP status codes:

- **200 OK**: Successful request
- **422 Unprocessable Entity**: Invalid request data
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Radar data not ready

## Rate Limiting

No rate limiting is currently implemented. However, radar data scraping is resource-intensive, so avoid rapid successive requests.

## CORS

The API is configured to accept requests from:
- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `http://localhost:8000`
- `http://127.0.0.1:8000`
- `file://` protocol

## Examples

### JavaScript/Fetch

```javascript
const response = await fetch('http://localhost:8000/check_rain/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    user: 'John Doe',
    home: 'Barcelona, Spain',
    work: 'Terrassa, Spain',
    vehicle: 'bike'
  })
});

const data = await response.json();
console.log(data);
```

### Python/Requests

```python
import requests

url = "http://localhost:8000/check_rain/"
payload = {
    "user": "John Doe",
    "home": "Barcelona, Spain", 
    "work": "Terrassa, Spain",
    "vehicle": "bike"
}

response = requests.post(url, json=payload)
data = response.json()
print(data)
```

### cURL

```bash
curl -X POST "http://localhost:8000/check_rain/" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "John Doe",
    "home": "Barcelona, Spain",
    "work": "Terrassa, Spain", 
    "vehicle": "bike"
  }'
```

## Notes

- The API automatically scrapes radar data on startup
- Addresses are geocoded to GPS coordinates for analysis
- Map images are generated as PNG files and returned as base64
- The service is optimized for Catalonia region weather data
- ChromeDriver is required for web scraping functionality
