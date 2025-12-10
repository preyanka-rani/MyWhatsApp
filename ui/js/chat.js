// Chat Manager
class ChatManager {
    constructor() {
        this.conversations = [];
        this.currentConversationId = null;
        this.messages = {};
        this.messagePollingInterval = null;
    }

    // Load all conversations
    async loadConversations() {
        try {
            const response = await authManager.authenticatedRequest('/conversations/');
            
            if (response.ok) {
                this.conversations = await response.json();
                console.log('Loaded conversations:', this.conversations); // Debug log
                this.renderConversations();
                return true;
            } else {
                showToast('Failed to load conversations', 'error');
                return false;
            }
        } catch (error) {
            console.error('Error loading conversations:', error);
            showToast('Error loading conversations', 'error');
            return false;
        }
    }

    // Create new conversation
    async createConversation(phoneNumber, contactName = null) {
        try {
            showLoading();
            
            // Create or get user by phone number (auto-creates if not exists)
            const response = await authManager.authenticatedRequest(
                `/auth/users/create-or-get?phone_number=${encodeURIComponent(phoneNumber)}`,
                {
                    method: 'POST'
                }
            );
            
            if (!response.ok) {
                hideLoading();
                showToast('Failed to add contact', 'error');
                return null;
            }
            
            const user = await response.json();

            // Use provided name or phone number
            const conversationName = contactName || user.phone_number;

            // Create conversation with user ID
            const convResponse = await authManager.authenticatedRequest('/conversations/', {
                method: 'POST',
                body: JSON.stringify({
                    participant_ids: [user.id],
                    name: conversationName
                })
            });

            hideLoading();

            if (convResponse.ok) {
                const conversation = await convResponse.json();
                this.conversations.unshift(conversation);
                this.renderConversations();
                showToast('Contact added successfully!', 'success');
                return conversation;
            } else {
                const error = await convResponse.json();
                showToast(error.detail || 'Failed to create conversation', 'error');
                return null;
            }
        } catch (error) {
            hideLoading();
            console.error('Error creating conversation:', error);
            showToast('Error creating conversation', 'error');
            return null;
        }
    }

    // Load messages for a conversation
    async loadMessages(conversationId) {
        try {
            const response = await authManager.authenticatedRequest(
                `/conversations/${conversationId}/messages`
            );
            
            if (response.ok) {
                const messages = await response.json();
                console.log(`Loaded ${messages.length} messages from API for conversation ${conversationId}`);
                
                // Replace cached messages completely (don't merge)
                this.messages[conversationId] = messages;
                
                this.renderMessages(conversationId);
                return this.messages[conversationId];
            } else {
                showToast('Failed to load messages', 'error');
                return [];
            }
        } catch (error) {
            console.error('Error loading messages:', error);
            showToast('Error loading messages', 'error');
            return [];
        }
    }

    // Send message
    async sendMessage(conversationId, content) {
        try {
            const response = await authManager.authenticatedRequest(
                `/conversations/${conversationId}/messages`,
                {
                    method: 'POST',
                    body: JSON.stringify({
                        type: 'TEXT',
                        content: content
                    })
                }
            );

            if (response.ok) {
                const message = await response.json();
                
                // Add message to local cache
                if (!this.messages[conversationId]) {
                    this.messages[conversationId] = [];
                }
                this.messages[conversationId].push(message);
                
                // Re-render messages
                this.renderMessages(conversationId);
                
                // Update conversation preview
                await this.loadConversations();
                
                return message;
            } else {
                const error = await response.json();
                showToast(error.detail || 'Failed to send message', 'error');
                return null;
            }
        } catch (error) {
            console.error('Error sending message:', error);
            showToast('Error sending message', 'error');
            return null;
        }
    }

