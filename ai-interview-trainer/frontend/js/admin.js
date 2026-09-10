let adminData = {
    users: [],
    interviews: [],
    questions: [],
    answers: [],
    results: [],
};

function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatDate(value) {
    if (!value) return '-';
    const d = new Date(value);
    if (isNaN(d)) return escapeHtml(value);
    return d.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function formatList(items) {
    if (!items || items.length === 0) return '-';
    return items.join(', ');
}

function statusBadge(status) {
    const cls = String(status || '').replace('_', '-');
    return `<span class="badge badge-${escapeHtml(cls)}">${escapeHtml(String(status || '').replace('_', ' '))}</span>`;
}

async function adminFetch(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });

        if (response.status === 401) {
            window.location.href = '/admin/login';
            throw new Error('Admin authentication required');
        }

        if (!response.ok) {
            let detail = 'Request failed';
            try {
                const data = await response.json();
                if (data && data.detail) detail = data.detail;
            } catch (e) { /* ignore */ }
            throw new Error(detail);
        }

        return response.json();
    } catch (error) {
        if (error.message === 'Admin authentication required') throw error;
        throw new Error(error.message || 'Failed to connect to server.');
    }
}

function showAdminError(message) {
    const errorDiv = document.getElementById('adminLoginError');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
    }
}

function hideAdminError() {
    const errorDiv = document.getElementById('adminLoginError');
    if (errorDiv) {
        errorDiv.textContent = '';
        errorDiv.classList.add('hidden');
    }
}

