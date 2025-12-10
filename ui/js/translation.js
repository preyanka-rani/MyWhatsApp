// Translation Manager
class TranslationManager {
    constructor() {
        this.currentLanguage = 'en';
        this.languages = [];
        this.loadLanguages();
    }

    // Load supported languages
    async loadLanguages() {
        try {
            const response = await authManager.authenticatedRequest('/auth/languages');
            if (response.ok) {
                const data = await response.json();
                this.languages = data.languages;
                console.log('Loaded languages:', this.languages);
            }
        } catch (error) {
            console.error('Error loading languages:', error);
        }
    }

    // Get user's preferred language
    async getUserLanguage() {
        try {
            const response = await authManager.authenticatedRequest('/auth/users/me');
            if (response.ok) {
                const user = await response.json();
                this.currentLanguage = user.preferred_language || 'en';
                return this.currentLanguage;
            }
        } catch (error) {
            console.error('Error getting user language:', error);
        }
        return 'en';
    }

    // Set user's preferred language
    async setLanguage(languageCode) {
        try {
            showLoading();
            const response = await authManager.authenticatedRequest('/auth/users/me/language', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ language: languageCode })
            });

            if (response.ok) {
                const data = await response.json();
                this.currentLanguage = languageCode;
                
                // Clear message cache and reload current conversation to show translated messages
                if (chatManager.currentConversationId) {
                    console.log(`Language changed to ${languageCode}, reloading messages...`);
                    // Clear the cached messages to force fresh translation
                    delete chatManager.messages[chatManager.currentConversationId];
                    await chatManager.loadMessages(chatManager.currentConversationId);
                    chatManager.renderMessages(chatManager.currentConversationId);
                }
                
                // Also reload user profile
                await authManager.loadUserProfile();
                
                hideLoading();
                showToast('Language updated successfully! Messages refreshed.', 'success');
                
                return true;
            } else {
                hideLoading();
                const error = await response.json();
                showToast(error.detail || 'Failed to update language', 'error');
                return false;
            }
        } catch (error) {
            hideLoading();
            console.error('Error setting language:', error);
            showToast('Error updating language', 'error');
            return false;
        }
    }

    // Show language selector modal
    showLanguageSelector() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header">
                    <h2>Choose Language</h2>
                    <button class="btn-icon" onclick="this.closest('.modal').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                        All incoming messages will be automatically translated to your preferred language.
                    </p>
                    <div class="language-list" id="languageList" style="max-height: 400px; overflow-y: auto;">
                        ${this.languages.map(lang => `
                            <div class="language-item ${lang.code === this.currentLanguage ? 'active' : ''}" 
                                 onclick="translationManager.selectLanguage('${lang.code}')"
                                 data-lang-code="${lang.code}">
                                <div class="language-info">
                                    <span class="language-name">${escapeHtml(lang.name)}</span>
                                    <span class="language-code">${lang.code}</span>
                                </div>
                                ${lang.code === this.currentLanguage ? '<i class="fas fa-check"></i>' : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        setTimeout(() => modal.classList.add('show'), 10);
    }

    // Select language from modal
    async selectLanguage(languageCode) {
        const success = await this.setLanguage(languageCode);
        
        if (success) {
            // Update UI
            document.querySelectorAll('.language-item').forEach(item => {
                item.classList.remove('active');
                const checkIcon = item.querySelector('.fa-check');
                if (checkIcon) checkIcon.remove();
            });

            const selectedItem = document.querySelector(`[data-lang-code="${languageCode}"]`);
            if (selectedItem) {
                selectedItem.classList.add('active');
                selectedItem.querySelector('.language-info').insertAdjacentHTML('afterend', '<i class="fas fa-check"></i>');
            }

            // Close modal after 500ms
            setTimeout(() => {
                document.querySelector('.modal').remove();
            }, 500);
        }
    }
    
    // Show conversation language selector
    showConversationLanguageSelector(conversationId) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header">
                    <h2>Set Translation for This Chat</h2>
                    <button class="btn-icon" onclick="this.closest('.modal').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                        Choose what language the other person will see your messages in.
                    </p>
                    <div class="language-list" id="conversationLanguageList" style="max-height: 400px; overflow-y: auto;">
                        <div class="language-item" 
                             onclick="translationManager.selectConversationLanguage('${conversationId}', null)"
                             data-lang-code="none">
                            <div class="language-info">
                                <span class="language-name">No Translation</span>
                                <span class="language-code">Send original language</span>
                            </div>
                        </div>
                        ${this.languages.map(lang => `
                            <div class="language-item" 
                                 onclick="translationManager.selectConversationLanguage('${conversationId}', '${lang.code}')"
                                 data-lang-code="${lang.code}">
                                <div class="language-info">
                                    <span class="language-name">${escapeHtml(lang.name)}</span>
                                    <span class="language-code">${lang.code}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        setTimeout(() => modal.classList.add('show'), 10);
    }
    
    // Set conversation language
    async selectConversationLanguage(conversationId, languageCode) {
        try {
            const response = await authManager.authenticatedRequest(`/conversations/${conversationId}/language`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ language: languageCode || '' })
            });

            if (response.ok) {
                const data = await response.json();
                const langName = languageCode ? 
                    this.languages.find(l => l.code === languageCode)?.name : 
                    'No Translation';
                showToast(`Messages will be sent in: ${langName}`, 'success');
                
                // Close modal
                setTimeout(() => {
                    document.querySelector('.modal')?.remove();
                }, 500);
                
                return true;
            } else {
                const error = await response.json();
                showToast(error.detail || 'Failed to set conversation language', 'error');
                return false;
            }
        } catch (error) {
            console.error('Error setting conversation language:', error);
            showToast('Error setting conversation language', 'error');
            return false;
        }
    }
}

// Global translation manager instance
const translationManager = new TranslationManager();

// Global functions for HTML onclick handlers
function showConversationLanguageSelector() {
    if (chatManager.currentConversationId) {
        translationManager.showConversationLanguageSelector(chatManager.currentConversationId);
        // Hide the dropdown menu
        document.getElementById('chatOptionsMenu').style.display = 'none';
    } else {
        showToast('No conversation selected', 'error');
    }
}

function showChatOptionsMenu(event) {
    event.stopPropagation();
    const menu = document.getElementById('chatOptionsMenu');
    
    if (menu.style.display === 'none') {
        menu.style.display = 'block';
        
        // Close menu when clicking outside
        setTimeout(() => {
            document.addEventListener('click', function closeMenu(e) {
                if (!menu.contains(e.target)) {
                    menu.style.display = 'none';
                    document.removeEventListener('click', closeMenu);
                }
            });
        }, 0);
    } else {
        menu.style.display = 'none';
    }
}

function viewContactInfo() {
    showToast('Contact info coming soon!', 'info');
    document.getElementById('chatOptionsMenu').style.display = 'none';
}