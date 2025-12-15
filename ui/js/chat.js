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
    async sendMessage(conversationId, content, messageType = 'TEXT', mediaId = null) {
        try {
            const response = await authManager.authenticatedRequest(
                `/conversations/${conversationId}/messages`,
                {
                    method: 'POST',
                    body: JSON.stringify({
                        type: messageType,
                        content: content,
                        media_id: mediaId
                    })
                }
            );

            if (response.ok) {
                const message = await response.json();
                
                console.log('Message sent successfully:', message.id);
                
                // Store sent message ID temporarily
                if (!this.sentMessageIds) {
                    this.sentMessageIds = new Set();
                }
                this.sentMessageIds.add(message.id);
                
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

    // Upload media file
    async uploadMedia(file) {
        try {
            console.log('Uploading file:', file.name, file.type, file.size);
            showLoading();
            
            const formData = new FormData();
            formData.append('file', file);
            
            console.log('FormData created, sending request...');
            const response = await authManager.authenticatedRequest(
                '/media',
                {
                    method: 'POST',
                    body: formData,
                    skipContentType: true // Don't set Content-Type, let browser handle it
                }
            );
            
            hideLoading();
            
            console.log('Response status:', response.status);
            
            if (response.ok) {
                const media = await response.json();
                console.log('Media uploaded:', media);
                showToast('Media uploaded successfully!', 'success');
                return media;
            } else {
                const errorText = await response.text();
                console.error('Upload failed:', response.status, errorText);
                try {
                    const error = JSON.parse(errorText);
                    showToast(error.detail || 'Failed to upload media', 'error');
                } catch {
                    showToast(`Failed to upload media: ${response.status}`, 'error');
                }
                return null;
            }
        } catch (error) {
            hideLoading();
            console.error('Error uploading media:', error);
            showToast('Error uploading media: ' + error.message, 'error');
            return null;
        }
    }

    // Send media message
    async sendMediaMessage(conversationId, file, caption = '') {
        try {
            // Upload media first
            const media = await this.uploadMedia(file);
            if (!media) return null;
            
            // Determine message type from MIME type
            let messageType = 'DOCUMENT';
            if (media.mime_type.startsWith('image/')) {
                messageType = 'IMAGE';
            } else if (media.mime_type.startsWith('video/')) {
                messageType = 'VIDEO';
            } else if (media.mime_type.startsWith('audio/')) {
                messageType = 'AUDIO';
            }
            
            // Send message with media
            return await this.sendMessage(conversationId, caption, messageType, media.id);
        } catch (error) {
            console.error('Error sending media message:', error);
            showToast('Error sending media message', 'error');
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

            // Generate media content if present
            let mediaContent = '';
            let hasMedia = false;
            if (msg.media && msg.media.url) {
                hasMedia = true;
                const media = msg.media;
                // Ensure media URLs are absolute
                const mediaUrl = media.url.startsWith('http') ? media.url : `http://localhost:8000${media.url}`;
                const thumbnailUrl = media.thumbnail_url ? 
                    (media.thumbnail_url.startsWith('http') ? media.thumbnail_url : `http://localhost:8000${media.thumbnail_url}`) 
                    : mediaUrl;
                
                if (msg.type === 'IMAGE') {
                    mediaContent = `
                        <div class="message-media">
                            <img src="${thumbnailUrl}" 
                                 alt="${media.filename}"
                                 onclick="window.open('${mediaUrl}', '_blank')">
                        </div>
                    `;
                } else if (msg.type === 'VIDEO') {
                    mediaContent = `
                        <div class="message-media">
                            <video controls>
                                <source src="${mediaUrl}" type="${media.mime_type}">
                                Your browser does not support video playback.
                            </video>
                        </div>
                    `;
                } else if (msg.type === 'AUDIO') {
                    mediaContent = `
                        <div class="message-media">
                            <audio controls>
                                <source src="${mediaUrl}" type="${media.mime_type}">
                                Your browser does not support audio playback.
                            </audio>
                        </div>
                    `;
                } else if (msg.type === 'DOCUMENT') {
                    mediaContent = `
                        <div class="message-media message-document">
                            <a href="${mediaUrl}" target="_blank" download="${media.filename}">
                                <i class="fas fa-file-${this.getDocumentIcon(media.mime_type)}"></i>
                                <div class="document-info">
                                    <div class="document-name">${media.filename}</div>
                                    <div class="document-size">${this.formatFileSize(media.size)}</div>
                                </div>
                            </a>
                        </div>
                    `;
                }
            }

            // Message action menu
            const actionMenu = `
                <div class="message-actions">
                    <button class="message-action-btn" onclick="chatManager.toggleMessageMenu(event, '${msg.id}')" title="More">
                        <i class="fas fa-chevron-down"></i>
                    </button>
                </div>
                <div class="message-dropdown" id="menu-${msg.id}" style="display: none;">
                    <button class="message-dropdown-item" onclick="chatManager.showMessageInfo('${msg.id}')">
                        <i class="fas fa-info-circle"></i>
                        <span>Message info</span>
                    </button>
                    <button class="message-dropdown-item" onclick="chatManager.replyToMessage('${msg.id}')">
                        <i class="fas fa-reply"></i>
                        <span>Reply</span>
                    </button>
                    ${msg.content ? `
                        <button class="message-dropdown-item" onclick="chatManager.copyMessage('${msg.id}')">
                            <i class="fas fa-copy"></i>
                            <span>Copy</span>
                        </button>
                    ` : ''}
                    <button class="message-dropdown-item" onclick="chatManager.reactToMessage('${msg.id}')">
                        <i class="fas fa-face-smile"></i>
                        <span>React</span>
                    </button>
                    ${msg.media ? `
                        <button class="message-dropdown-item" onclick="chatManager.downloadMedia('${msg.media.url}', '${msg.media.filename}')">
                            <i class="fas fa-download"></i>
                            <span>Download</span>
                        </button>
                    ` : ''}
                    <button class="message-dropdown-item" onclick="chatManager.forwardMessage('${msg.id}')">
                        <i class="fas fa-share"></i>
                        <span>Forward</span>
                    </button>
                    <button class="message-dropdown-item" onclick="chatManager.pinMessage('${msg.id}')">
                        <i class="fas fa-thumbtack"></i>
                        <span>Pin</span>
                    </button>
                    <button class="message-dropdown-item" onclick="chatManager.starMessage('${msg.id}')">
                        <i class="fas fa-star"></i>
                        <span>Star</span>
                    </button>
                    <button class="message-dropdown-item" onclick="chatManager.deleteMessage('${msg.id}')">
                        <i class="fas fa-trash"></i>
                        <span>Delete</span>
                    </button>
                </div>
            `;

            return `
                ${dateHtml}
                <div class="message ${isSent ? 'sent' : 'received'}" data-message-id="${msg.id}">
                    <div class="message-bubble ${hasMedia ? 'has-media' : ''}">
                        ${mediaContent}
                        ${msg.content ? `<div class="message-content">${this.escapeHtml(msg.content)}</div>` : ''}
                        ${!hasMedia || msg.content ? `
                            <div class="message-meta">
                                <span>${this.formatTime(msg.created_at)}</span>
                                ${isSent ? '<i class="fas fa-check-double message-status"></i>' : ''}
                            </div>
                        ` : ''}
                        ${actionMenu}
                    </div>
                    ${hasMedia && !msg.content ? `
                        <div style="padding: 0.25rem 0.5rem; font-size: 0.7rem; color: var(--text-muted); text-align: right;">
                            <span>${this.formatTime(msg.created_at)}</span>
                            ${isSent ? '<i class="fas fa-check-double" style="color: #53bdeb; margin-left: 0.25rem;"></i>' : ''}
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
        
        // Scroll to bottom
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }

    // Helper: Get document icon based on MIME type
    getDocumentIcon(mimeType) {
        if (mimeType.includes('pdf')) return 'pdf';
        if (mimeType.includes('word')) return 'word';
        if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return 'excel';
        if (mimeType.includes('powerpoint') || mimeType.includes('presentation')) return 'powerpoint';
        if (mimeType.includes('zip') || mimeType.includes('archive')) return 'archive';
        return 'alt';
    }

    // Helper: Format file size
    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
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

    // Toggle message dropdown menu
    toggleMessageMenu(event, messageId) {
        event.stopPropagation();
        
        // Close all other menus
        document.querySelectorAll('.message-dropdown').forEach(menu => {
            if (menu.id !== `menu-${messageId}`) {
                menu.style.display = 'none';
            }
        });
        
        // Toggle current menu
        const menu = document.getElementById(`menu-${messageId}`);
        if (menu) {
            menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
        }
    }

    // Show message info
    showMessageInfo(messageId) {
        // Close dropdown menu
        document.querySelectorAll('.message-dropdown').forEach(menu => {
            menu.style.display = 'none';
        });
        
        const messages = this.messages[this.currentConversationId] || [];
        const message = messages.find(m => m.id === messageId);
        
        if (!message) {
            showToast('Message not found', 'error');
            return;
        }
        
        const currentUserId = authManager.getCurrentUser()?.id;
        const isSent = message.sender_id === currentUserId;
        
        const modalHtml = `
            <div class="modal" id="messageInfoModal" style="display: flex;">
                <div class="modal-content" style="max-width: 500px;">
                    <div class="modal-header">
                        <h2>Message Info</h2>
                        <button class="close-btn" onclick="document.getElementById('messageInfoModal').remove()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom: 1.5rem;">
                            <div style="background: var(--bg-tertiary); padding: 1rem; border-radius: 8px;">
                                ${message.content ? `<p style="color: var(--text-primary); margin-bottom: 0.5rem;">${this.escapeHtml(message.content)}</p>` : ''}
                                ${message.type !== 'TEXT' ? `<p style="color: var(--text-secondary); font-size: 0.85rem;"><i class="fas fa-paperclip"></i> ${message.type}</p>` : ''}
                            </div>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 1rem;">
                            <div>
                                <div style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.25rem;">Type</div>
                                <div style="color: var(--text-primary);">${message.type}</div>
                            </div>
                            <div>
                                <div style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.25rem;">Status</div>
                                <div style="color: var(--text-primary);">${isSent ? 'Sent' : 'Received'}</div>
                            </div>
                            <div>
                                <div style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.25rem;">Sent At</div>
                                <div style="color: var(--text-primary);">${new Date(message.created_at).toLocaleString()}</div>
                            </div>
                            ${message.media ? `
                                <div>
                                    <div style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.25rem;">Media</div>
                                    <div style="color: var(--text-primary);">
                                        ${message.media.filename}<br>
                                        <span style="color: var(--text-secondary); font-size: 0.85rem;">${this.formatFileSize(message.media.size)}</span>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    // Copy message text
    copyMessage(messageId) {
        // Close dropdown menu
        document.querySelectorAll('.message-dropdown').forEach(menu => {
            menu.style.display = 'none';
        });
        
        const messages = this.messages[this.currentConversationId] || [];
        const message = messages.find(m => m.id === messageId);
        
        if (!message || !message.content) {
            showToast('No text to copy', 'error');
            return;
        }
        
        // Copy to clipboard
        navigator.clipboard.writeText(message.content).then(() => {
            showToast('Message copied', 'success');
        }).catch(err => {
            console.error('Copy failed:', err);
            showToast('Failed to copy', 'error');
        });
    }

    // React to message
    reactToMessage(messageId) {
        // Close dropdown menu
        document.querySelectorAll('.message-dropdown').forEach(menu => {
            menu.style.display = 'none';
        });
        
        const reactions = ['❤️', '😂', '😮', '😢', '🙏', '👍'];
        
        const modalHtml = `
            <div class="modal" id="reactModal" style="display: flex;" onclick="if(event.target.id === 'reactModal') document.getElementById('reactModal').remove()">
                <div class="modal-content" style="max-width: 400px;">
                    <div class="modal-header">
                        <h2>React to message</h2>
                        <button class="close-btn" onclick="document.getElementById('reactModal').remove()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <div style="display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
                            ${reactions.map(emoji => `
                                <button onclick="chatManager.addReaction('${messageId}', '${emoji}')" 
                                        style="font-size: 2rem; background: none; border: none; cursor: pointer; padding: 0.5rem; transition: transform 0.2s;"
                                        onmouseover="this.style.transform='scale(1.3)'"
                                        onmouseout="this.style.transform='scale(1)'">
                                    ${emoji}
                                </button>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    // Add reaction
    addReaction(messageId, emoji) {
        // Close modal
        document.getElementById('reactModal')?.remove();
        
        // Find message element and add reaction badge
        const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageEl) {
            let reactionBadge = messageEl.querySelector('.reaction-badge');
            if (!reactionBadge) {
                reactionBadge = document.createElement('div');
                reactionBadge.className = 'reaction-badge';
                reactionBadge.style.cssText = 'position: absolute; bottom: -8px; right: 8px; background: var(--bg-secondary); border: 2px solid var(--border-color); border-radius: 12px; padding: 2px 8px; font-size: 0.9rem;';
                messageEl.querySelector('.message-bubble').appendChild(reactionBadge);
            }
            reactionBadge.textContent = emoji;
        }
        
        showToast('Reaction added', 'success');
    }

    // Forward message
    forwardMessage(messageId) {
        // Close dropdown menu
        document.querySelectorAll('.message-dropdown').forEach(menu => {
            menu.style.display = 'none';
        });
        
        const messages = this.messages[this.currentConversationId] || [];
        const message = messages.find(m => m.id === messageId);
        
        if (!message) {
            showToast('Message not found', 'error');
            return;
        }
        
        // Create forward modal with conversation list
        const modalHtml = `
            <div class="modal" id="forwardModal" style="display: flex;" onclick="if(event.target.id === 'forwardModal') document.getElementById('forwardModal').remove()">
                <div class="modal-content" style="max-width: 500px;">
                    <div class="modal-header">
                        <h2>Forward to...</h2>
                        <button class="close-btn" onclick="document.getElementById('forwardModal').remove()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <div style="max-height: 400px; overflow-y: auto;">
                            ${this.conversations.filter(c => c.id !== this.currentConversationId).map(conv => `
                                <div onclick="chatManager.executeForward('${messageId}', '${conv.id}')" 
                                     style="padding: 1rem; display: flex; align-items: center; gap: 1rem; cursor: pointer; border-radius: 8px; transition: background 0.2s;"
                                     onmouseover="this.style.background='var(--hover-bg)'"
                                     onmouseout="this.style.background='transparent'">
                                    <div class="avatar" style="width: 40px; height: 40px; border-radius: 50%; background: var(--bg-tertiary); display: flex; align-items: center; justify-content: center;">
                                        <i class="fas ${conv.type === 'GROUP' ? 'fa-users' : 'fa-user'}"></i>
                                    </div>
                                    <div style="flex: 1;">
                                        <div style="color: var(--text-primary); font-weight: 500;">${this.escapeHtml(conv.name || 'Chat')}</div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    // Execute forward
    async executeForward(messageId, targetConversationId) {
        document.getElementById('forwardModal')?.remove();
        
        const messages = this.messages[this.currentConversationId] || [];
        const message = messages.find(m => m.id === messageId);
        
        if (!message) {
            showToast('Message not found', 'error');
            return;
        }
        
        try {
            showLoading();
            
            // Forward the message
            let result;
            if (message.media) {
                result = await this.sendMessage(targetConversationId, message.content || '', message.type, message.media.id);
            } else {
                result = await this.sendMessage(targetConversationId, message.content, 'TEXT');
            }
            
            hideLoading();
            
            if (result) {
                showToast('Message forwarded', 'success');
            } else {
                showToast('Failed to forward message', 'error');
            }
        } catch (error) {
            hideLoading();
            console.error('Forward error:', error);
            showToast('Failed to forward message', 'error');
        }
    }

    // Star message
    starMessage(messageId) {
        // Close dropdown menu
        document.querySelectorAll('.message-dropdown').forEach(menu => {
            menu.style.display = 'none';
        });
        
        // Find message element and toggle star
        const messageEl = document.querySelector(`[data-message-id="${messageId}"]`);
        if (messageEl) {
            let starBadge = messageEl.querySelector('.star-badge');
            if (!starBadge) {
                // Add star
                starBadge = document.createElement('div');
                starBadge.className = 'star-badge';
                starBadge.style.cssText = 'position: absolute; top: 4px; left: 4px; color: #ffd700; font-size: 0.9rem; z-index: 5;';
                starBadge.innerHTML = '<i class="fas fa-star"></i>';
                messageEl.querySelector('.message-bubble').appendChild(starBadge);
                
                // Store starred message
                if (!this.starredMessages) this.starredMessages = [];
                this.starredMessages.push(messageId);
                
                showToast('Message starred', 'success');
            } else {
                // Remove star
                starBadge.remove();
                
                // Remove from starred messages
                if (this.starredMessages) {
                    this.starredMessages = this.starredMessages.filter(id => id !== messageId);
                }
                
                showToast('Star removed', 'success');
            }
        }
    }

    // Download media
    async downloadMedia(url, filename) {
        try {
            // Close dropdown menu
            document.querySelectorAll('.message-dropdown').forEach(menu => {
                menu.style.display = 'none';
            });
            
            // Ensure URL is absolute
            const mediaUrl = url.startsWith('http') ? url : `http://localhost:8000${url}`;
            
            // Download using fetch and blob
            const response = await fetch(mediaUrl);
            if (!response.ok) throw new Error('Download failed');
            
            const blob = await response.blob();
            const blobUrl = window.URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.href = blobUrl;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Clean up
            window.URL.revokeObjectURL(blobUrl);
            
            showToast('Download started', 'success');
        } catch (error) {
            console.error('Download error:', error);
            showToast('Download failed', 'error');
        }
    }

    // Reply to message
    replyToMessage(messageId) {
        // Close dropdown menu
        document.querySelectorAll('.message-dropdown').forEach(menu => {
            menu.style.display = 'none';
        });
        
        // Find the message
        const messages = this.messages[this.currentConversationId] || [];
        const message = messages.find(m => m.id === messageId);
        
        if (!message) {
            showToast('Message not found', 'error');
            return;
        }
        
        // Show reply preview in input area
        const inputArea = document.querySelector('.message-input-area');
        let replyPreview = inputArea.querySelector('.reply-preview');
        
        if (!replyPreview) {
            replyPreview = document.createElement('div');
            replyPreview.className = 'reply-preview';
            inputArea.insertBefore(replyPreview, inputArea.firstChild);
        }
        
        const previewText = message.content ? 
            this.truncateText(message.content, 50) : 
            (message.type || 'Media');
        
        replyPreview.innerHTML = `
            <div style="background: var(--bg-tertiary); padding: 0.5rem 0.75rem; border-left: 3px solid var(--primary-color); margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.75rem; color: var(--primary-color); font-weight: 600;">Replying to</div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary);">${previewText}</div>
                </div>
                <button onclick="chatManager.cancelReply()" style="background: none; border: none; color: var(--text-secondary); cursor: pointer;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        // Store reply context
        this.replyingTo = messageId;
        
        // Focus input
        document.getElementById('messageInput').focus();
        
        showToast('Reply mode activated', 'info');
    }

    // Cancel reply
    cancelReply() {
        const replyPreview = document.querySelector('.reply-preview');
        if (replyPreview) {
            replyPreview.remove();
        }
        this.replyingTo = null;
    }

    // Pin message
    async pinMessage(messageId) {
        // Close dropdown menu
        document.querySelectorAll('.message-dropdown').forEach(menu => {
            menu.style.display = 'none';
        });
        
        try {
            // Find the message
            const messages = this.messages[this.currentConversationId] || [];
            const message = messages.find(m => m.id === messageId);
            
            if (!message) {
                showToast('Message not found', 'error');
                return;
            }
            
            // Show pinned message banner
            const chatHeader = document.querySelector('.chat-header');
            let pinnedBanner = document.querySelector('.pinned-message-banner');
            
            if (!pinnedBanner) {
                pinnedBanner = document.createElement('div');
                pinnedBanner.className = 'pinned-message-banner';
                chatHeader.parentNode.insertBefore(pinnedBanner, chatHeader.nextSibling);
            }
            
            const previewText = message.content ? 
                this.truncateText(message.content, 50) : 
                (message.type || 'Media');
            
            pinnedBanner.innerHTML = `
                <div style="background: var(--bg-tertiary); padding: 0.75rem 1rem; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color);">
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <i class="fas fa-thumbtack" style="color: var(--primary-color);"></i>
                        <div>
                            <div style="font-size: 0.75rem; color: var(--text-secondary);">Pinned Message</div>
                            <div style="font-size: 0.9rem; color: var(--text-primary);">${previewText}</div>
                        </div>
                    </div>
                    <button onclick="chatManager.unpinMessage()" style="background: none; border: none; color: var(--text-secondary); cursor: pointer;">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            
            // Store pinned message ID
            this.pinnedMessageId = messageId;
            
            showToast('Message pinned', 'success');
        } catch (error) {
            console.error('Pin error:', error);
            showToast('Failed to pin message', 'error');
        }
    }

    // Unpin message
    unpinMessage() {
        const pinnedBanner = document.querySelector('.pinned-message-banner');
        if (pinnedBanner) {
            pinnedBanner.remove();
        }
        this.pinnedMessageId = null;
        showToast('Message unpinned', 'success');
    }

    // Delete message
    deleteMessage(messageId) {
        // Close dropdown menu
        document.querySelectorAll('.message-dropdown').forEach(menu => {
            menu.style.display = 'none';
        });
        
        // Check if user is the sender
        const messages = this.messages[this.currentConversationId] || [];
        const message = messages.find(m => m.id === messageId);
        
        if (!message) {
            console.error('Message not found in local cache:', messageId);
            showToast('Message not found', 'error');
            return;
        }
        
        const currentUserId = authManager.getCurrentUser()?.id;
        const isSender = message && message.sender_id === currentUserId;
        
        console.log('Delete check:', {
            messageId,
            currentUserId,
            messageSenderId: message.sender_id,
            isSender
        });
        
        // Show WhatsApp-style delete modal
        const modalHtml = `
            <div class="modal delete-modal" id="deleteModal" style="display: flex; background: rgba(0, 0, 0, 0.8);">
                <div class="modal-content" style="max-width: 400px; background: var(--bg-secondary); border-radius: 8px; overflow: visible;">
                    <div style="padding: 1.5rem 1.5rem 1rem;">
                        <h3 style="color: var(--text-primary); font-size: 1.1rem; margin-bottom: 0.5rem;">Delete message?</h3>
                    </div>
                    <div style="display: flex; flex-direction: column;">
                        ${isSender ? `
                            <button onclick="chatManager.executeDelete('${messageId}', 'everyone')" 
                                    class="delete-option-btn"
                                    style="padding: 1rem 1.5rem; text-align: left; background: none; border: none; color: var(--text-primary); cursor: pointer; transition: background 0.2s; font-size: 0.95rem;"
                                    onmouseover="this.style.background='var(--hover-bg)'"
                                    onmouseout="this.style.background='none'">
                                Delete for everyone
                            </button>
                        ` : ''}
                        <button onclick="chatManager.executeDelete('${messageId}', 'me')" 
                                class="delete-option-btn"
                                style="padding: 1rem 1.5rem; text-align: left; background: none; border: none; color: var(--text-primary); cursor: pointer; transition: background 0.2s; font-size: 0.95rem;"
                                onmouseover="this.style.background='var(--hover-bg)'"
                                onmouseout="this.style.background='none'">
                            Delete for me
                        </button>
                        <button onclick="document.getElementById('deleteModal').remove()" 
                                class="delete-option-btn"
                                style="padding: 1rem 1.5rem; text-align: left; background: none; border: none; color: var(--primary-color); cursor: pointer; transition: background 0.2s; font-size: 0.95rem; border-top: 1px solid var(--border-color); margin-top: 0.5rem;"
                                onmouseover="this.style.background='var(--hover-bg)'"
                                onmouseout="this.style.background='none'">
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Close on outside click
        setTimeout(() => {
            document.getElementById('deleteModal')?.addEventListener('click', (e) => {
                if (e.target.id === 'deleteModal') {
                    document.getElementById('deleteModal').remove();
                }
            });
        }, 100);
    }

    // Execute delete
    async executeDelete(messageId, deleteType) {
        // Close modal
        document.getElementById('deleteModal')?.remove();
        
        console.log('Deleting message:', messageId, 'Type:', deleteType);
        
        try {
            showLoading();
            
            if (deleteType === 'everyone') {
                // Check if this is a recently sent message
                const isRecentlySent = this.sentMessageIds && this.sentMessageIds.has(messageId);
                
                if (isRecentlySent) {
                    console.log('Recently sent message detected, waiting for DB sync...');
                    // Wait a bit for database to sync
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
                
                // Delete for everyone (backend deletion)
                const url = `/messages/${messageId}`;
                console.log('DELETE request to:', url);
                
                const response = await authManager.authenticatedRequest(url, {
                    method: 'DELETE'
                });
                
                console.log('DELETE response status:', response.status);
                
                hideLoading();
                
                if (response.ok || response.status === 204) {
                    // Remove from sentMessageIds
                    if (this.sentMessageIds) {
                        this.sentMessageIds.delete(messageId);
                    }
                    
                    // Remove from local cache
                    if (this.messages[this.currentConversationId]) {
                        this.messages[this.currentConversationId] = this.messages[this.currentConversationId].filter(
                            m => m.id !== messageId
                        );
                    }
                    
                    // Re-render messages
                    this.renderMessages(this.currentConversationId);
                    
                    showToast('Message deleted for everyone', 'success');
                } else if (response.status === 404 && isRecentlySent) {
                    // Message might not be in DB yet - try once more after a delay
                    console.log('Message not found (recently sent), retrying after 1.5 seconds...');
                    showLoading();
                    
                    await new Promise(resolve => setTimeout(resolve, 1500));
                    
                    const retryResponse = await authManager.authenticatedRequest(url, {
                        method: 'DELETE'
                    });
                    
                    console.log('Retry DELETE response status:', retryResponse.status);
                    hideLoading();
                    
                    if (retryResponse.ok || retryResponse.status === 204) {
                        // Remove from sentMessageIds
                        if (this.sentMessageIds) {
                            this.sentMessageIds.delete(messageId);
                        }
                        
                        // Remove from local cache
                        if (this.messages[this.currentConversationId]) {
                            this.messages[this.currentConversationId] = this.messages[this.currentConversationId].filter(
                                m => m.id !== messageId
                            );
                        }
                        
                        // Re-render messages
                        this.renderMessages(this.currentConversationId);
                        
                        showToast('Message deleted for everyone', 'success');
                    } else {
                        const errorText = await retryResponse.text();
                        console.error('DELETE retry error:', errorText);
                        showToast('Message not found in database. Please try again in a moment.', 'warning');
                    }
                } else {
                    const errorText = await response.text();
                    console.error('DELETE error response:', errorText);
                    let error;
                    try {
                        error = JSON.parse(errorText);
                    } catch {
                        error = { detail: 'Failed to delete message' };
                    }
                    showToast(error.detail || 'Failed to delete message', 'error');
                }
            } else {
                // Delete for me only (local deletion)
                hideLoading();
                
                // Remove from local cache only
                if (this.messages[this.currentConversationId]) {
                    this.messages[this.currentConversationId] = this.messages[this.currentConversationId].filter(
                        m => m.id !== messageId
                    );
                }
                
                // Re-render messages
                this.renderMessages(this.currentConversationId);
                
                showToast('Message deleted for you', 'success');
            }
        } catch (error) {
            hideLoading();
            console.error('Delete error:', error);
            showToast('Failed to delete message', 'error');
        }
    }

    // Cleanup
    destroy() {
        this.stopMessagePolling();
    }
}

// Export chat manager
window.chatManager = new ChatManager();
