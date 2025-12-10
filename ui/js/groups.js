// Group Manager
class GroupManager {
    constructor() {
        this.groups = [];
        this.currentGroupId = null;
    }

    // Create new group
    async createGroup(name, description, memberIds) {
        try {
            showLoading();
            
            const response = await authManager.authenticatedRequest('/groups', {
                method: 'POST',
                body: JSON.stringify({
                    name: name,
                    description: description || '',
                    member_ids: memberIds
                })
            });

            hideLoading();

            if (response.ok) {
                const group = await response.json();
                showToast('Group created successfully!', 'success');
                
                // Reload conversations to show new group
                await chatManager.loadConversations();
                
                return group;
            } else {
                const error = await response.json();
                showToast(error.detail || 'Failed to create group', 'error');
                return null;
            }
        } catch (error) {
            hideLoading();
            console.error('Error creating group:', error);
            showToast('Error creating group', 'error');
            return null;
        }
    }

    // Get group details
    async getGroup(groupId) {
        try {
            const response = await authManager.authenticatedRequest(`/groups/${groupId}`);
            
            if (response.ok) {
                return await response.json();
            } else {
                showToast('Failed to load group', 'error');
                return null;
            }
        } catch (error) {
            console.error('Error loading group:', error);
            return null;
        }
    }

    // Add member to group
    async addMember(groupId, userId) {
        try {
            const response = await authManager.authenticatedRequest(
                `/groups/${groupId}/members`,
                {
                    method: 'POST',
                    body: JSON.stringify({ user_id: userId })
                }
            );

            if (response.ok) {
                showToast('Member added successfully!', 'success');
                return true;
            } else {
                const error = await response.json();
                showToast(error.detail || 'Failed to add member', 'error');
                return false;
            }
        } catch (error) {
            console.error('Error adding member:', error);
            showToast('Error adding member', 'error');
            return false;
        }
    }

    // Remove member from group
    async removeMember(groupId, memberId) {
        try {
            const response = await authManager.authenticatedRequest(
                `/groups/${groupId}/members/${memberId}`,
                { method: 'DELETE' }
            );

            if (response.ok || response.status === 204) {
                showToast('Member removed successfully!', 'success');
                return true;
            } else {
                const error = await response.json();
                showToast(error.detail || 'Failed to remove member', 'error');
                return false;
            }
        } catch (error) {
            console.error('Error removing member:', error);
            showToast('Error removing member', 'error');
            return false;
        }
    }

    // Get group members
    async getMembers(groupId) {
        try {
            const response = await authManager.authenticatedRequest(
                `/groups/${groupId}/members`
            );
            
            if (response.ok) {
                return await response.json();
            } else {
                return [];
            }
        } catch (error) {
            console.error('Error loading members:', error);
            return [];
        }
    }

    // Update group
    async updateGroup(groupId, data) {
        try {
            const response = await authManager.authenticatedRequest(
                `/groups/${groupId}`,
                {
                    method: 'PATCH',
                    body: JSON.stringify(data)
                }
            );

            if (response.ok) {
                showToast('Group updated successfully!', 'success');
                await chatManager.loadConversations();
                return true;
            } else {
                const error = await response.json();
                showToast(error.detail || 'Failed to update group', 'error');
                return false;
            }
        } catch (error) {
            console.error('Error updating group:', error);
            showToast('Error updating group', 'error');
            return false;
        }
    }

