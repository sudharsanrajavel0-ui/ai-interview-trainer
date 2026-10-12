async function initResult() {
    if (!isLoggedIn()) {
        window.location.href = '/login';
        return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const interviewId = urlParams.get('id');

    if (!interviewId) {
        window.location.href = '/dashboard';
        return;
    }

    try {
        const interview = await api.interviews.getOne(interviewId);
        renderResults(interview);
    } catch (error) {
        console.error('Failed to load results:', error);
        document.getElementById('resultsContent').innerHTML = `
            <div class="empty-state">
                <h3>Could not load results</h3>
                <p>${error.message}</p>
                <a href="/dashboard" class="btn btn-primary">Back to Dashboard</a>
            </div>
        `;
    }
}

function renderResults(interview) {
    const avgScore = interview.total_score;
    const percentage = (avgScore / 10) * 100;

    let scoreClass = 'poor';
    let scoreLabel = 'Needs Improvement';
    if (avgScore >= 8) {
        scoreClass = 'excellent';
        scoreLabel = 'Excellent';
    } else if (avgScore >= 6) {
        scoreClass = 'good';
        scoreLabel = 'Good';
    } else if (avgScore >= 4) {
        scoreClass = 'average';
        scoreLabel = 'Average';
    }

    document.getElementById('scoreCircle').className = `score-circle ${scoreClass}`;
    document.getElementById('scoreValue').textContent = avgScore.toFixed(1);
    document.getElementById('overallFeedback').textContent = interview.overall_feedback || 'We couldn\u2019t load your feedback right now. Please try again later.';

    const questionsHtml = (interview.questions || [])
        .filter(q => q.answer)
        .map(q => {
            const score = q.answer.score;
            let badgeClass = 'low';
            if (score >= 7) badgeClass = 'high';
            else if (score >= 5) badgeClass = 'medium';

            const strengths = q.answer.feedback ? q.answer.feedback.strengths || [] : [];
            const weaknesses = q.answer.feedback ? q.answer.feedback.weaknesses || [] : [];
            const modelAnswer = q.answer.feedback ? q.answer.feedback.model_answer : '';

            return `
                <div class="card question-result">
                    <div class="question-result-header">
                        <h4>Q${q.question_number}: ${q.question_text}</h4>
                        <span class="feedback-score ${badgeClass}">${score}/10</span>
                    </div>
                    <p style="font-size: 0.85rem; color: var(--gray-600); margin-bottom: 0.75rem;">
                        <strong>Your answer:</strong> ${truncate(q.answer.candidate_answer, 200)}
                    </p>
                    ${strengths.length > 0 ? `
                        <div style="margin-bottom: 0.5rem;">
                            <strong style="font-size: 0.8rem; color: var(--success);">Strengths:</strong>
                            <ul class="feedback-list strengths">
                                ${strengths.map(s => `<li>${s}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    ${weaknesses.length > 0 ? `
                        <div style="margin-bottom: 0.5rem;">
                            <strong style="font-size: 0.8rem; color: var(--danger);">Weaknesses:</strong>
                            <ul class="feedback-list weaknesses">
                                ${weaknesses.map(w => `<li>${w}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    ${modelAnswer ? `
                        <details style="margin-top: 0.5rem;">
                            <summary style="font-size: 0.8rem; color: var(--primary); cursor: pointer;">View model answer</summary>
                            <p style="font-size: 0.85rem; color: var(--gray-600); margin-top: 0.5rem; padding: 0.75rem; background: var(--gray-50); border-radius: var(--radius-sm);">${modelAnswer}</p>
                        </details>
                    ` : ''}
                </div>
            `;
        }).join('');

    document.getElementById('questionsResults').innerHTML = questionsHtml;

    document.getElementById('btnRetake').href = '/interview';
    document.getElementById('btnDashboard').href = '/dashboard';
}

function truncate(text, maxLen) {
    if (!text) return '';
    if (text.length <= maxLen) return text;
    return text.substring(0, maxLen) + '...';
}
