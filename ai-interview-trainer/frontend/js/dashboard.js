async function initDashboard() {
    if (!isLoggedIn()) {
        window.location.href = '/login';
        return;
    }

    try {
        const user = await api.auth.getMe();
        updateNavbar(user);
    } catch {
        window.location.href = '/login';
        return;
    }

    loadDashboardStats();
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

async function loadDashboardStats() {
    try {
        const stats = await api.dashboard.getStats();
        renderStats(stats);
        renderInterviewHistory(stats.recent_interviews);
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