    // Show group info modal
    async showGroupInfo(conversationId) {
        const conversation = chatManager.conversations.find(c => c.id === conversationId);
        if (!conversation || conversation.type !== 'GROUP') return;

        // Get group details
        const group = await this.getGroup(conversationId);
        if (!group) return;

        // Get group members
        const members = await this.getMembers(conversationId);

        // Create modal
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header">
                    <h2>${escapeHtml(group.name)}</h2>
                    <button class="btn-icon" onclick="this.closest('.modal').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <div class="group-info">
                        <div class="group-avatar">
                            <i class="fas fa-users"></i>
                        </div>
                        <p class="group-description">${escapeHtml(group.description || 'No description')}</p>
                        
                        <div class="group-stats">
                            <span><i class="fas fa-user"></i> ${members.length} members</span>
                            <span><i class="fas fa-calendar"></i> Created ${new Date(group.created_at).toLocaleDateString()}</span>
                        </div>

                        <div class="group-actions" style="margin-top: 1rem;">
                            <button class="btn btn-primary" onclick="groupManager.showAddMemberModal('${conversationId}')">
                                <i class="fas fa-user-plus"></i> Add Member
                            </button>
                            <button class="btn btn-secondary" onclick="groupManager.showEditGroupModal('${conversationId}')">
                                <i class="fas fa-edit"></i> Edit Group
                            </button>
                        </div>

                        <div class="group-members" style="margin-top: 2rem;">
                            <h3>Members</h3>
                            <div class="members-list">
                                ${members.map(member => `
                                    <div class="member-item">
                                        <div class="avatar">
                                            <i class="fas fa-user"></i>
                                        </div>
                                        <div class="member-info">
                                            <span class="member-name">${escapeHtml(member.name || member.phone_number)}</span>
                                            <span class="member-phone">${escapeHtml(member.phone_number)}</span>
                                        </div>
                                        ${member.id !== authManager.getCurrentUser()?.id ? `
                                            <button class="btn-icon" onclick="groupManager.removeMemberConfirm('${conversationId}', '${member.id}', '${escapeHtml(member.phone_number)}')">
                                                <i class="fas fa-trash"></i>
                                            </button>
                                        ` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        setTimeout(() => modal.classList.add('show'), 10);
    }

    // Show add member modal
    showAddMemberModal(groupId) {
        // Close any existing modals
        document.querySelectorAll('.modal').forEach(m => m.remove());

        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Add Member</h2>
                    <button class="btn-icon" onclick="this.closest('.modal').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <form onsubmit="groupManager.handleAddMember(event, '${groupId}')">
                        <div class="form-group">
                            <label>Phone Number</label>
                            <input type="tel" id="addMemberPhone" class="form-control" 
                                   placeholder="+8801XXXXXXXXX" required>
                        </div>
                        <div class="form-actions">
                            <button type="button" class="btn btn-secondary" 
                                    onclick="this.closest('.modal').remove()">Cancel</button>
                            <button type="submit" class="btn btn-primary">Add Member</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        setTimeout(() => modal.classList.add('show'), 10);
    }

    // Handle add member form
    async handleAddMember(event, groupId) {
        event.preventDefault();
        
        const phone = document.getElementById('addMemberPhone').value.trim();
        
        // Get or create user
        const response = await authManager.authenticatedRequest(
            `/auth/users/create-or-get?phone_number=${encodeURIComponent(phone)}`,
            { method: 'POST' }
        );

        if (!response.ok) {
            showToast('Failed to find user', 'error');
            return;
        }

        const user = await response.json();
        
        // Add to group
        const success = await this.addMember(groupId, user.id);
        
        if (success) {
            document.querySelector('.modal').remove();
            // Refresh group info
            this.showGroupInfo(groupId);
        }
    }

    // Confirm remove member
    removeMemberConfirm(groupId, memberId, memberName) {
        if (confirm(`Remove ${memberName} from group?`)) {
            this.removeMember(groupId, memberId).then(success => {
                if (success) {
                    this.showGroupInfo(groupId);
                }
            });
        }
    }

    // Show new group modal - Step 1: Select Members
    async showNewGroupModal() {
        // Close existing modals
        document.querySelectorAll('.modal').forEach(m => m.remove());

        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header">
                    <button class="icon-btn" onclick="this.closest('.modal').remove()" style="margin-right: 1rem;">
                        <i class="fas fa-arrow-left"></i>
                    </button>
                    <h2>Add group members</h2>
                </div>
                <div class="modal-body" style="padding: 0;">
                    <!-- Search Bar -->
                    <div class="search-bar" style="padding: 0.75rem 1rem;">
                        <div class="search-input-wrapper">
                            <i class="fas fa-search"></i>
                            <input type="text" id="groupMemberSearch" placeholder="Search name or number">
                        </div>
                    </div>

                    <!-- Selected Members -->
                    <div id="selectedMembers" style="padding: 0.75rem 1rem; display: none; background: var(--bg-secondary);">
                        <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;" id="selectedMemberChips"></div>
                    </div>

                    <!-- Contact List -->
                    <div class="contacts-list" id="groupContactsList" style="max-height: 400px;">
                        <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                            <i class="fas fa-spinner fa-spin"></i> Loading contacts...
                        </div>
                    </div>

                    <!-- Next Button -->
                    <div style="padding: 1rem; border-top: 1px solid var(--border-color);">
                        <button class="btn btn-primary" style="width: 100%;" onclick="groupManager.showGroupDetailsForm()" id="groupNextBtn" disabled>
                            <i class="fas fa-arrow-right"></i> Next
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        setTimeout(() => modal.classList.add('show'), 10);
        
        // Load contacts
        await this.loadGroupContacts();
    }
    
    // Toggle member selection
    selectedMembers = new Set();
    selectedMemberNames = new Map();
    
    toggleMemberSelection(memberId, memberName) {
        const checkbox = document.getElementById(`member_${memberId}`);
        
        if (this.selectedMembers.has(memberId)) {
            this.selectedMembers.delete(memberId);
            this.selectedMemberNames.delete(memberId);
            checkbox.checked = false;
        } else {
            this.selectedMembers.add(memberId);
            this.selectedMemberNames.set(memberId, memberName);
            checkbox.checked = true;
        }
        
        this.updateSelectedMembersUI();
    }
    
    updateSelectedMembersUI() {
        const selectedDiv = document.getElementById('selectedMembers');
        const chipsDiv = document.getElementById('selectedMemberChips');
        const nextBtn = document.getElementById('groupNextBtn');
        
        if (this.selectedMembers.size > 0) {
            selectedDiv.style.display = 'block';
            nextBtn.disabled = false;
            
            chipsDiv.innerHTML = Array.from(this.selectedMembers).map(id => {
                const name = this.selectedMemberNames.get(id);
                return `
                    <div class="member-chip">
                        <span>${escapeHtml(name)}</span>
                        <i class="fas fa-times" onclick="groupManager.toggleMemberSelection('${id}', '${escapeHtml(name)}')"></i>
                    </div>
                `;
            }).join('');
        } else {
            selectedDiv.style.display = 'none';
            nextBtn.disabled = true;
        }
    }
    
    // Show group details form (Step 2)
    showGroupDetailsForm() {
        if (this.selectedMembers.size === 0) {
            showToast('Please select at least one member', 'warning');
            return;
        }
        
        // Close current modal
        document.querySelector('.modal').remove();
        
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <button class="icon-btn" onclick="groupManager.showNewGroupModal()" style="margin-right: 1rem;">
                        <i class="fas fa-arrow-left"></i>
                    </button>
                    <h2>New Group</h2>
                </div>
                <div class="modal-body">
                    <form onsubmit="groupManager.handleCreateGroupFinal(event)">
                        <div class="form-group">
                            <label>Group Name</label>
                            <input type="text" id="newGroupName" class="form-control" 
                                   placeholder="Enter group name" required>
                        </div>
                        <div class="form-group">
                            <label>Description (Optional)</label>
                            <textarea id="newGroupDescription" class="form-control" 
                                      rows="3" placeholder="Group description"></textarea>
                        </div>
                        <div class="form-group">
                            <label>Selected Members (${this.selectedMembers.size})</label>
                            <div style="padding: 0.75rem; background: var(--bg-tertiary); border-radius: 6px;">
                                ${Array.from(this.selectedMemberNames.values()).join(', ')}
                            </div>
                        </div>
                        <div class="form-actions">
                            <button type="button" class="btn btn-secondary" 
                                    onclick="this.closest('.modal').remove()">Cancel</button>
                            <button type="submit" class="btn btn-primary">Create Group</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        setTimeout(() => modal.classList.add('show'), 10);
    }
    
    // Handle final group creation
    async handleCreateGroupFinal(event) {
        event.preventDefault();
        
        const name = document.getElementById('newGroupName').value.trim();
        const description = document.getElementById('newGroupDescription').value.trim();
        
        console.log('Creating group with selected conversations:', Array.from(this.selectedMembers));
        
        // Get phone numbers for selected conversations
        const phoneNumbers = [];
        const currentUserId = authManager.getCurrentUser()?.id;
        
        for (const convId of this.selectedMembers) {
            const conv = chatManager.conversations.find(c => c.id === convId);
            console.log('Processing conversation:', conv);
            
            if (conv) {
                // For each conversation, we need to get the participant's phone
                // We'll create/get users by their conversation ID
                // First, let's get the conversation details with members
                try {
                    const response = await authManager.authenticatedRequest(`/conversations/${convId}/members`);
                    if (response.ok) {
                        const members = await response.json();
                        console.log('Members for conversation', convId, ':', members);
                        
                        // Get the other user's phone (not current user)
                        for (const member of members) {
                            if (member.user_id !== currentUserId && member.phone_number) {
                                phoneNumbers.push(member.phone_number);
                                break;
                            }
                        }
                    }
                } catch (error) {
                    console.error('Error fetching members for conversation:', convId, error);
                }
            }
        }
        
        console.log('Phone numbers for group:', phoneNumbers);
        
        if (phoneNumbers.length === 0) {
            showToast('Failed to get member phone numbers. Please try again.', 'error');
            return;
        }
        
        // Create or get users and collect their IDs
        const memberIds = [];
        for (const phone of phoneNumbers) {
            try {
                const response = await authManager.authenticatedRequest(
                    `/auth/users/create-or-get?phone_number=${encodeURIComponent(phone)}`,
                    { method: 'POST' }
                );
                
                if (response.ok) {
                    const user = await response.json();
                    memberIds.push(user.id);
                }
            } catch (error) {
                console.error('Error creating/getting user:', phone, error);
            }
        }
        
        console.log('Final member IDs:', memberIds);
        
        if (memberIds.length === 0) {
            showToast('Failed to prepare group members. Please try again.', 'error');
            return;
        }
        
        // Create group
        const group = await this.createGroup(name, description, memberIds);
        
        if (group) {
            document.querySelector('.modal').remove();
            // Reset selection
            this.selectedMembers.clear();
            this.selectedMemberNames.clear();
        }
    }

    // Load contacts for group creation
    async loadGroupContacts() {
        const contactsList = document.getElementById('groupContactsList');
        
        // Make sure conversations are loaded
        if (!chatManager.conversations || chatManager.conversations.length === 0) {
            console.log('Loading conversations for group creation...');
            await chatManager.loadConversations();
        }
        
        console.log('All conversations:', chatManager.conversations); // Debug
        
        // Filter out group conversations, show all private chats
        const conversations = chatManager.conversations.filter(c => c.type !== 'GROUP');
        
        console.log('Filtered conversations for group:', conversations); // Debug
        
        if (conversations.length === 0) {
            contactsList.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--text-secondary);">No contacts available<br><small>Add contacts first to create a group</small></div>';
            return;
        }
        
        contactsList.innerHTML = conversations.map(conv => {
            const displayName = conv.name || conv.phone_number || 'Unknown';
            
            return `
                <div class="contact-item" onclick="groupManager.toggleMemberSelection('${conv.id}', '${escapeHtml(displayName)}')" data-contact-id="${conv.id}">
                    <input type="checkbox" class="member-checkbox" id="member_${conv.id}" 
                           onclick="event.stopPropagation(); groupManager.toggleMemberSelection('${conv.id}', '${escapeHtml(displayName)}')">
                    <div class="avatar">
                        <i class="fas fa-user"></i>
                    </div>
                    <div class="contact-info">
                        <div class="contact-name">${escapeHtml(displayName)}</div>
                    </div>
                </div>
            `;
        }).join('');
        
        // Add search functionality
        const searchInput = document.getElementById('groupMemberSearch');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                const query = e.target.value.toLowerCase();
                document.querySelectorAll('#groupContactsList .contact-item').forEach(item => {
                    const name = item.querySelector('.contact-name').textContent.toLowerCase();
                    item.style.display = name.includes(query) ? 'flex' : 'none';
                });
            });
        }
    }

    // Handle create group form
    async handleCreateGroup(event) {
        event.preventDefault();
        
        const name = document.getElementById('newGroupName').value.trim();
        const description = document.getElementById('newGroupDescription').value.trim();
        const membersText = document.getElementById('newGroupMembers').value.trim();
        
        // Parse phone numbers
        const phoneNumbers = membersText.split(',').map(p => p.trim()).filter(p => p);
        
        if (phoneNumbers.length === 0) {
            showToast('Please add at least one member', 'warning');
            return;
        }
        
        // Create or get users for each phone number
        const memberIds = [];
        for (const phone of phoneNumbers) {
            try {
                const response = await authManager.authenticatedRequest(
                    `/auth/users/create-or-get?phone_number=${encodeURIComponent(phone)}`,
                    { method: 'POST' }
                );
                
                if (response.ok) {
                    const user = await response.json();
                    memberIds.push(user.id);
                } else {
                    showToast(`Failed to add ${phone}`, 'error');
                }
            } catch (error) {
                console.error(`Error adding ${phone}:`, error);
                showToast(`Error adding ${phone}`, 'error');
            }
        }
        
        if (memberIds.length === 0) {
            showToast('Failed to add any members', 'error');
            return;
        }
        
        // Create group
        const group = await this.createGroup(name, description, memberIds);
        
        if (group) {
            document.querySelector('.modal').remove();
        }
    }

    // Show edit group modal
    async showEditGroupModal(groupId) {
        const group = await this.getGroup(groupId);
        if (!group) return;

        // Close existing modals
        document.querySelectorAll('.modal').forEach(m => m.remove());

        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Edit Group</h2>
                    <button class="btn-icon" onclick="this.closest('.modal').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <form onsubmit="groupManager.handleEditGroup(event, '${groupId}')">
                        <div class="form-group">
                            <label>Group Name</label>
                            <input type="text" id="editGroupName" class="form-control" 
                                   value="${escapeHtml(group.name)}" required>
                        </div>
                        <div class="form-group">
                            <label>Description</label>
                            <textarea id="editGroupDescription" class="form-control" 
                                      rows="3">${escapeHtml(group.description || '')}</textarea>
                        </div>
                        <div class="form-actions">
                            <button type="button" class="btn btn-secondary" 
                                    onclick="this.closest('.modal').remove()">Cancel</button>
                            <button type="submit" class="btn btn-primary">Save Changes</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        setTimeout(() => modal.classList.add('show'), 10);
    }

    // Handle edit group form
    async handleEditGroup(event, groupId) {
        event.preventDefault();
        
        const name = document.getElementById('editGroupName').value.trim();
        const description = document.getElementById('editGroupDescription').value.trim();
        
        const success = await this.updateGroup(groupId, { name, description });
        
        if (success) {
            document.querySelector('.modal').remove();
        }
    }
}

// Global instance
const groupManager = new GroupManager();

// Helper function
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}
