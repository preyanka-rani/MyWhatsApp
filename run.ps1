# Run Script for WhatsApp Clone API
# Usage: .\run.ps1 [command]

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "WhatsApp Clone API - Run Script" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\run.ps1 [command]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Green
    Write-Host "  start         - Start all services with Docker Compose"
    Write-Host "  stop          - Stop all services"
    Write-Host "  restart       - Restart all services"
    Write-Host "  logs          - View application logs"
    Write-Host "  db-reset      - Reset database (WARNING: deletes all data)"
    Write-Host "  test          - Run tests"
    Write-Host "  shell         - Open shell in app container"
    Write-Host "  dev           - Run in development mode (without Docker)"
    Write-Host "  help          - Show this help message"
    Write-Host ""
}

function Start-Services {
    Write-Host "Starting WhatsApp Clone API..." -ForegroundColor Green
    
    # Check if .env exists
    if (-not (Test-Path ".env")) {
        Write-Host "Creating .env file from .env.example..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "Please edit .env file with your configuration!" -ForegroundColor Yellow
        return
    }
    
    docker-compose up -d
    Write-Host ""
    Write-Host "Services started successfully!" -ForegroundColor Green
    Write-Host "API: http://localhost:8000" -ForegroundColor Cyan
    Write-Host "Docs: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "Flower: http://localhost:5555" -ForegroundColor Cyan
}

function Stop-Services {
    Write-Host "Stopping services..." -ForegroundColor Yellow
    docker-compose down
    Write-Host "Services stopped." -ForegroundColor Green
}

function Restart-Services {
    Write-Host "Restarting services..." -ForegroundColor Yellow
    docker-compose restart
    Write-Host "Services restarted." -ForegroundColor Green
}

function Show-Logs {
    Write-Host "Showing logs (Ctrl+C to exit)..." -ForegroundColor Cyan
    docker-compose logs -f app
}

function Reset-Database {
    Write-Host "WARNING: This will delete all data!" -ForegroundColor Red
    $confirm = Read-Host "Are you sure? (yes/no)"
    
    if ($confirm -eq "yes") {
        Write-Host "Resetting database..." -ForegroundColor Yellow
        docker-compose down -v
        docker-compose up -d
        Write-Host "Database reset complete." -ForegroundColor Green
    } else {
        Write-Host "Cancelled." -ForegroundColor Yellow
    }
}

function Run-Tests {
    Write-Host "Running tests..." -ForegroundColor Cyan
    docker-compose exec app pytest
}

function Open-Shell {
    Write-Host "Opening shell in app container..." -ForegroundColor Cyan
    docker-compose exec app /bin/bash
}

function Start-Dev {
    Write-Host "Starting in development mode..." -ForegroundColor Green
    
    # Check if virtual environment exists
    if (-not (Test-Path "venv")) {
        Write-Host "Creating virtual environment..." -ForegroundColor Yellow
        python -m venv venv
    }
    
    # Activate virtual environment
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    .\venv\Scripts\Activate.ps1
    
    # Install dependencies
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
    
    # Run application
    Write-Host "Starting application..." -ForegroundColor Green
    Write-Host "API will be available at http://localhost:8000" -ForegroundColor Cyan
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

# Execute command
switch ($Command.ToLower()) {
    "start" { Start-Services }
    "stop" { Stop-Services }
    "restart" { Restart-Services }
    "logs" { Show-Logs }
    "db-reset" { Reset-Database }
    "test" { Run-Tests }
    "shell" { Open-Shell }
    "dev" { Start-Dev }
    "help" { Show-Help }
    default { 
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
    }
}
