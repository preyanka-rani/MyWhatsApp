# Local Development Setup Guide

This guide helps you set up PostgreSQL and Redis locally on Windows without Docker.

## Prerequisites

- Python 3.11+ installed
- Conda environment activated (`conda activate wp`)

## Step 1: Install PostgreSQL (Windows)

### Option A: Using Chocolatey (Recommended)
```powershell
# Install Chocolatey if not installed
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install PostgreSQL
choco install postgresql15 -y

# Refresh environment
refreshenv
```

### Option B: Manual Download
1. Download PostgreSQL 15 from: https://www.postgresql.org/download/windows/
2. Run installer
3. Remember the password you set for postgres user
4. Default port: 5432

### Configure PostgreSQL
```powershell
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE whatsapp_db;
CREATE USER whatsapp_user WITH PASSWORD 'whatsapp_password';
GRANT ALL PRIVILEGES ON DATABASE whatsapp_db TO whatsapp_user;
\q
```

## Step 2: Install Redis (Windows)

### Option A: Using Chocolatey (Recommended)
```powershell
# Install Redis
choco install redis-64 -y

# Start Redis service
redis-server --service-start

# Test Redis
redis-cli ping
# Should return: PONG
```

### Option B: Manual Installation
1. Download Redis from: https://github.com/microsoftarchive/redis/releases
2. Extract to `C:\Redis`
3. Run `redis-server.exe`

### Option C: Using WSL (Linux Subsystem)
```bash
# In WSL terminal
sudo apt update
sudo apt install redis-server -y
sudo service redis-server start
redis-cli ping
```

### Option D: Using Memurai (Redis Alternative)
1. Download from: https://www.memurai.com/get-memurai
2. Install and it runs as Windows service

## Step 3: Verify Services

### Check PostgreSQL
```powershell
# Test connection
psql -U whatsapp_user -d whatsapp_db -W
# Enter password: whatsapp_password

# If successful, you'll see:
# whatsapp_db=>
```

### Check Redis
```powershell
# Test Redis
redis-cli ping
# Should return: PONG

# Check if Redis is running
redis-cli info server
```

## Step 4: Update .env File

Edit your `.env` file with local connection strings:

```env
# Local PostgreSQL
DATABASE_URL=postgresql+asyncpg://whatsapp_user:whatsapp_password@localhost:5432/whatsapp_db

# Local Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

## Step 5: Install Python Dependencies

```powershell
# Make sure you're in the project directory
cd E:\MyWhatsApp

# Install all dependencies
pip install -r requirements.txt
```

## Step 6: Run the Application

```powershell
# Simple way
python app.py

# Or using uvicorn directly
uvicorn app.main:app --reload
```

## Step 7: Test the API

Open browser and visit:
- http://localhost:8000/health
- http://localhost:8000/docs

You should see:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

## Troubleshooting

### PostgreSQL Connection Issues

**Error**: `could not connect to server`
```powershell
# Check if PostgreSQL is running
Get-Service postgresql*

# Start if stopped
Start-Service postgresql-x64-15
```

**Error**: `password authentication failed`
```powershell
# Reset PostgreSQL password
psql -U postgres
ALTER USER whatsapp_user WITH PASSWORD 'whatsapp_password';
```

### Redis Connection Issues

**Error**: `Error connecting to Redis`
```powershell
# Check if Redis is running
redis-cli ping

# Start Redis service
redis-server --service-start

# Or run Redis in terminal
redis-server
```

### Port Already in Use

**Error**: `Address already in use: 8000`
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F

# Or use different port
uvicorn app.main:app --reload --port 8001
```

### Database Migration Issues

**Error**: `relation does not exist`
```powershell
# The app creates tables automatically on startup
# Just restart the app
python app.py
```

## Alternative: Using Docker Desktop (Easier!)

If you have Docker Desktop installed:

```powershell
# Just start everything with Docker
docker-compose up -d

# No need to install PostgreSQL or Redis manually!
```

## Quick Commands Reference

### PostgreSQL
```powershell
# Start PostgreSQL
Start-Service postgresql-x64-15

# Stop PostgreSQL
Stop-Service postgresql-x64-15

# Connect to database
psql -U whatsapp_user -d whatsapp_db
```

### Redis
```powershell
# Start Redis
redis-server --service-start

# Stop Redis
redis-server --service-stop

# Test Redis
redis-cli ping

# Monitor Redis
redis-cli monitor
```

### Application
```powershell
# Run app
python app.py

# Run with auto-reload
uvicorn app.main:app --reload

# Run on different port
uvicorn app.main:app --reload --port 8001

# Run Celery worker (in another terminal)
celery -A app.workers.tasks worker --loglevel=info --pool=solo

# Run Celery beat (in another terminal)
celery -A app.workers.tasks beat --loglevel=info
```

## Next Steps

Once everything is running:

1. Test authentication: http://localhost:8000/docs
2. Try the OTP flow
3. Create a conversation
4. Send messages
5. Test WebSocket: `python examples/websocket_client.py`

## Need Help?

Common issues and solutions:
- **Can't install packages**: Try `pip install --upgrade pip` first
- **Import errors**: Make sure you're in the right directory
- **Database errors**: Check `.env` file has correct credentials
- **Redis errors**: Make sure Redis service is started

Good luck! 🚀
