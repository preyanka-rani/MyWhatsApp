# WhatsApp Clone Backend API

A complete, production-ready WhatsApp-like messaging system built with FastAPI, PostgreSQL, Redis, and WebSockets.

## 🚀 Features

### Core Functionality
- **Phone Number Authentication** - OTP-based login with JWT tokens
- **1:1 Messaging** - Direct messaging between users
- **Group Chats** - Create groups, manage members, admin roles
- **Media Sharing** - Send/receive images, videos, audio, documents with S3 storage
  - Automatic thumbnail generation for images
  - Support for multiple file formats (JPEG, PNG, MP4, PDF, etc.)
  - WhatsApp Business API integration for media
  - Real-time media broadcasting via WebSocket
- **Real-time Communication** - WebSocket support for instant messaging
- **Message Status** - SENT, DELIVERED, READ receipts
- **Presence System** - Online/offline status, last seen
- **Typing Indicators** - Real-time typing status
- **Message Search** - Full-text search across conversations
- **WhatsApp Business API Integration** - Send/receive messages via WhatsApp

### Technical Features
- **Async Architecture** - Fully asynchronous with asyncio and AsyncIO PostgreSQL
- **Redis Pub/Sub** - Real-time message broadcasting
- **Background Workers** - Celery for async task processing
- **S3 Media Storage** - Scalable media file storage
- **Docker Support** - Complete Docker Compose setup
- **OOP Design** - Clean, maintainable code following SOLID principles
- **OpenAPI Documentation** - Auto-generated API docs

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- AWS S3 Account (optional for media storage)
- WhatsApp Business API credentials
- Twilio Account (optional for OTP)

## 🛠️ Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd MyWhatsApp
```

### 2. Environment Setup

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
- WhatsApp Business API tokens
- Database credentials
- Redis URL
- AWS S3 credentials
- JWT secret key
- Twilio credentials (for OTP)

### 3. Docker Compose Setup

Start all services:

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database
- Redis
- FastAPI application
- Celery worker
- Celery beat scheduler
- Flower (Celery monitoring)

### 4. Manual Setup (Without Docker)

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the application:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Start Celery worker:

```bash
celery -A app.workers.tasks worker --loglevel=info
```

Start Celery beat:

```bash
celery -A app.workers.tasks beat --loglevel=info
```

## 🌐 API Endpoints

### Authentication
```
POST   /api/auth/request-otp     - Request OTP for phone number
POST   /api/auth/verify-otp      - Verify OTP and get JWT token
GET    /api/auth/users/me        - Get current user profile
PUT    /api/auth/users/me        - Update user profile
```

### Conversations
```
POST   /api/conversations              - Create new conversation
GET    /api/conversations              - List user's conversations
GET    /api/conversations/{id}         - Get conversation details
```

### Messages
```
POST   /api/conversations/{id}/messages     - Send message
GET    /api/conversations/{id}/messages     - Get messages (paginated)
PATCH  /api/conversations/messages/{id}     - Edit message
DELETE /api/conversations/messages/{id}     - Delete message
GET    /api/conversations/messages/search   - Search messages
```

### Groups
```
POST   /api/groups                          - Create group
GET    /api/groups/{id}                     - Get group details
PATCH  /api/groups/{id}                     - Update group settings
POST   /api/groups/{id}/members             - Add member
DELETE /api/groups/{id}/members/{user_id}  - Remove member
GET    /api/groups/{id}/members             - List members
```

### Media
```
POST   /api/media        - Upload media file
GET    /api/media/{id}   - Get media details
```

### Webhooks
```
GET    /api/webhook      - Verify webhook (WhatsApp)
POST   /api/webhook      - Receive webhook events
```

### WebSocket
```
WS     /ws?token={jwt}   - WebSocket connection
```

## 🔌 WebSocket Events

### Client → Server
```json
{
  "type": "typing_indicator",
  "conversation_id": "uuid",
  "is_typing": true
}
```

```json
{
  "type": "heartbeat"
}
```

```json
{
  "type": "message_read",
  "message_id": "uuid"
}
```

### Server → Client
```json
{
  "type": "new_message",
  "message_id": "uuid",
  "conversation_id": "uuid",
  "sender_id": "uuid",
  "content": "Hello!"
}
```

```json
{
  "type": "typing_indicator",
  "conversation_id": "uuid",
  "user_id": "uuid",
  "is_typing": true
}
```

```json
{
  "type": "presence_update",
  "user_id": "uuid",
  "is_online": true
}
```

## 📖 Usage Examples

### 1. Authentication Flow

```python
import requests

