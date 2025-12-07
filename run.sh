#!/bin/bash
# Run Script for WhatsApp Clone API
# Usage: ./run.sh [command]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

show_help() {
    echo -e "${CYAN}WhatsApp Clone API - Run Script${NC}"
    echo -e "${CYAN}================================${NC}"
    echo ""
    echo -e "${YELLOW}Usage: ./run.sh [command]${NC}"
    echo ""
    echo -e "${GREEN}Commands:${NC}"
    echo "  start         - Start all services with Docker Compose"
    echo "  stop          - Stop all services"
    echo "  restart       - Restart all services"
    echo "  logs          - View application logs"
    echo "  db-reset      - Reset database (WARNING: deletes all data)"
    echo "  test          - Run tests"
    echo "  shell         - Open shell in app container"
    echo "  dev           - Run in development mode (without Docker)"
    echo "  help          - Show this help message"
    echo ""
}

start_services() {
    echo -e "${GREEN}Starting WhatsApp Clone API...${NC}"
    
    # Check if .env exists
    if [ ! -f .env ]; then
        echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env file with your configuration!${NC}"
        return
    fi
    
    docker-compose up -d
    echo ""
    echo -e "${GREEN}Services started successfully!${NC}"
    echo -e "${CYAN}API: http://localhost:8000${NC}"
    echo -e "${CYAN}Docs: http://localhost:8000/docs${NC}"
    echo -e "${CYAN}Flower: http://localhost:5555${NC}"
}

stop_services() {
    echo -e "${YELLOW}Stopping services...${NC}"
    docker-compose down
    echo -e "${GREEN}Services stopped.${NC}"
}

restart_services() {
    echo -e "${YELLOW}Restarting services...${NC}"
    docker-compose restart
    echo -e "${GREEN}Services restarted.${NC}"
}

show_logs() {
    echo -e "${CYAN}Showing logs (Ctrl+C to exit)...${NC}"
    docker-compose logs -f app
}

reset_database() {
    echo -e "${RED}WARNING: This will delete all data!${NC}"
    read -p "Are you sure? (yes/no): " confirm
    
    if [ "$confirm" = "yes" ]; then
        echo -e "${YELLOW}Resetting database...${NC}"
        docker-compose down -v
        docker-compose up -d
        echo -e "${GREEN}Database reset complete.${NC}"
    else
        echo -e "${YELLOW}Cancelled.${NC}"
    fi
}

run_tests() {
    echo -e "${CYAN}Running tests...${NC}"
    docker-compose exec app pytest
}

open_shell() {
    echo -e "${CYAN}Opening shell in app container...${NC}"
    docker-compose exec app /bin/bash
}

start_dev() {
    echo -e "${GREEN}Starting in development mode...${NC}"
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
    
    # Install dependencies
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
    
    # Run application
    echo -e "${GREEN}Starting application...${NC}"
    echo -e "${CYAN}API will be available at http://localhost:8000${NC}"
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

# Execute command
case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        show_logs
        ;;
    db-reset)
        reset_database
        ;;
    test)
        run_tests
        ;;
    shell)
        open_shell
        ;;
    dev)
        start_dev
        ;;
    help|"")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
