// WebSocket Manager
class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.isConnecting = false;
    }

    // Connect to WebSocket
    connect() {
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            console.log('WebSocket already connected or connecting');
            return;
        }

        if (this.isConnecting) {
            console.log('Connection attempt already in progress');
            return;
        }

        const token = authManager.getToken();
        if (!token) {
            console.error('No authentication token available');
            return;
        }

        try {
            this.isConnecting = true;
            const wsUrl = `${CONFIG.WS_BASE_URL}/ws?token=${encodeURIComponent(token)}`;
            console.log('Connecting to WebSocket...');
            
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnecting = false;
                this.reconnectAttempts = 0;
                showToast('Connected to chat server', 'success');
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.isConnecting = false;
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);
                this.isConnecting = false;
                this.ws = null;

                // Attempt to reconnect
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`Reconnecting... Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
                    setTimeout(() => this.connect(), this.reconnectDelay);
                } else {
                    showToast('Disconnected from chat server', 'warning');
                }
            };
        } catch (error) {
            console.error('Error creating WebSocket connection:', error);
            this.isConnecting = false;
        }
    }

    // Handle incoming WebSocket messages
    handleMessage(data) {
        console.log('WebSocket message received:', data);

        switch (data.type) {
            case 'new_message':
                // Handle both data.message and data.data for compatibility
                const messageData = data.message || data.data;
                if (messageData) {
                    this.handleNewMessage(messageData);
                } else {
                    console.error('No message data found in WebSocket message');
                }
                break;
            
            case 'group_created':
                this.handleGroupCreated(data.data);
                break;
            
            case 'message_status':
                this.handleMessageStatus(data.data || data.status);
                break;
            
            case 'typing':
                this.handleTypingIndicator(data.data || data.typing);
                break;
            
            case 'presence':
                this.handlePresenceUpdate(data.data || data.presence);
                break;
            
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    // Handle new message
    async handleNewMessage(message) {
        const conversationId = message.conversation_id;
        
        console.log('Handling new message:');
        console.log('- Message conversation_id:', conversationId);
        console.log('- Current conversation_id:', chatManager.currentConversationId);
        console.log('- Match:', conversationId === chatManager.currentConversationId);
        console.log('- Full message:', message);
        
        // Translate message if user has preferred language and it's not from current user
        const currentUserId = authManager.getCurrentUser()?.id;
        const preferredLang = authManager.user?.preferred_language;
        
        if (preferredLang && preferredLang !== 'en' && message.sender_id !== currentUserId && message.type === 'TEXT') {
            console.log(`Translating WebSocket message to ${preferredLang}...`);
            // Note: Translation will happen when messages are loaded from API
            // For now, we'll let the API handle translation on next load
        }
        
        // Add message to local cache
        if (!chatManager.messages[conversationId]) {
            chatManager.messages[conversationId] = [];
        }
        
        // Check if message already exists (prevent duplicates)
        const exists = chatManager.messages[conversationId].some(m => m.id === message.id);
        
        if (!exists) {
            chatManager.messages[conversationId].push(message);
            console.log('Message added to cache. Total messages:', chatManager.messages[conversationId].length);
            
            // If this is the current conversation, reload from API to get translated version
            if (chatManager.currentConversationId === conversationId && preferredLang && preferredLang !== 'en') {
                console.log('Reloading messages from API to get translation...');
                // Small delay to ensure message is saved in backend
                setTimeout(async () => {
                    await chatManager.loadMessages(conversationId);
                    chatManager.renderMessages(conversationId);
                }, 500);
            } else {
                // Otherwise just render what we have
                if (chatManager.currentConversationId === conversationId) {
                    console.log('Re-rendering messages for current conversation');
                    chatManager.renderMessages(conversationId);
                }
            }
            
            // Update conversations list to show latest message
            chatManager.loadConversations();
            
            // Show notification if not current conversation
            if (message.sender_id !== currentUserId && chatManager.currentConversationId !== conversationId) {
                showToast('New message received', 'info');
            }
        } else {
            console.log('Message already exists, skipping');
        }
    }

    // Handle message status update
    handleMessageStatus(data) {
        console.log('Message status update:', data);
        // Update message status in UI if needed
    }

    // Handle typing indicator
    handleTypingIndicator(data) {
        if (chatManager.currentConversationId === data.conversation_id) {
            const statusEl = document.getElementById('chatUserStatus');
            if (statusEl) {
                if (data.is_typing) {
                    statusEl.textContent = 'typing...';
                } else {
                    statusEl.textContent = 'online';
                }
            }
        }
    }

    // Handle presence update
    handlePresenceUpdate(data) {
        console.log('Presence update:', data);
        // Update user status in UI if needed
    }

    // Handle group created notification
    handleGroupCreated(groupData) {
        console.log('Group created notification:', groupData);
        showToast(`New group created: ${groupData.name}`, 'success');
        
        // Reload conversations to show the new group
        chatManager.loadConversations();
    }

    // Send message via WebSocket
    sendMessage(conversationId, content) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = {
                type: 'send_message',
                data: {
                    conversation_id: conversationId,
                    content: content
                }
            };
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected, cannot send message');
        }
    }

    // Send typing indicator
    sendTypingIndicator(conversationId, isTyping) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = {
                type: 'typing',
                data: {
                    conversation_id: conversationId,
                    is_typing: isTyping
                }
            };
            this.ws.send(JSON.stringify(message));
        }
    }

    // Disconnect WebSocket
    disconnect() {
        if (this.ws) {
            this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
            this.ws.close();
            this.ws = null;
        }
    }

    // Check if connected
    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

// Export WebSocket manager
window.wsManager = new WebSocketManager();
