import axios from 'axios';

const api = axios.create({
    baseURL: process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add a request interceptor to include the appropriate token based on the request type
api.interceptors.request.use(
    (config) => {
        // For admin endpoints (tenant registration), use admin API key
        if (config.url && config.url.includes('/admin/')) {
            const adminKey = process.env.REACT_APP_ADMIN_API_KEY;
            if (adminKey) {
                config.headers['X-Admin-API-Key'] = adminKey;
            }
            return config;
        }

        // For tenant-level endpoints, use plexus_user_auth_token
        const plexusToken = localStorage.getItem('plexus_user_auth_token');
        const jwtToken = localStorage.getItem('jwt_token');

        console.log('API Request - URL:', config.url);
        console.log('API Request - Plexus token exists:', !!plexusToken);
        console.log('API Request - JWT token exists:', !!jwtToken);

        if (plexusToken) {
            config.headers.Authorization = `Bearer ${plexusToken}`;
            console.log('API Request - Using Plexus token');
        } else if (jwtToken) {
            config.headers.Authorization = `Bearer ${jwtToken}`;
            console.log('API Request - Using JWT token');
        } else {
            console.log('API Request - No token available');
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Add a response interceptor to handle authentication errors
api.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        if (error.response && error.response.status === 401) {
            // Token is invalid or expired, clear tokens and redirect to login
            localStorage.removeItem('jwt_token');
            localStorage.removeItem('plexus_user_auth_token');
            localStorage.removeItem('user_email');
            localStorage.removeItem('tenant_id');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

// Tenant management functions
export const tenantApi = {
    // Register a new tenant
    registerTenant: async (entityId, email) => {
        const response = await api.post('/admin/tenants/', {
            entity_id: entityId,
            email: email
        });
        return response.data;
    },

    // Register base configuration for tenant
    registerBaseConfig: async (entityId) => {
        const response = await api.post(`/${entityId}/plexus-auth/register-base-config`);
        return response.data;
    },

    // Get tenant integrations
    getIntegrations: async (entityId) => {
        const response = await api.get(`/${entityId}/integrations`);
        return response.data;
    },

    // Gmail integration functions
    // NOTE: Updated endpoints to align with MCP Plexus backend design
    //       The tenant entity ID is now inferred from the Plexus token rather than URL path.
    startGmailOAuth: async () => {
        // Backend expects POST /integrations/gmail/auth and returns { auth_url }
        const response = await api.post('/integrations/gmail/auth');
        return response.data;
    },

    getGmailStatus: async () => {
        // Backend exposes Gmail integration status at GET /integrations/gmail/status
        const response = await api.get('/integrations/gmail/status');
        return response.data;
    },

    disconnectGmail: async () => {
        // Disconnect tenant-level Gmail tokens via DELETE /integrations/gmail
        const response = await api.delete('/integrations/gmail');
        return response.data;
    },

    // Gmail email operations
    searchGmailEmails: async (entityId, query) => {
        const response = await api.post(`/${entityId}/gmail/search`, { query });
        return response.data;
    },

    getLastGmailEmail: async (entityId) => {
        const response = await api.get(`/${entityId}/gmail/last-email`);
        return response.data;
    },

    sendGmailEmail: async (entityId, emailData) => {
        const response = await api.post(`/${entityId}/gmail/send`, emailData);
        return response.data;
    },

    // Calendar integration functions
    startCalendarOAuth: async () => {
        // Use the calendar OAuth endpoint
        const response = await api.post('/integrations/calendar/auth');
        return response.data;
    },

    getCalendarStatus: async () => {
        // Use the calendar status endpoint
        const response = await api.get('/integrations/calendar/status');
        return response.data;
    },

    disconnectCalendar: async (entityId) => {
        // Use the unified integrations endpoint
        const response = await api.delete('/integrations/calendar');
        return response.data;
    },

    // Calendar operations
    getCalendarEvents: async (entityId, timeMin, timeMax) => {
        const response = await api.get(`/${entityId}/calendar/events`, {
            params: { timeMin, timeMax }
        });
        return response.data;
    },

    createCalendarEvent: async (entityId, eventId, eventData) => {
        const response = await api.post(`/${entityId}/calendar/events`, eventData);
        return response.data;
    },

    updateCalendarEvent: async (entityId, eventId, eventData) => {
        const response = await api.put(`/${entityId}/calendar/events/${eventId}`, eventData);
        return response.data;
    },

    deleteCalendarEvent: async (entityId, eventId) => {
        const response = await api.delete(`/${entityId}/calendar/events/${eventId}`);
        return response.data;
    }
};

// Chatbot API functions
export const chatbotApi = {
    // Create a new chat session
    createNewChat: async (userId, tenantId, integrations = []) => {
        const response = await api.post('/api/chatbot/new-chat', {
            user_id: userId,
            tenant_id: tenantId,
            integrations: integrations
        });
        return response.data;
    },

    // Send a message to the chatbot
    sendMessage: async (chatId, message, integrations = [], token = null) => {
        const requestData = {
            chat_id: chatId,
            message: message,
            integrations: integrations
        };

        // Add token if provided
        if (token) {
            requestData.token = token;
        }

        const response = await api.post('/api/chatbot/message', requestData);
        return response.data;
    },

    // Continue an existing chat
    continueChat: async (chatId, message, integrations = [], token = null) => {
        const requestData = {
            message: message,
            integrations: integrations
        };

        // Add token if provided
        if (token) {
            requestData.token = token;
        }

        const response = await api.post(`/api/chatbot/chat/${chatId}/continue`, requestData);
        return response.data;
    },

    // Get chat history
    getChatHistory: async (chatId, limit = 50) => {
        const response = await api.get(`/api/chatbot/chat/${chatId}/history`, {
            params: { limit }
        });
        return response.data;
    },

    // Get user's chat sessions
    getUserChats: async (userId, limit = 20) => {
        const response = await api.get(`/api/chatbot/chats/${userId}`, {
            params: { limit }
        });
        return response.data;
    },

    // Get chatbot status
    getStatus: async () => {
        const response = await api.get('/api/chatbot/status');
        return response.data;
    },

    // Get storage statistics
    getStorageStats: async () => {
        const response = await api.get('/api/chatbot/storage/stats');
        return response.data;
    }
};

export default api;
