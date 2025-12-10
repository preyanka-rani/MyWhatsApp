// Main Application
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

// Initialize application
function initializeApp() {
    // Check authentication status
    if (authManager.isAuthenticated()) {
        showChatInterface();
    } else {
        showLoginScreen();
    }

    // Setup event listeners
    setupEventListeners();
}

// Show login screen
function showLoginScreen() {
    document.getElementById('loginScreen').style.display = 'flex';
    document.getElementById('otpScreen').style.display = 'none';
    document.getElementById('chatInterface').style.display = 'none';
}

// Show OTP screen
function showOTPScreen() {
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('otpScreen').style.display = 'flex';
    document.getElementById('chatInterface').style.display = 'none';
    
    const phone = localStorage.getItem(CONFIG.STORAGE_KEYS.PHONE);
    document.getElementById('phoneDisplay').textContent = phone;
}

// Show chat interface
async function showChatInterface() {
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('otpScreen').style.display = 'none';
    document.getElementById('chatInterface').style.display = 'flex';

    // Load user profile
    const user = await authManager.getProfile();
    if (user) {
        document.getElementById('userName').textContent = user.phone_number || 'User';
        console.log('User preferred language:', user.preferred_language);
    }
    
    // Load user's language preference
    await translationManager.getUserLanguage();

    // Load conversations
    await chatManager.loadConversations();

    // Connect WebSocket
    wsManager.connect();
}

// Back to login
function backToLogin() {
    showLoginScreen();
    localStorage.removeItem(CONFIG.STORAGE_KEYS.PHONE);
}

// Logout
function logout() {
    if (confirm('Are you sure you want to logout?')) {
        authManager.logout();
    }
}

// Show new chat modal
function showNewChatModal() {
    document.getElementById('newChatModal').style.display = 'flex';
    loadNewChatContacts();
    document.getElementById('newChatSearch').focus();
}

// Close new chat modal
function closeNewChatModal() {
    document.getElementById('newChatModal').style.display = 'none';
}

// Show add contact modal
function showAddContactModal() {
    closeNewChatModal();
    document.getElementById('addContactModal').style.display = 'flex';
    document.getElementById('contactPhone').focus();
}

// Close add contact modal
function closeAddContactModal() {
    document.getElementById('addContactModal').style.display = 'none';
    document.getElementById('addContactForm').reset();
}

