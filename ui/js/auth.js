// Authentication Module
class AuthManager {
    constructor() {
        this.token = localStorage.getItem(CONFIG.STORAGE_KEYS.TOKEN);
        this.user = JSON.parse(localStorage.getItem(CONFIG.STORAGE_KEYS.USER) || 'null');
        this.phone = localStorage.getItem(CONFIG.STORAGE_KEYS.PHONE);
    }

    // Request OTP
    async requestOTP(phoneNumber) {
        try {
            showLoading();
            const response = await fetch(`${CONFIG.API_BASE_URL}/auth/request-otp`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ phone_number: phoneNumber })
            });

            const data = await response.json();
            hideLoading();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to request OTP');
            }

            this.phone = phoneNumber;
            localStorage.setItem(CONFIG.STORAGE_KEYS.PHONE, phoneNumber);
            showToast('OTP sent successfully!', 'success');
            return true;
        } catch (error) {
            hideLoading();
            showToast(error.message, 'error');
            return false;
        }
    }

    // Verify OTP and Login
    async verifyOTP(otp) {
        try {
            showLoading();
            const response = await fetch(`${CONFIG.API_BASE_URL}/auth/verify-otp`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    phone_number: this.phone,
                    otp_code: otp
                })
            });

            const data = await response.json();
            hideLoading();

            if (!response.ok) {
                throw new Error(data.detail || 'Invalid OTP');
            }

            // Store authentication data
            this.token = data.access_token;
            this.user = data.user;
            localStorage.setItem(CONFIG.STORAGE_KEYS.TOKEN, this.token);
            localStorage.setItem(CONFIG.STORAGE_KEYS.USER, JSON.stringify(this.user));

            showToast('Login successful!', 'success');
            return true;
        } catch (error) {
            hideLoading();
            showToast(error.message, 'error');
            return false;
        }
    }

    // Get user profile
    async getProfile() {
        try {
            const response = await this.authenticatedRequest('/auth/users/me');
            if (response.ok) {
                const userData = await response.json();
                this.user = userData;
                localStorage.setItem(CONFIG.STORAGE_KEYS.USER, JSON.stringify(userData));
                return userData;
            }
            return null;
        } catch (error) {
            console.error('Failed to get profile:', error);
            return null;
        }
    }

    // Make authenticated request
    async authenticatedRequest(endpoint, options = {}) {
        const headers = {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json',
            ...options.headers
        };

        return fetch(`${CONFIG.API_BASE_URL}${endpoint}`, {
            ...options,
            headers
        });
    }

    // Search user by phone
    async searchUserByPhone(phoneNumber) {
        try {
            const response = await this.authenticatedRequest(
                `/auth/users/search?phone_number=${encodeURIComponent(phoneNumber)}`
            );
            
            if (response.ok) {
                return await response.json();
            }
            return null;
        } catch (error) {
            console.error('Failed to search user:', error);
            return null;
        }
    }

    // Logout
    logout() {
        this.token = null;
        this.user = null;
        this.phone = null;
        localStorage.removeItem(CONFIG.STORAGE_KEYS.TOKEN);
        localStorage.removeItem(CONFIG.STORAGE_KEYS.USER);
        localStorage.removeItem(CONFIG.STORAGE_KEYS.PHONE);
        
        // Disconnect WebSocket if connected
        if (window.wsManager) {
            window.wsManager.disconnect();
        }
        
        showToast('Logged out successfully', 'info');
        window.location.reload();
    }

    // Load/refresh user profile
    async loadUserProfile() {
        try {
            const response = await this.authenticatedRequest('/auth/users/me');
            if (response.ok) {
                this.user = await response.json();
                localStorage.setItem(CONFIG.STORAGE_KEYS.USER, JSON.stringify(this.user));
                console.log('User profile loaded:', this.user);
                return this.user;
            }
        } catch (error) {
            console.error('Error loading user profile:', error);
        }
        return null;
    }

    // Check if user is authenticated
    isAuthenticated() {
        return this.token !== null && this.user !== null;
    }

    // Get current user
    getCurrentUser() {
        return this.user;
    }

    // Get auth token
    getToken() {
        return this.token;
    }
}

// Export auth manager
window.authManager = new AuthManager();
