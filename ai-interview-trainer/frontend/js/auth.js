// CHANGED: Email domain validation constants — only @gmail.com addresses are allowed
const EMAIL_DOMAIN_ERROR = 'Only @gmail.com email addresses are allowed.';

function isEmailDomainValid(email) {
    if (typeof email !== 'string' || !email) return false;
    // CHANGED: reject whitespace and any domain other than gmail.com (case-insensitive)
    return /^[^@\s]+@gmail\.com$/i.test(email.trim());
}

// CHANGED: Password policy — preserve minimum length and add strict rules.
// Allowed special characters are only ! and @; an uppercase letter, a lowercase
// letter and a number are all required.
function getPasswordPolicyError(password) {
    if (!password || password.length < 6) return 'Password must be at least 6 characters long.';
    if (!/[A-Z]/.test(password)) return 'Password must contain at least one uppercase letter.';
    if (!/[a-z]/.test(password)) return 'Password must contain at least one lowercase letter.';
    if (!/[0-9]/.test(password)) return 'Password must contain at least one number.';
    if (/[^A-Za-z0-9!@]/.test(password)) return 'Password may contain only ! and @ as special characters.';
    return null;
}

// CHANGED: Password notification helpers
function getPasswordNotificationElement() {
    return document.getElementById('passwordMessage');
}

function showPasswordNotification(message, type) {
    const el = getPasswordNotificationElement();
    if (!el) return;
    el.textContent = message;
    el.classList.remove('hidden');
    if (type === 'success') {
        el.classList.add('alert-success');
        el.classList.remove('alert-error', 'alert-info');
    } else if (type === 'error') {
        el.classList.add('alert-error');
        el.classList.remove('alert-success', 'alert-info');
    } else {
        el.classList.add('alert-info');
        el.classList.remove('alert-success', 'alert-error');
    }
}

function hidePasswordNotification() {
    const el = getPasswordNotificationElement();
    if (el) {
        el.textContent = '';
        el.classList.add('hidden');
        el.classList.remove('alert-success', 'alert-error', 'alert-info');
    }
}

// CHANGED: Password notification — live validation on the register page
function initPasswordNotification() {
    const registerForm = document.getElementById('registerForm');
    const passwordInput = document.getElementById('password');
    const confirmInput = document.getElementById('confirmPassword');

    if (registerForm && passwordInput) {
        passwordInput.addEventListener('blur', () => {
            if (!passwordInput.value) return;
            const policyError = getPasswordPolicyError(passwordInput.value);
            if (policyError) {
                showPasswordNotification(policyError, 'error');
            } else if (confirmInput && confirmInput.value && passwordInput.value !== confirmInput.value) {
                showPasswordNotification('Passwords do not match.', 'error');
            } else {
                hidePasswordNotification();
            }
        });
        if (confirmInput) {
            confirmInput.addEventListener('blur', () => {
                if (!confirmInput.value) return;
                if (confirmInput.value !== passwordInput.value) {
                    showPasswordNotification('Passwords do not match.', 'error');
                } else {
                    hidePasswordNotification();
                }
            });
        }
        passwordInput.addEventListener('input', hidePasswordNotification);
        if (confirmInput) confirmInput.addEventListener('input', hidePasswordNotification);
    }

    // CHANGED: Password notification — clear login password hint while typing
    const loginForm = document.getElementById('loginForm');
    const loginPassword = loginForm ? document.getElementById('password') : null;
    if (loginPassword) {
        loginPassword.addEventListener('input', hidePasswordNotification);
    }
}

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

    initPasswordNotification();
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const btn = document.getElementById('loginBtn');
    const errorDiv = document.getElementById('loginError');

    hidePasswordNotification();

    if (!email) {
        showError(errorDiv, 'Please enter your email address');
        return;
    }
    // CHANGED: Email domain validation before authentication
    if (!isEmailDomainValid(email)) {
        showError(errorDiv, EMAIL_DOMAIN_ERROR);
        return;
    }
    if (!password) {
        showPasswordNotification('Please enter your password.', 'error');
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
        const message = error.message || 'Invalid email or password.';
        if (message.toLowerCase().indexOf('password') !== -1) {
            // CHANGED: Password notification — password-related failures appear near the password field
            showPasswordNotification(message, 'error');
        } else {
            showError(errorDiv, message);
        }
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

    hidePasswordNotification();

    if (!fullName || !email || !password || !confirmPassword) {
        showError(errorDiv, 'Please fill in all fields');
        return;
    }

    if (fullName.length < 2) {
        showError(errorDiv, 'Name must be at least 2 characters');
        return;
    }

    // CHANGED: Email domain validation before creating the account
    if (!isEmailDomainValid(email)) {
        showError(errorDiv, EMAIL_DOMAIN_ERROR);
        return;
    }

    // CHANGED: Password policy validation before creating the account
    const policyError = getPasswordPolicyError(password);
    if (policyError) {
        showPasswordNotification(policyError, 'error');
        return;
    }

    if (password !== confirmPassword) {
        showPasswordNotification('Passwords do not match.', 'error');
        return;
    }

    setLoading(btn, true);
    hideError(errorDiv);

    try {
        await api.auth.register({ full_name: fullName, email, password });
        // CHANGED: Password notification — success message for account creation
        showPasswordNotification('Account created successfully.', 'success');
        const result = await api.auth.login({ email, password });
        if (result && result.access_token) {
            window.location.href = '/training';
        } else {
            showError(errorDiv, 'Account created but login failed. Please sign in manually.');
        }
    } catch (error) {
        const message = error.message || 'Registration failed. Please try again.';
        if (message.toLowerCase().indexOf('password') !== -1) {
            showPasswordNotification(message, 'error');
        } else {
            showError(errorDiv, message);
        }
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