// Load contacts for new chat modal
async function loadNewChatContacts() {
    const contactsList = document.getElementById('newChatContactsList');
    contactsList.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-secondary);">Loading contacts...</div>';

    try {
        // Get all conversations to show as contacts
        const conversations = chatManager.conversations;
        
        if (conversations.length === 0) {
            contactsList.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-secondary);">No contacts yet. Add a new contact to start chatting!</div>';
            return;
        }

        contactsList.innerHTML = conversations.map(conv => {
            const displayName = conv.name || 'Unknown';
            const iconClass = conv.type === 'GROUP' ? 'fa-users' : 'fa-user';
            
            return `
                <div class="contact-item" onclick="selectContactFromNewChat('${conv.id}')">
                    <div class="avatar">
                        <i class="fas ${iconClass}"></i>
                    </div>
                    <div class="contact-info">
                        <div class="contact-name">${escapeHtml(displayName)}</div>
                        <div class="contact-status">Tap to open chat</div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading contacts:', error);
        contactsList.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-secondary);">Failed to load contacts</div>';
    }
}

// Select contact from new chat modal
function selectContactFromNewChat(conversationId) {
    closeNewChatModal();
    chatManager.selectConversation(conversationId);
}

// Helper function for HTML escaping
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Send message
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const content = input.value.trim();
    
    if (!content) return;
    if (!chatManager.currentConversationId) {
        showToast('Please select a conversation', 'warning');
        return;
    }

    // Clear input immediately
    input.value = '';

    // Send message
    await chatManager.sendMessage(chatManager.currentConversationId, content);
}

// Setup event listeners
function setupEventListeners() {
    // Login form
    document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const phone = document.getElementById('phoneNumber').value.trim();
        
        if (!phone) {
            showToast('Please enter phone number', 'warning');
            return;
        }

        const success = await authManager.requestOTP(phone);
        if (success) {
            showOTPScreen();
        }
    });

    // OTP form
    document.getElementById('otpForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const otp = document.getElementById('otpCode').value.trim();
        
        if (!otp || otp.length !== 6) {
            showToast('Please enter valid 6-digit OTP', 'warning');
            return;
        }

        const success = await authManager.verifyOTP(otp);
        if (success) {
            showChatInterface();
        }
    });

    // Add contact form
    document.getElementById('addContactForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const phone = document.getElementById('contactPhone').value.trim();
        const name = document.getElementById('contactName').value.trim();
        
        if (!phone) {
            showToast('Please enter phone number', 'warning');
            return;
        }

        const conversation = await chatManager.createConversation(phone, name || null);
        if (conversation) {
            closeAddContactModal();
            chatManager.selectConversation(conversation.id);
        }
    });

    // New chat search
    document.getElementById('newChatSearch')?.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const contacts = document.querySelectorAll('#newChatContactsList .contact-item');
        
        contacts.forEach(contact => {
            const name = contact.querySelector('.contact-name').textContent.toLowerCase();
            if (name.includes(query)) {
                contact.style.display = 'flex';
            } else {
                contact.style.display = 'none';
            }
        });
    });

    // Message input - Enter to send
    document.getElementById('messageInput')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Message input - Typing indicator
    let typingTimeout;
    document.getElementById('messageInput')?.addEventListener('input', (e) => {
        if (!chatManager.currentConversationId) return;
        
        // Send typing indicator
        wsManager.sendTypingIndicator(chatManager.currentConversationId, true);
        
        // Clear previous timeout
        clearTimeout(typingTimeout);
        
        // Stop typing after 2 seconds of inactivity
        typingTimeout = setTimeout(() => {
            wsManager.sendTypingIndicator(chatManager.currentConversationId, false);
        }, 2000);
    });

    // Search input
    document.getElementById('searchInput')?.addEventListener('input', (e) => {
        chatManager.searchConversations(e.target.value);
    });

    // Close modal on background click
    document.getElementById('newChatModal')?.addEventListener('click', (e) => {
        if (e.target.id === 'newChatModal') {
            closeNewChatModal();
        }
    });
    
    document.getElementById('addContactModal')?.addEventListener('click', (e) => {
        if (e.target.id === 'addContactModal') {
            closeAddContactModal();
        }
    });

    // Mobile back button (if needed)
    if (window.innerWidth <= 768) {
        // Add back button to chat header for mobile
        const chatHeader = document.querySelector('.chat-header');
        if (chatHeader) {
            const backBtn = document.createElement('button');
            backBtn.className = 'icon-btn mobile-back-btn';
            backBtn.innerHTML = '<i class="fas fa-arrow-left"></i>';
            backBtn.onclick = () => {
                document.querySelector('.chat-area').classList.remove('active');
            };
            chatHeader.insertBefore(backBtn, chatHeader.firstChild);
        }
    }
}

// UI Helper Functions

// Handle chat header click (for group info)
function handleChatHeaderClick() {
    const currentConversation = chatManager.getCurrentConversation();
    if (currentConversation && currentConversation.type === 'GROUP') {
        groupManager.showGroupInfo(currentConversation.id);
    }
}

// Show loading overlay
function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

// Hide loading overlay
function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

// Show toast notification
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    }[type] || 'fa-info-circle';
    
    toast.innerHTML = `
        <i class="fas ${icon}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after 4 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Handle window beforeunload
window.addEventListener('beforeunload', () => {
    if (chatManager) {
        chatManager.destroy();
    }
    if (wsManager) {
        wsManager.disconnect();
    }
});

// Handle online/offline events
window.addEventListener('online', () => {
    showToast('Connection restored', 'success');
    if (authManager.isAuthenticated() && !wsManager.isConnected()) {
        wsManager.connect();
    }
});

window.addEventListener('offline', () => {
    showToast('No internet connection', 'warning');
});