    // Select conversation
    async selectConversation(conversationId) {
        this.currentConversationId = conversationId;
        
        // Update UI
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-conversation-id="${conversationId}"]`)?.classList.add('active');
        
        // Show chat container
        document.getElementById('noChatSelected').style.display = 'none';
        document.getElementById('chatContainer').style.display = 'flex';
        
        // Load messages
        await this.loadMessages(conversationId);
        
        // Update chat header
        const conversation = this.conversations.find(c => c.id === conversationId);
        if (conversation) {
            document.getElementById('chatUserName').textContent = conversation.name || 'Chat';
            
            // Update avatar icon based on type
            const chatAvatar = document.getElementById('chatAvatar');
            const iconClass = conversation.type === 'GROUP' ? 'fa-users' : 'fa-user';
            chatAvatar.innerHTML = `<i class="fas ${iconClass}"></i>`;
            
            // Make header clickable for groups
            const chatUserInfo = document.getElementById('chatUserInfo');
            if (conversation.type === 'GROUP') {
                chatUserInfo.style.cursor = 'pointer';
                chatUserInfo.title = 'View group info';
            } else {
                chatUserInfo.style.cursor = 'default';
                chatUserInfo.title = '';
            }
        }
        
        // Disable polling - WebSocket handles real-time updates
        // this.startMessagePolling(conversationId);
        
        // On mobile, show chat area
        if (window.innerWidth <= 768) {
            document.querySelector('.chat-area').classList.add('active');
        }
    }
    
    // Get current conversation
    getCurrentConversation() {
        return this.conversations.find(c => c.id === this.currentConversationId);
    }

    // Start polling for new messages
    startMessagePolling(conversationId) {
        // Clear existing interval
        if (this.messagePollingInterval) {
            clearInterval(this.messagePollingInterval);
        }
        
        // Poll every 3 seconds
        this.messagePollingInterval = setInterval(() => {
            if (this.currentConversationId === conversationId) {
                this.loadMessages(conversationId);
            }
        }, 3000);
    }

    // Stop message polling
    stopMessagePolling() {
        if (this.messagePollingInterval) {
            clearInterval(this.messagePollingInterval);
            this.messagePollingInterval = null;
        }
    }

    // Render conversations list
    renderConversations() {
        const listContainer = document.getElementById('conversationsList');
        
        if (this.conversations.length === 0) {
            listContainer.innerHTML = `
                <div class="no-conversations">
                    <i class="fas fa-comments"></i>
                    <p>No conversations yet</p>
                    <button class="btn btn-primary" onclick="showNewChatModal()">Start New Chat</button>
                </div>
            `;
            return;
        }

        listContainer.innerHTML = this.conversations.map(conv => {
            // Get last message from cache or conversation
            let lastMessage = null;
            let preview = 'Start chatting';
            let time = '';
            
            // Check if we have messages in cache for this conversation
            if (this.messages[conv.id] && this.messages[conv.id].length > 0) {
                const messages = this.messages[conv.id];
                lastMessage = messages[messages.length - 1]; // Get last message
                preview = this.truncateText(lastMessage.content || '', 40);
                time = this.formatTime(lastMessage.created_at);
            }
            
            // Use custom name, fallback to 'Chat' if not available
            const displayName = conv.name || 'Chat';
            
            // Use group icon for GROUP type conversations
            const iconClass = conv.type === 'GROUP' ? 'fa-users' : 'fa-user';

            return `
                <div class="conversation-item" data-conversation-id="${conv.id}" onclick="chatManager.selectConversation('${conv.id}')">
                    <div class="avatar">
                        <i class="fas ${iconClass}"></i>
                    </div>
                    <div class="conversation-info">
                        <div class="conversation-header">
                            <span class="conversation-name">${this.escapeHtml(displayName)}</span>
                            <span class="conversation-time">${time}</span>
                        </div>
                        <div class="conversation-preview">${this.escapeHtml(preview)}</div>
                    </div>
                </div>
            `;
        }).join('');
    }

    // Render messages
    renderMessages(conversationId) {
        const messagesArea = document.getElementById('messagesArea');
        const messages = this.messages[conversationId] || [];
        
        if (messages.length === 0) {
            messagesArea.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
                    <i class="fas fa-comments" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                    <p>No messages yet. Start the conversation!</p>
                </div>
            `;
            return;
        }

        const currentUserId = authManager.getCurrentUser()?.id;
        let lastDate = null;

        // Sort messages by created_at (oldest first, recent at bottom)
        // Remove duplicates by id
        const uniqueMessages = Array.from(new Map(messages.map(m => [m.id, m])).values());
        const sortedMessages = uniqueMessages.sort((a, b) => {
            return new Date(a.created_at) - new Date(b.created_at);
        });

        messagesArea.innerHTML = sortedMessages.map(msg => {
            const isSent = msg.sender_id === currentUserId;
            const messageDate = new Date(msg.created_at).toDateString();
            
            let dateHtml = '';
            if (messageDate !== lastDate) {
                dateHtml = `
                    <div class="date-divider">
                        <span>${this.formatDate(msg.created_at)}</span>
                    </div>
                `;
                lastDate = messageDate;
            }

            return `
                ${dateHtml}
                <div class="message ${isSent ? 'sent' : 'received'}">
                    <div class="message-bubble">
                        <div class="message-content">${this.escapeHtml(msg.content)}</div>
                        <div class="message-meta">
                            <span>${this.formatTime(msg.created_at)}</span>
                            ${isSent ? '<i class="fas fa-check-double message-status"></i>' : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        // Scroll to bottom
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }

    // Search conversations
    searchConversations(query) {
        const lowerQuery = query.toLowerCase();
        document.querySelectorAll('.conversation-item').forEach(item => {
            const name = item.querySelector('.conversation-name').textContent.toLowerCase();
            const preview = item.querySelector('.conversation-preview').textContent.toLowerCase();
            
            if (name.includes(lowerQuery) || preview.includes(lowerQuery)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    }

    // Helper: Format time
    formatTime(timestamp) {
        const date = new Date(timestamp);
        // Add 6 hours for Bangladesh timezone (UTC+6)
        date.setHours(date.getHours() + 6);
        // Get hours and minutes
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
    }

    // Helper: Format date
    formatDate(timestamp) {
        const date = new Date(timestamp);
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        if (date.toDateString() === today.toDateString()) {
            return 'Today';
        } else if (date.toDateString() === yesterday.toDateString()) {
            return 'Yesterday';
        } else {
            return date.toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                year: 'numeric' 
            });
        }
    }

    // Helper: Truncate text
    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    // Helper: Escape HTML
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Cleanup
    destroy() {
        this.stopMessagePolling();
    }
}

// Export chat manager
window.chatManager = new ChatManager();