# Request OTP
response = requests.post(
    "http://localhost:8000/api/auth/request-otp",
    json={"phone_number": "+1234567890"}
)

# Verify OTP
response = requests.post(
    "http://localhost:8000/api/auth/verify-otp",
    json={
        "phone_number": "+1234567890",
        "otp_code": "123456"
    }
)

token = response.json()["access_token"]
```

### 2. Send Message

```python
headers = {"Authorization": f"Bearer {token}"}

response = requests.post(
    f"http://localhost:8000/api/conversations/{conversation_id}/messages",
    headers=headers,
    json={
        "conversation_id": conversation_id,
        "type": "TEXT",
        "content": "Hello, World!"
    }
)
```

### 3. WebSocket Connection

```python
import asyncio
import websockets
import json

async def connect():
    uri = f"ws://localhost:8000/ws?token={token}"
    
    async with websockets.connect(uri) as websocket:
        # Send typing indicator
        await websocket.send(json.dumps({
            "type": "typing_indicator",
            "conversation_id": conversation_id,
            "is_typing": True
        }))
        
        # Receive messages
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

asyncio.run(connect())
```

## 🏗️ Project Structure

```
MyWhatsApp/
├── app/
│   ├── api/                    # API endpoints
│   │   ├── auth.py            # Authentication routes
│   │   ├── conversations.py   # Conversation routes
│   │   ├── messages.py        # Message routes
│   │   ├── groups.py          # Group routes
│   │   ├── media.py           # Media upload routes
│   │   ├── webhook.py         # WhatsApp webhook
│   │   └── dependencies.py    # FastAPI dependencies
│   ├── core/                   # Core configuration
│   │   ├── config.py          # Settings management
│   │   ├── security.py        # JWT & password hashing
│   │   ├── database.py        # Database session
│   │   └── redis.py           # Redis connection
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── media.py
│   │   └── group.py
│   ├── services/               # Business logic
│   │   ├── whatsapp_client.py
│   │   ├── media_manager.py
│   │   ├── message_service.py
│   │   ├── group_service.py
│   │   ├── presence_service.py
│   │   ├── notification_service.py
│   │   └── otp_service.py
│   ├── websocket/              # WebSocket handling
│   │   ├── manager.py
│   │   └── routes.py
│   ├── workers/                # Celery tasks
│   │   └── tasks.py
│   ├── schemas/                # Pydantic schemas
│   │   └── __init__.py
│   ├── utils/                  # Utilities
│   │   └── __init__.py
│   └── main.py                 # FastAPI application
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## 🧪 Testing

Run tests (if implemented):

```bash
pytest
```

## 📊 Monitoring

### Flower (Celery Monitoring)
Access Flower dashboard at: http://localhost:5555

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔒 Security

- JWT token authentication
- Password hashing with bcrypt
- CORS protection
- Environment variable protection
- Rate limiting (recommended to add)
- SQL injection prevention via SQLAlchemy ORM

## 🚀 Deployment

### Production Checklist
1. Change `SECRET_KEY` to a strong random value
2. Set `DEBUG=False`
3. Configure proper CORS origins
4. Set up SSL/TLS certificates
5. Use managed database services
6. Configure S3 bucket policies
7. Set up monitoring and logging
8. Configure backup strategies
9. Set up CI/CD pipeline

### Docker Production Build

```bash
docker build -t whatsapp-api:prod .
docker run -p 8000:8000 --env-file .env whatsapp-api:prod
```

## 📝 License

This project is for educational purposes.

## 🤝 Contributing

Contributions are welcome! Please follow the code style and add tests for new features.

## 📧 Support

For issues and questions, please open an issue in the repository.

## 🙏 Acknowledgments

- FastAPI framework
- SQLAlchemy ORM
- WhatsApp Business API
- Redis pub/sub system
