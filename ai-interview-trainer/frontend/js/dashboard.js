async function initDashboard() {
    if (!isLoggedIn()) {
        window.location.href = '/login';
        return;
    }

    try {
        const user = await api.auth.getMe();
        updateNavbar(user);
        loadDashboardStats(user);
    } catch {
        window.location.href = '/login';
        return;
    }
}

function updateNavbar(user) {
    const userSection = document.getElementById('userSection');
    if (userSection && user) {
        const initials = user.full_name
            .split(' ')
            .map(n => n[0])
            .join('')
            .toUpperCase()
            .substring(0, 2);

        userSection.innerHTML = `
            <div class="navbar-user">
                <div class="user-avatar">${initials}</div>
                <span style="font-size: 0.9rem; font-weight: 500;">${user.full_name}</span>
            </div>
            <a href="/dashboard">Dashboard</a>
            <button onclick="handleLogout()">Logout</button>
        `;
    }
}

function handleLogout() {
    api.auth.logout();
    window.location.href = '/login';
}

async function loadDashboardStats(user) {
    try {
        const [stats, loginHistory] = await Promise.all([
            api.dashboard.getStats(),
            api.dashboard.getLoginHistory().catch(() => []),
        ]);
        renderStats(stats);
        renderInterviewHistory(stats.recent_interviews);
        // CHANGED: User dashboard charts
        renderUserCharts(user, stats, loginHistory);
    } catch (error) {
        console.error('Failed to load dashboard:', error);
    }
}

function renderStats(stats) {
    document.getElementById('totalInterviews').textContent = stats.total_interviews;
    document.getElementById('completedInterviews').textContent = stats.completed_interviews;
    document.getElementById('averageScore').textContent = stats.average_score.toFixed(1);
    document.getElementById('highestScore').textContent = stats.highest_score.toFixed(1);
}

function renderInterviewHistory(interviews) {
    const tbody = document.getElementById('historyBody');
    if (!tbody) return;

    if (!interviews || interviews.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center" style="padding: 2rem;">
                    No interviews yet. Start your first interview!
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = interviews.map(interview => {
        const date = new Date(interview.created_at).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });

        return `
            <tr>
                <td>${interview.job_role}</td>
                <td><span class="badge badge-${interview.difficulty}">${interview.difficulty}</span></td>
                <td>${interview.total_score.toFixed(1)}</td>
                <td>${interview.total_questions} questions</td>
                <td><span class="badge badge-${interview.status === 'completed' ? 'completed' : 'in-progress'}">${interview.status.replace('_', ' ')}</span></td>
                <td>${date}</td>
            </tr>
        `;
    }).join('');
}

// CHANGED: User dashboard charts — only the currently authenticated user's data.
function renderUserCharts(user, stats, loginHistory) {
    // A. User login history (time-series chart) — from login events
    const history = loginHistory || [];
    const series = buildDateCountSeries(history, 'created_at');
    drawLineChart(document.getElementById('userChartLoginHistory'), {
        labels: series.labels,
        values: series.values,
        xLabel: 'Date',
        yLabel: 'Logins',
        emptyMessage: 'No login activity recorded yet.',
    });

    // B. Profile completion (progress visualization) — derived from the user's own record.
    renderProfileCompletion(user, stats);

    // C. User usage statistics (bar chart) — scoped to the authenticated user via /api/dashboard/stats.
    drawBarChart(document.getElementById('userChartUsage'), {
        labels: ['Interviews', 'Completed', 'Questions Answered'],
        values: [stats.total_interviews || 0, stats.completed_interviews || 0, stats.questions_answered || 0],
        xLabel: 'Usage',
        yLabel: 'Count',
        emptyMessage: 'No usage data available yet.',
    });
}

// CHANGED: User dashboard charts — profile completion progress bars from real user data.
function renderProfileCompletion(user, stats) {
    const container = document.getElementById('profileCompletion');
    if (!container) return;

    const items = [
        { label: 'Full name provided', done: !!(user.full_name && user.full_name.trim().length >= 2) },
        { label: 'Email address provided', done: !!(user.email) },
        { label: 'First interview started', done: (stats.total_interviews || 0) > 0 },
        { label: 'First interview completed', done: (stats.completed_interviews || 0) > 0 },
        { label: 'Received feedback', done: (stats.questions_answered || 0) > 0 },
    ];

    const doneCount = items.filter((i) => i.done).length;
    const percent = Math.round((doneCount / items.length) * 100);

    container.innerHTML = `
        <div class="progress-row" style="margin-bottom: 0.75rem;">
            <div class="progress-label" style="font-weight: 600;">Profile completion: ${percent}%</div>
            <div class="progress-track">
                <div class="progress-fill" style="width: ${percent}%;"></div>
            </div>
        </div>
        ${items.map((item) => `
            <div class="progress-row">
                <div class="progress-label">${item.label}</div>
                <div class="progress-track">
                    <div class="progress-fill ${item.done ? '' : 'is-empty'}" style="width: ${item.done ? 100 : 0}%;"></div>
                </div>
            </div>
        `).join('')}
    `;
}
