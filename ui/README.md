# WhatsApp Web Clone UI

A complete WhatsApp Web-like interface that connects to the WhatsApp backend API.

## Features

✅ **Authentication**
- Phone number + OTP login
- JWT token-based authentication
- Auto-login if token exists

✅ **Real-time Messaging**
- Send and receive messages instantly
- WebSocket connection for live updates
- Message status indicators (sent, delivered, read)
- Typing indicators

✅ **Conversations**
- View all conversations
- Create new conversations by phone number
- Search conversations
- Last message preview
- Timestamps

✅ **User Interface**
- WhatsApp-like dark theme
- Responsive design (mobile & desktop)
- Smooth animations
- Toast notifications
- Loading states

## How to Use

### 1. Start the Backend

Make sure the backend server is running:

```powershell
cd e:\MyWhatsApp
python app.py
```

Backend will run at: `http://localhost:8000`

**IMPORTANT:** If you get CORS errors, make sure you've restarted the backend after the CORS fix was applied.

### 2. Serve the UI

**Option A: Using Python HTTP Server (Recommended)**

```powershell
cd e:\MyWhatsApp\ui
python -m http.server 8080
```

Then open: `http://localhost:8080`

**Option B: Open HTML file directly**

```powershell
# From project root
start ui\index.html
```

**Option C: Use the startup script**

```powershell
# This starts both backend and UI
.\start.ps1
```

### 3. Login

1. Enter your phone number (e.g., `+8801608529761`)
2. Click "Request OTP"
3. Check your console/logs for the OTP code (or receive it via WhatsApp if configured)
4. Enter the 6-digit OTP
5. Click "Verify & Login"

### 4. Start Chatting

1. Click the **New Chat** button (message icon)
2. Enter the recipient's phone number (e.g., `+8801980680622`)
3. Click "Start Chat"
4. Type your message and press Enter or click send button

## File Structure

```
ui/
├── index.html          # Main HTML file
├── css/
│   └── styles.css      # All styling (WhatsApp theme)
├── js/
│   ├── config.js       # Configuration (API URLs)
│   ├── auth.js         # Authentication logic
│   ├── chat.js         # Chat & messaging logic
│   ├── websocket.js    # WebSocket connection
│   └── app.js          # Main application logic
└── README.md           # This file
```

## Configuration

Edit `js/config.js` to change API endpoints:

```javascript
const API_BASE_URL = 'http://localhost:8000/api';
const WS_BASE_URL = 'ws://localhost:8000/ws';
```

## Features Breakdown

### Authentication Flow
1. User enters phone number
2. Backend sends OTP
3. User enters OTP
4. Backend returns JWT token
5. Token stored in localStorage
6. Auto-login on page refresh

### Messaging Flow
1. User creates conversation with phone number
2. Backend searches for user by phone
3. Conversation created with user ID
4. Messages sent via REST API
5. Messages received via WebSocket
6. UI updates in real-time

### WebSocket Events

**Sent by Client:**
- `send_message` - Send a message
- `typing` - Typing indicator

**Received from Server:**
- `new_message` - New message received
- `message_status` - Message status update
- `typing` - Someone is typing
- `presence` - User online/offline status

## Browser Support

- Chrome (recommended)
- Firefox
- Edge
- Safari
- Opera

## Responsive Design

- Desktop: Full 3-column layout (sidebar, chat list, chat area)
- Mobile: Single view with navigation between sections

## Keyboard Shortcuts

- **Enter**: Send message
- **Shift + Enter**: New line in message
- **Esc**: Close modals
- **Ctrl + K**: Focus search (if implemented)

## Troubleshooting

### 1. "Failed to load conversations"
**Solution**: Make sure backend is running at `http://localhost:8000`

### 2. "Connection refused" or CORS errors
**Solution**: Backend must allow CORS from your UI origin. Check `app/main.py` CORS settings.

### 3. "Disconnected from chat server"
**Solution**: 
- Check if WebSocket endpoint is available
- Ensure token is valid
- Check browser console for errors

### 4. "User not found with this phone number"
**Solution**: 
- User must be registered in the system first
- Try logging in with that phone number first to create the user

### 5. Messages not updating in real-time
**Solution**:
- Check WebSocket connection status (green indicator)
- Fallback: UI polls for new messages every 3 seconds

## Development

### To modify styles:
Edit `css/styles.css` - uses CSS variables for easy theming

### To add features:
- Authentication: Edit `js/auth.js`
- Chat logic: Edit `js/chat.js`
- WebSocket: Edit `js/websocket.js`
- UI logic: Edit `js/app.js`

## API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/request-otp` | POST | Request OTP for phone number |
| `/api/auth/verify-otp` | POST | Verify OTP and get token |
| `/api/auth/users/me` | GET | Get current user profile |
| `/api/auth/users/search` | GET | Search user by phone number |
| `/api/conversations/` | GET | Get all conversations |
| `/api/conversations/` | POST | Create new conversation |
| `/api/conversations/{id}/messages` | GET | Get messages in conversation |
| `/api/conversations/{id}/messages` | POST | Send message in conversation |
| `/ws/chat?token={token}` | WebSocket | Real-time chat connection |

## Security

- All API requests require JWT authentication
- Token stored in localStorage (can be migrated to httpOnly cookies)
- WebSocket connection requires valid token
- XSS protection via HTML escaping

## Future Enhancements

- [ ] File/image upload
- [ ] Voice messages
- [ ] Message search
- [ ] User profile editing
- [ ] Group chats
- [ ] Message reactions
- [ ] Message deletion
- [ ] Read receipts
- [ ] Notifications API
- [ ] Dark/Light theme toggle
- [ ] Settings page

## Credits

UI design inspired by WhatsApp Web
Built for the MyWhatsApp backend project

## License

This is a demo/educational project.
