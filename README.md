# Directed Evolution Portal

A full-stack web application for managing directed evolution experiments and data.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Backend Setup](#2-backend-setup)
  - [3. Frontend Setup](#3-frontend-setup)
  - [4. Environment Configuration](#4-environment-configuration)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
- **Node.js 18+** - [Download Node.js](https://nodejs.org/)
- **pnpm** - Install via: `npm install -g pnpm`
- **Git** - [Download Git](https://git-scm.com/downloads)

**Note:** This project uses [Neon](https://neon.tech/) as a cloud PostgreSQL database, so you don't need to install PostgreSQL locally.

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Directed-Evolution-Portal
```

### 2. Backend Setup

#### 2.1. Navigate to the backend directory

```bash
cd backend
```

#### 2.2. Create a Python virtual environment

**On Windows:**

```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

#### 2.3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Frontend Setup

#### 3.1. Navigate to the frontend directory

```bash
cd ../frontend
```

#### 3.2. Install frontend dependencies

```bash
pnpm install
```

### 4. Environment Configuration

#### 4.1. Backend Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Secret key for Flask session management
SECRET_KEY=your-secret-key-here

# Database connection string (Neon PostgreSQL)
DATABASE_URL=postgresql://your-neon-connection-string

# Frontend URL for CORS
FRONTEND_URL=http://localhost:3000
```

**Important:** Replace the placeholder values with your actual configuration:

- Generate a secure `SECRET_KEY` (e.g., using `python -c "import secrets; print(secrets.token_hex(32))"`)
- Update `DATABASE_URL` with your Neon database connection string (available in your Neon dashboard)
- Adjust `FRONTEND_URL` if using a different port

**Note:** The Neon connection string should include `?sslmode=require` for secure connections.

#### 4.2. Frontend Environment Variables

Create a `.env.local` file in the `frontend/` directory:

```env
# Frontend environment variables
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## Running the Application

### Option 1: Run Both Frontend and Backend Simultaneously

From the **root directory** of the project:

```bash
npm install
npm run dev
```

This will start:

- Backend server on `http://localhost:8000`
- Frontend development server on `http://localhost:3000`

### Option 2: Run Backend and Frontend Separately

#### Start the Backend Server

```bash
cd backend
# Activate virtual environment first (if not already activated)
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
python run.py
```

The backend API will be available at `http://localhost:8000`

#### Start the Frontend Development Server

In a new terminal:

```bash
cd frontend
pnpm dev
```

The frontend will be available at `http://localhost:3000`

## Project Structure

```
Directed-Evolution-Portal/
├── backend/                 # Flask backend application
│   ├── models/             # Database models
│   ├── routes/             # API route handlers
│   ├── services/           # Business logic
│   ├── config.py           # Application configuration
│   ├── database.py         # Database initialization
│   ├── run.py              # Application entry point
│   └── requirements.txt    # Python dependencies
├── frontend/               # Next.js frontend application
│   ├── app/                # Next.js app directory
│   ├── components/         # React components
│   ├── hooks/              # Custom React hooks
│   ├── lib/                # Utility functions
│   ├── public/             # Static assets
│   └── package.json        # Node.js dependencies
└── package.json            # Root package.json for running both servers
```

## Tech Stack

### Backend

- **Flask** - Python web framework
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL (Neon)** - Serverless PostgreSQL database
- **Flask-CORS** - Cross-Origin Resource Sharing support
- **Flask-Session** - Server-side session management
- **bcrypt** - Password hashing

### Frontend

- **Next.js** - React framework
- **TypeScript** - Type-safe JavaScript
- **Radix UI** - Accessible UI components
- **Tailwind CSS** - Utility-first CSS framework
- **pnpm** - Fast, disk space efficient package manager

## License

This project is licensed under the [MIT License](LICENSE).

## Support

For support, please open an issue in the GitHub repository.