function setAdminLoading(button, loading) {
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

function initAdminLoginPage() {
    const form = document.getElementById('adminLoginForm');
    if (!form) return;

    if (window.location.pathname === '/admin') {
        window.location.href = '/admin/login';
        return;
    }

    form.addEventListener('submit', handleAdminLogin);
}

async function handleAdminLogin(e) {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const btn = document.getElementById('adminLoginBtn');
    const errorDiv = document.getElementById('adminLoginError');

    if (!username || !password) {
        showAdminError('Please fill in all fields');
        return;
    }

    setAdminLoading(btn, true);
    hideAdminError();

    try {
        const response = await fetch('/api/admin/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });

        if (response.status === 401) {
            let detail = 'Invalid admin credentials';
            try {
                const data = await response.json();
                if (data && data.detail) detail = data.detail;
            } catch (err) { /* ignore */ }
            showAdminError(detail);
            return;
        }

        if (!response.ok) {
            showAdminError('Admin login failed. Please try again.');
            return;
        }

        window.location.href = '/admin';
    } catch (error) {
        showAdminError('Unable to connect to server. Please try again.');
    } finally {
        setAdminLoading(btn, false);
    }
}

async function initAdminDashboard() {
    try {
        await loadAllAdminData();
    } catch (error) {
        if (error.message && error.message.includes('authentication')) return;
    }
}

async function loadAllAdminData() {
    const [stats, users, interviews, questions, answers, results] = await Promise.all([
        adminFetch('/api/admin/stats'),
        adminFetch('/api/admin/users'),
        adminFetch('/api/admin/interviews'),
        adminFetch('/api/admin/questions'),
        adminFetch('/api/admin/answers'),
        adminFetch('/api/admin/results'),
    ]);

    adminData.users = users;
    adminData.interviews = interviews;
    adminData.questions = questions;
    adminData.answers = answers;
    adminData.results = results;

    renderStats(stats);
    renderTable('users', renderUsers);
    renderTable('interviews', renderInterviews);
    renderTable('questions', renderQuestions);
    renderTable('answers', renderAnswers);
    renderTable('results', renderResults);
}

function renderStats(stats) {
    document.getElementById('statUsers').textContent = stats.total_users ?? 0;
    document.getElementById('statInterviews').textContent = stats.total_interviews ?? 0;
    document.getElementById('statQuestions').textContent = stats.total_questions ?? 0;
    document.getElementById('statAnswers').textContent = stats.total_answers ?? 0;
    document.getElementById('statCompleted').textContent = stats.total_completed_interviews ?? 0;
    document.getElementById('statAverage').textContent = (stats.average_score ?? 0).toFixed(1);
}

function renderTable(key, renderFn) {
    const filterEl = document.getElementById('filter' + key.charAt(0).toUpperCase() + key.slice(1));
    const query = filterEl ? filterEl.value.toLowerCase() : '';
    const body = document.getElementById(key + 'Body');
    if (!body) return;

    const rows = renderFn(adminData[key], query);
    if (rows.length === 0) {
        body.innerHTML = `<tr><td colspan="9" class="text-center" style="padding: 1.5rem; color: var(--gray-500);">No records found.</td></tr>`;
        return;
    }
    body.innerHTML = rows.join('');
}

function renderUsers(users, query) {
    return users
        .filter(u => !query || `${u.full_name} ${u.email}`.toLowerCase().includes(query))
        .map(u => `
            <tr>
                <td>${u.id}</td>
                <td>${escapeHtml(u.full_name)}</td>
                <td>${escapeHtml(u.email)}</td>
                <td>${u.interview_count ?? 0}</td>
                <td>${u.completed_interviews ?? 0}</td>
                <td>${formatDate(u.created_at)}</td>
            </tr>`);
}

function renderInterviews(interviews, query) {
    return interviews
        .filter(i => !query || `${i.job_role} ${i.difficulty} ${i.interview_type} ${i.user_email} ${i.user_name} ${i.status}`.toLowerCase().includes(query))
        .map(i => `
            <tr>
                <td>${i.id}</td>
                <td>${escapeHtml(i.user_name)} (${escapeHtml(i.user_email)})</td>
                <td>${escapeHtml(i.job_role)}</td>
                <td>${escapeHtml(String(i.interview_type).replace('_', ' '))}</td>
                <td><span class="badge badge-${escapeHtml(i.difficulty)}">${escapeHtml(i.difficulty)}</span></td>
                <td>${statusBadge(i.status)}</td>
                <td>${i.total_score}</td>
                <td>${formatDate(i.created_at)}</td>
            </tr>`);
}

function renderQuestions(questions, query) {
    return questions
        .filter(q => !query || `${q.question_text} ${q.job_role} ${q.difficulty} ${q.question_type} ${q.user_email}`.toLowerCase().includes(query))
        .map(q => `
            <tr>
                <td>${q.id}</td>
                <td>${q.interview_id}</td>
                <td>${q.question_number}</td>
                <td>${escapeHtml(q.question_text)}</td>
                <td><span class="badge badge-user">${escapeHtml(q.question_type)}</span></td>
                <td>${escapeHtml(q.job_role)}</td>
                <td><span class="badge badge-${escapeHtml(q.difficulty)}">${escapeHtml(q.difficulty)}</span></td>
            </tr>`);
}

function renderAnswers(answers, query) {
    return answers
        .filter(a => !query || `${a.user_email} ${a.question_text} ${a.candidate_answer}`.toLowerCase().includes(query))
        .map(a => `
            <tr>
                <td>${a.id}</td>
                <td>${escapeHtml(a.user_name)} (${escapeHtml(a.user_email)})</td>
                <td>${escapeHtml(a.question_text)}</td>
                <td>${escapeHtml(a.candidate_answer)}</td>
                <td>${a.score}</td>
                <td>${escapeHtml(formatList(a.strengths))}</td>
            </tr>`);
}

function renderResults(results, query) {
    return results
        .filter(r => !query || `${r.user_email} ${r.question_text} ${r.candidate_answer} ${r.status}`.toLowerCase().includes(query))
        .map(r => `
            <tr>
                <td>${r.id}</td>
                <td>${escapeHtml(r.user_name)} (${escapeHtml(r.user_email)})</td>
                <td>${r.interview_id}</td>
                <td>${escapeHtml(r.question_text)}</td>
                <td>${r.score}</td>
                <td>${escapeHtml(formatList(r.strengths))}</td>
                <td>${escapeHtml(formatList(r.weaknesses))}</td>
                <td>${escapeHtml(formatList(r.suggestions))}</td>
                <td>${statusBadge(r.status)}</td>
            </tr>`);
}

function handleAdminLogout() {
    fetch('/api/admin/logout', { method: 'POST' })
        .then(() => { window.location.href = '/admin/login'; })
        .catch(() => { window.location.href = '/admin/login'; });
}

document.addEventListener('DOMContentLoaded', function () {
    const filters = ['users', 'interviews', 'questions', 'answers', 'results'];
    filters.forEach(key => {
        const el = document.getElementById('filter' + key.charAt(0).toUpperCase() + key.slice(1));
        if (el) {
            el.addEventListener('input', () => renderTable(key, key === 'users' ? renderUsers : key === 'interviews' ? renderInterviews : key === 'questions' ? renderQuestions : key === 'answers' ? renderAnswers : renderResults));
        }
    });

    const navLinks = document.querySelectorAll('.admin-sidebar-nav a');
    navLinks.forEach(link => {
        link.addEventListener('click', function () {
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
});