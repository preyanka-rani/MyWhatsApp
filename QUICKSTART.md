# Quick Start Guide - WhatsApp Clone API

This guide will help you get the WhatsApp Clone API up and running in under 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- Git installed

## Step 1: Clone and Setup

```bash
# Clone the repository
cd MyWhatsApp

# Copy environment file
cp .env.example .env
```

## Step 2: Configure Environment

Open `.env` and ensure these critical values are set:

```env
# Required - WhatsApp Business API (Use provided values or get from Meta)
WHATSAPP_ACCESS_TOKEN=EAARmI6vCLQYBQAZBAVUjHmQeCyOcBnrmtowwR4vxUZAzBzYrj3ZAagaTvTSXcCUVTtFgCGYNuDZCqQ4o1PJNcDvtMdrLTAo4GhTbjOMu2D9EDjIY2KB96bk0zIjT0ugIpi3KNN2mR98xBZA9ZAA2uiIDm6adiK31TnVewbHnAc7EEChgjCJF5xPZBFkxXmB0AZDZD
WHATSAPP_PHONE_NUMBER_ID=899470373245308
WHATSAPP_BUSINESS_ACCOUNT_ID=1357342392543789
VERIFY_TOKEN=my_verify_token_123

# Required - JWT Secret (CHANGE THIS!)
SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
```

> **Note**: For development, Twilio and AWS S3 are optional. The system will work without them using mock OTP and local file storage.

## Step 3: Start with Docker

```bash
# Start all services
docker-compose up -d

# Check if services are running
docker-compose ps
```

You should see these services running:
- ✅ whatsapp_postgres
- ✅ whatsapp_redis
- ✅ whatsapp_app
- ✅ whatsapp_celery_worker
- ✅ whatsapp_celery_beat
- ✅ whatsapp_flower

## Step 4: Verify Installation

Open your browser and visit:
- **API Docs**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health
- **Flower (Task Queue)**: http://localhost:5555

You should see:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

## Step 5: Test Authentication

### A. Request OTP

Using curl:
```bash
curl -X POST http://localhost:8000/api/auth/request-otp \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890"}'
```

Response (development mode):
```json
{
  "status": "success",
  "message": "OTP generated (development mode)",
  "otp": "123456",
  "expires_in": 300
}
```

### B. Verify OTP and Get Token

```bash
curl -X POST http://localhost:8000/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+1234567890",
    "otp_code": "123456"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "...",
    "phone_number": "+1234567890",
    "name": "+1234567890",
    "is_online": false
  }
}
```

**Save this token!** You'll need it for all subsequent requests.

## Step 6: Test Sending a Message

### A. Create Another User

Repeat Step 5 with a different phone number (e.g., `+0987654321`) and save that token as `TOKEN_2`.

### B. Create a Conversation

Using your first user's token:
```bash
curl -X POST http://localhost:8000/api/conversations \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "participant_ids": ["USER_2_ID_HERE"]
  }'
```

Response:
```json
{
  "id": "conversation-uuid-here",
  "type": "DIRECT",
  ...
}
```

### C. Send a Message

```bash
curl -X POST http://localhost:8000/api/conversations/CONVERSATION_ID/messages \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "CONVERSATION_ID",
    "type": "TEXT",
    "content": "Hello, World! 🚀"
  }'
```

## Step 7: Test WebSocket (Real-time)

### Using Python

```bash
cd examples
python websocket_client.py
```

Enter your JWT token when prompted and test real-time features!

### Using Browser Console

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=YOUR_TOKEN_HERE');

ws.onopen = () => {
  console.log('✅ Connected!');
  
  // Send typing indicator
  ws.send(JSON.stringify({
    type: 'typing_indicator',
    conversation_id: 'CONVERSATION_ID',
    is_typing: true
  }));
};

ws.onmessage = (event) => {
  console.log('📨 Received:', JSON.parse(event.data));
};
```

## Common Issues & Solutions

### Issue: Port already in use

```bash
# Stop and remove containers
docker-compose down

# Change ports in docker-compose.yml
# Then restart
docker-compose up -d
```

### Issue: Database connection error

```bash
# Check database logs
docker-compose logs postgres

# Recreate database
docker-compose down -v
docker-compose up -d
```

### Issue: Redis connection error

```bash
# Check Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

## Next Steps

1. **Explore the API** - Visit http://localhost:8000/docs
2. **Import Postman Collection** - Use `postman_collection.json`
3. **Read Full Documentation** - See `README.md`
4. **Set up WhatsApp Webhook** - Configure webhook URL in Meta Developer Console
5. **Deploy to Production** - Follow deployment guide in README

## Useful Commands

```bash
# View logs
docker-compose logs -f app

# Restart a service
docker-compose restart app

# Stop all services
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v

# Run without Docker
uvicorn app.main:app --reload
```

## API Quick Reference

### Authentication
- `POST /api/auth/request-otp` - Get OTP
- `POST /api/auth/verify-otp` - Login with OTP
- `GET /api/auth/users/me` - Get profile
- `PUT /api/auth/users/me` - Update profile

### Messaging
- `POST /api/conversations` - Create chat
- `GET /api/conversations` - List chats
- `POST /api/conversations/{id}/messages` - Send message
- `GET /api/conversations/{id}/messages` - Get messages

### Groups
- `POST /api/groups` - Create group
- `POST /api/groups/{id}/members` - Add member
- `DELETE /api/groups/{id}/members/{user_id}` - Remove member

### Media
- `POST /api/media` - Upload file
- `GET /api/media/{id}` - Get file info

### WebSocket
- `WS /ws?token={jwt}` - Real-time connection

## Success! 🎉

You now have a fully functional WhatsApp-like messaging system running locally!

For production deployment and advanced configuration, see the main README.md file.

## Support

- GitHub Issues: [Create an issue]
- Documentation: See README.md
- API Docs: http://localhost:8000/docs
