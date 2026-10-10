# Trekking Club Flask App

A Flask-based web application for trekking club members, featuring authentication, trekking difficulty levels, emergency SOS messaging, location tracking, and an AI-powered chat interface.

## 🚀 Features

- User registration and login
- Member dashboard
- Trekking difficulty levels: Easy, Moderate, and Hard
- Trekking maps and location links
- SOS messaging through Fast2SMS
- Location updates and live tracking
- AI chat functionality powered by Google's Gemini API
- HTML templates and trekking image assets

## 📂 Project Structure

```text
Trekking-Club-Application/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── static/
│   └── img/
│       ├── DEFAULT.jpg
│       ├── EASY.jpg
│       ├── MODERATE.jpg
│       ├── HARD.jpg
│       ├── logo.jpeg
│       └── map.jpeg
└── templates/
    ├── home.html
    ├── login.html
    ├── signup.html
    ├── dashboard.html
    ├── button.html
    ├── chat.html
    └── track.html
```

## Prerequisites

- Python 3.11 or a compatible Python version
- MySQL Server
- A Google Gemini API key for chatbot functionality
- A Fast2SMS API key for SMS functionality
- A Google Maps API key for map rendering

## ⚙️ Installation

### 1. Clone the repository

```powershell
git clone https://github.com/LeutnantMutig/Trekking-Club-Application.git
cd Trekking-Club-Application
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file by copying the example:

```powershell
Copy-Item .env.example .env
```

Update `.env` with your own configuration values. Set your MySQL credentials, database name, Flask secret key, and the API keys required by the features you intend to use.

**Never commit `.env` or publish API keys, passwords, or other secrets.**

### 5. Configure MySQL

Create the MySQL database and required tables expected by `app.py` before starting the application. Use the database name configured in `.env`.

### 6. Run the application

```powershell
python app.py
```

By default, the application uses:

```text
http://127.0.0.1:3000
```

The port can be changed using the `PORT` environment variable.

## Security Notes

- Keep API keys and database credentials private.
- Use a strong, unique Flask `SECRET_KEY`.
- Restrict access to live location data before deploying publicly.
- Use a production-ready WSGI server and appropriate HTTPS configuration for deployment. Flask's built-in development server is for local development.


## 🤝 Contributing

Contributions are welcome. For substantial changes, open an issue to discuss the proposed update before submitting a pull request.


## 📜 License

This project is distributed under the MIT License. See the `LICENSE` file for details.
