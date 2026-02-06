# Directed Evolution Portal - Backend

Flask backend API for the Directed Evolution Portal with PostgreSQL database integration.

## Features

- **User Authentication**: Register, login, logout with secure password hashing (bcrypt)
- **Session Management**: 24-hour session duration using Flask-Session
- **PostgreSQL Database**: User data persisted in PostgreSQL (Neon)
- **CORS Support**: Configured for frontend communication

## API Endpoints

### Authentication

#### POST `/api/auth/register`

Register a new user account.

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**

```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "createdAt": "2026-02-06T13:00:00"
  }
}
```

#### POST `/api/auth/login`

Login with existing credentials.

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**

```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "createdAt": "2026-02-06T13:00:00"
  }
}
```

#### POST `/api/auth/logout`

Logout and clear session.

**Response:**

```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

#### GET `/api/auth/session`

Check if user has an active session.

**Response:**

```json
{
  "success": true,
  "authenticated": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "createdAt": "2026-02-06T13:00:00"
  }
}
```

### Health Check

#### GET `/health`

Check if the server is running.

**Response:**

```json
{
  "status": "ok"
}
```

## Setup

### Prerequisites

- Python 3.9+
- PostgreSQL database (or Neon account)

### Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:

```
SECRET_KEY=your-secret-key
FLASK_ENV=development
FRONTEND_URL=http://localhost:3000
DATABASE_URL=postgresql://user:password@host/database
```

3. Run the server:

```bash
python run.py
```

The server will start on `http://localhost:8000`

## Database

The application uses SQLAlchemy with PostgreSQL. The database schema is automatically created on first run.

### User Table Schema

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL
);
```

## Project Structure

```
backend/
├── models/          # SQLAlchemy database models
│   ├── __init__.py
│   └── user.py     # User model
├── routes/          # API route handlers
│   ├── __init__.py
│   └── auth.py     # Authentication routes
├── services/        # Business logic layer
│   ├── __init__.py
│   └── user_service.py  # User management service
├── config.py        # Application configuration
├── database.py      # Database connection and setup
├── run.py          # Application entry point
├── requirements.txt # Python dependencies
└── .env            # Environment variables (not in git)
```

## Security Features

- **Password Hashing**: bcrypt with salt
- **Session Security**: HttpOnly cookies, SameSite protection
- **Input Validation**: Email format and password strength checks
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection
- **CORS Configuration**: Restricted to frontend origin

## Development

The server runs in debug mode by default. For production:

1. Set `FLASK_ENV=production` in `.env`
2. Use a production WSGI server (gunicorn, uWSGI)
3. Enable HTTPS and set `SESSION_COOKIE_SECURE=True`
4. Use a strong `SECRET_KEY`
