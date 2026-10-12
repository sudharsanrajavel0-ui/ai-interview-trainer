const API_BASE = '';

function getToken() {
    return localStorage.getItem('token');
}

function setToken(token) {
    localStorage.setItem('token', token);
}

function clearToken() {
    localStorage.removeItem('token');
}

function isLoggedIn() {
    return !!getToken();
}

function errorMessageToString(value) {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value;
    if (typeof value.message === 'string') return value.message;
    if (typeof value.detail === 'string') return value.detail;
    if (Array.isArray(value.detail)) {
        return value.detail.map(item => {
            if (typeof item === 'string') return item;
            if (item && typeof item.msg === 'string') return item.msg;
            try { return JSON.stringify(item); } catch (e) { return ''; }
        }).join(', ');
    }
    if (typeof value.detail === 'object') {
        const d = value.detail;
        if (typeof d.message === 'string') return d.message;
        if (typeof d.error === 'string') return d.error;
        try { return JSON.stringify(d); } catch (e) { return ''; }
    }
    if (typeof value.error === 'string') return value.error;
    if (value.error && typeof value.error.message === 'string') return value.error.message;
    try { return JSON.stringify(value); } catch (e) { return ''; }
}

function getErrorMessage(error) {
    if (!error) return 'An unexpected error occurred.';
    if (typeof error === 'string') return error || 'An unexpected error occurred.';
    if (error instanceof Error) {
        return errorMessageToString(error) || error.message || 'An unexpected error occurred.';
    }
    return errorMessageToString(error) || 'An unexpected error occurred.';
}

async function apiRequest(endpoint, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers,
        });

        if (response.status === 401) {
            clearToken();
            return null;
        }

        const contentType = response.headers.get('content-type') || '';
        let data;

        if (contentType.includes('application/json')) {
            data = await response.json();
        } else {
            const text = await response.text();
            console.error(`Non-JSON response (${response.status}):`, text);
            if (!response.ok) {
                throw new Error('Registration failed. Please try again.');
            }
            return text;
        }

        if (!response.ok) {
            const apiError = data.detail || data.message || 'Something went wrong';
            throw new Error(errorMessageToString(apiError) || 'Something went wrong');
        }

        return data;
    } catch (error) {
        if (error.message === 'Failed to fetch') {
            throw new Error('Unable to connect to server. Please try again.');
        }
        throw error;
    }
}

const api = {
    auth: {
        async register(data) {
            return apiRequest('/api/auth/register', {
                method: 'POST',
                body: JSON.stringify(data),
            });
        },
        async login(data) {
            const result = await apiRequest('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify(data),
            });
            if (!result) {
                throw new Error('Invalid email or password.');
            }
            if (result.access_token) {
                setToken(result.access_token);
            }
            return result;
        },
        async getMe() {
            return apiRequest('/api/auth/me');
        },
        logout() {
            clearToken();
        },
    },

    dashboard: {
        async getStats() {
            return apiRequest('/api/dashboard/stats');
        },
        async getLoginHistory() {
            return apiRequest('/api/dashboard/login_history');
        },
    },

    interviews: {
        async create(data) {
            return apiRequest('/api/interviews', {
                method: 'POST',
                body: JSON.stringify(data),
            });
        },
        async getQuestion(interviewId) {
            return apiRequest(`/api/interviews/${interviewId}/questions`, {
                method: 'POST',
            });
        },
        async submitAnswer(interviewId, answerText, selectedOption) {
            const body = {};
            if (answerText != null) body.answer_text = answerText;
            if (selectedOption != null) body.selected_option = selectedOption;
            return apiRequest(`/api/interviews/${interviewId}/answers`, {
                method: 'POST',
                body: JSON.stringify(body),
            });
        },
        async complete(interviewId) {
            return apiRequest(`/api/interviews/${interviewId}/complete`, {
                method: 'POST',
            });
        },
        async getOne(interviewId) {
            return apiRequest(`/api/interviews/${interviewId}`);
        },
        async getAll() {
            return apiRequest('/api/interviews');
        },
    },
};
