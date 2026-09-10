function initAuthPage() {
    if (isLoggedIn()) {
        window.location.href = '/dashboard';
        return;
    }

    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const btn = document.getElementById('loginBtn');
    const errorDiv = document.getElementById('loginError');

    if (!email || !password) {
        showError(errorDiv, 'Please fill in all fields');
        return;
    }

    setLoading(btn, true);
    hideError(errorDiv);

    try {
        const result = await api.auth.login({ email, password });
        if (result && result.access_token) {
            window.location.href = '/training';
        } else {
            showError(errorDiv, 'Invalid email or password.');
        }
    } catch (error) {
        showError(errorDiv, error.message || 'Invalid email or password.');
    } finally {
        setLoading(btn, false);
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const fullName = document.getElementById('fullName').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const btn = document.getElementById('registerBtn');
    const errorDiv = document.getElementById('registerError');

    if (!fullName || !email || !password || !confirmPassword) {
        showError(errorDiv, 'Please fill in all fields');
        return;
    }

    if (fullName.length < 2) {
        showError(errorDiv, 'Name must be at least 2 characters');
        return;
    }

    if (password.length < 6) {
        showError(errorDiv, 'Password must be at least 6 characters');
        return;
    }

    if (password !== confirmPassword) {
        showError(errorDiv, 'Passwords do not match');
        return;
    }

    setLoading(btn, true);
    hideError(errorDiv);

    try {
        await api.auth.register({ full_name: fullName, email, password });
        const result = await api.auth.login({ email, password });
        if (result && result.access_token) {
            window.location.href = '/training';
        } else {
            showError(errorDiv, 'Account created but login failed. Please sign in manually.');
        }
    } catch (error) {
        showError(errorDiv, error.message);
    } finally {
        setLoading(btn, false);
    }
}

function showError(element, message) {
    if (element) {
        element.textContent = message;
        element.classList.remove('hidden');
    }
}

function hideError(element) {
    if (element) {
        element.textContent = '';
        element.classList.add('hidden');
    }
}

function setLoading(button, loading) {
    if (!button) return;
    if (loading) {
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<span class="spinner"></span> Please wait...';
    } else {
        button.disabled = false;
        button.innerHTML = button.dataset.originalText || button.innerHTML;
    }
}
