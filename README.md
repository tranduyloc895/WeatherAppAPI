# WeatherAppAPI

## Overview
WeatherAppAPI is a Django-based backend application that provides APIs for user authentication, weather data retrieval, and alert notifications. It integrates with Firebase for authentication and Realtime Database for weather data storage.

## Features
- **User Authentication**: Signup, login, and user profile retrieval.
- **Weather Data Retrieval**:
  - Daily weather data.
  - Weather data for a specific date range.
- **Alert Notifications**: Sends email alerts when weather conditions exceed specified thresholds.

## Prerequisites
- Python 3.12 or higher
- Firebase project with Realtime Database and Authentication enabled
- SMTP server credentials for sending emails

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd <repository-folder>
```

### 2. Create a Virtual Environment
```bash
python -m venv env
source env/bin/activate  # On Windows: .\env\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Firebase
- Place your Firebase credentials JSON file in the root directory.
- Update `settings.py` to include the Firebase configuration.

### 5. Configure Email Settings
Update the following in `settings.py`:
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your_email@example.com'
EMAIL_HOST_PASSWORD = 'your_password'
```

### 6. Run Migrations
```bash
python manage.py migrate
```

### 7. Start the Server
```bash
python manage.py runserver
```

## API Endpoints

### Authentication
- **Signup**: `POST /api/signup/`
- **Login**: `POST /api/login/`
- **Get User Info**: `GET /api/getMe/`

### Weather Data
- **Daily Weather Data**: `GET /api/weather/daily/`
- **Weather Data by Date Range**: `GET /api/weather/getDayRange/?start_date=<dd/mm/yyyy>&end_date=<dd/mm/yyyy>`

### Alerts
- **Send Alert Email**: `POST /api/send_alert_email/`
  - **Request Body**:
    ```json
    {
      "temp_threshold": 30,
      "humid_threshold": 80,
      "pressure_threshold": 101000,
      "email_to": "recipient@example.com"
    }
    ```

## License
This project is licensed under the MIT License.
