// Configuration
const API_BASE_URL = 'http://localhost:8000/api';
const WS_BASE_URL = 'ws://localhost:8000';

// Storage keys
const STORAGE_KEYS = {
    TOKEN: 'whatsapp_token',
    USER: 'whatsapp_user',
    PHONE: 'whatsapp_phone'
};

// Export config
window.CONFIG = {
    API_BASE_URL,
    WS_BASE_URL,
    STORAGE_KEYS
};
