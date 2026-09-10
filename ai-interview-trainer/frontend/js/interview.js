let currentInterview = null;
let currentQuestion = null;
let questionCount = 0;
let isSubmitting = false;
let isLoadingQuestion = false;

async function initInterview() {
    if (!isLoggedIn()) {
        window.location.href = '/login';
        return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const interviewId = urlParams.get('id');

    if (interviewId) {
        await loadExistingInterview(parseInt(interviewId));
    } else {
        showSetupForm();
    }
}

function showSetupForm() {
    document.getElementById('setupSection').classList.remove('hidden');
    document.getElementById('interviewSection').classList.add('hidden');
    initSetupForm();
}

function initSetupForm() {
    const options = document.querySelectorAll('.option-card[data-field]');
    options.forEach(opt => {
        opt.addEventListener('click', () => {
            const field = opt.dataset.field;
            const value = opt.dataset.value;
            selectOption(field, value);
        });
    });

    const startBtn = document.getElementById('startBtn');
    if (startBtn) {
        startBtn.addEventListener('click', startInterview);
    }
}

function selectOption(field, value) {
    const group = document.querySelector(`[data-option-group="${field}"]`);
    if (!group) return;
    group.querySelectorAll('.option-card').forEach(card => {
        card.classList.remove('selected');
    });
    const selected = group.querySelector(`[data-value="${value}"]`);
    if (selected) selected.classList.add('selected');
    document.getElementById(field).value = value;

    if (field === 'jobRole') {
        const customInput = document.getElementById('customRole');
        if (value === 'Other') {
            customInput.classList.remove('hidden');
            customInput.focus();
        } else {
            customInput.classList.add('hidden');
            customInput.value = '';
        }
    }
}

function showInterviewError(message) {
    const errorDiv = document.getElementById('interviewError');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
    }
}

function hideInterviewError() {
    const errorDiv = document.getElementById('interviewError');
    if (errorDiv) {
        errorDiv.textContent = '';
        errorDiv.classList.add('hidden');
    }
}

function setQuestionLoading(loading) {
    const submitBtn = document.getElementById('submitBtn');
    const answerArea = document.getElementById('answerText');
    const loadingOverlay = document.getElementById('questionLoading');
    isLoadingQuestion = loading;

    if (loading) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Generating question...';
        answerArea.disabled = true;
        answerArea.value = '';
        hideFeedback();
        hideInterviewError();
        if (loadingOverlay) loadingOverlay.classList.remove('hidden');
    } else {
        if (loadingOverlay) loadingOverlay.classList.add('hidden');
    }
}

async function startInterview() {
    let jobRole = document.getElementById('jobRole').value;
    const interviewType = document.getElementById('interviewType').value;
    const difficulty = document.getElementById('difficulty').value;
    const totalQuestions = parseInt(document.getElementById('totalQuestions').value);
    const errorDiv = document.getElementById('setupError');

    if (jobRole === 'Other') {
        const customRole = document.getElementById('customRole').value.trim();
        if (!customRole) {
            errorDiv.textContent = 'Please enter your job role';
            errorDiv.classList.remove('hidden');
            return;
        }
        jobRole = customRole;
    }

    if (!jobRole || !interviewType || !difficulty || !totalQuestions) {
        errorDiv.textContent = 'Please select all options';
        errorDiv.classList.remove('hidden');
        return;
    }

    errorDiv.classList.add('hidden');

    try {
        currentInterview = await api.interviews.create({
            job_role: jobRole,
            interview_type: interviewType,
            difficulty: difficulty,
            total_questions: totalQuestions,
        });

        questionCount = 0;
        document.getElementById('setupSection').classList.add('hidden');
        document.getElementById('interviewSection').classList.remove('hidden');
        updateSidebar();
        await loadNextQuestion();
    } catch (error) {
        errorDiv.textContent = getErrorMessage(error);
        errorDiv.classList.remove('hidden');
    }
}

async function loadExistingInterview(interviewId) {
    try {
        currentInterview = await api.interviews.getOne(interviewId);

        if (currentInterview.status === 'completed') {
            window.location.href = `/result?id=${interviewId}`;
            return;
        }

        questionCount = currentInterview.current_question;
        document.getElementById('setupSection').classList.add('hidden');
        document.getElementById('interviewSection').classList.remove('hidden');
        updateSidebar();
        await loadNextQuestion();
    } catch (error) {
        console.error('Failed to load interview:', error);
        showSetupForm();
    }
}

async function loadNextQuestion() {
    if (isLoadingQuestion) return;

    if (questionCount >= currentInterview.total_questions) {
        await finishInterview();
        return;
    }

    const submitBtn = document.getElementById('submitBtn');
    const answerArea = document.getElementById('answerText');

    setQuestionLoading(true);

    try {
        currentQuestion = await api.interviews.getQuestion(currentInterview.id);
        questionCount++;

        document.getElementById('questionNumber').textContent = `Question ${currentQuestion.question_number} of ${currentInterview.total_questions}`;
        document.getElementById('questionText').textContent = currentQuestion.question_text;

        if (currentQuestion.question_type === 'mcq') {
            renderMcqOptions(currentQuestion.options || []);
            answerArea.classList.add('hidden');
            answerArea.value = '';
            document.getElementById('mcqOptions').classList.remove('hidden');
        } else {
            document.getElementById('mcqOptions').classList.add('hidden');
            document.getElementById('optionsList').innerHTML = '';
            answerArea.classList.remove('hidden');
        }

        setQuestionLoading(false);
        updateSidebar();
        answerArea.disabled = false;
        if (currentQuestion.question_type !== 'mcq') {
            answerArea.focus();
        }
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Submit Answer';
        submitBtn.onclick = submitAnswer;
    } catch (error) {
        setQuestionLoading(false);
        document.getElementById('questionText').textContent = 'Failed to load the question.';
        showInterviewError(getErrorMessage(error) || 'Unable to generate the interview question. Please try again.');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<span class="spinner"></span> Retry';
        submitBtn.onclick = retryLoadQuestion;
    }
}

function renderMcqOptions(options) {
    const container = document.getElementById('optionsList');
    container.innerHTML = '';
    options.forEach(option => {
        const label = document.createElement('label');
        label.className = 'mcq-option';
        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = 'mcqOption';
        radio.value = option;
        const span = document.createElement('span');
        span.className = 'mcq-option-text';
        span.textContent = option;
        label.appendChild(radio);
        label.appendChild(span);
        label.addEventListener('click', () => {
            container.querySelectorAll('.mcq-option').forEach(el => el.classList.remove('selected'));
            label.classList.add('selected');
            radio.checked = true;
        });
        container.appendChild(label);
    });
}

function getSelectedMcqOption() {
    const radios = document.querySelectorAll('input[name="mcqOption"]');
    for (const radio of radios) {
        if (radio.checked) return radio.value;
    }
    return null;
}

async function retryLoadQuestion() {
    await loadNextQuestion();
}

async function submitAnswer() {
    if (isSubmitting || isLoadingQuestion) return;

    const answerText = document.getElementById('answerText').value.trim();
    const submitBtn = document.getElementById('submitBtn');
    const errorDiv = document.getElementById('answerError');
    const isMcq = currentQuestion && currentQuestion.question_type === 'mcq';

    if (isMcq) {
        const selected = getSelectedMcqOption();
        if (!selected) {
            errorDiv.textContent = 'Please select an answer.';
            errorDiv.classList.remove('hidden');
            return;
        }
        errorDiv.classList.add('hidden');
        isSubmitting = true;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Evaluating...';
        document.querySelectorAll('input[name="mcqOption"]').forEach(r => r.disabled = true);

        try {
            const result = await api.interviews.submitAnswer(currentInterview.id, null, selected);
            showFeedback(result);

            if (questionCount >= currentInterview.total_questions) {
                document.getElementById('nextBtn').textContent = 'Finish Interview';
            }
            document.getElementById('nextBtn').classList.remove('hidden');
            document.getElementById('submitBtn').classList.add('hidden');
        } catch (error) {
            errorDiv.textContent = getErrorMessage(error);
            errorDiv.classList.remove('hidden');
            document.querySelectorAll('input[name="mcqOption"]').forEach(r => r.disabled = false);
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Submit Answer';
            submitBtn.onclick = submitAnswer;
        } finally {
            isSubmitting = false;
        }
        return;
    }

    if (!answerText) {
        errorDiv.textContent = 'Please type your answer before submitting';
        errorDiv.classList.remove('hidden');
        return;
    }

    errorDiv.classList.add('hidden');
    isSubmitting = true;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Evaluating...';
    document.getElementById('answerText').disabled = true;

    try {
        const result = await api.interviews.submitAnswer(currentInterview.id, answerText);
        showFeedback(result);

        if (questionCount >= currentInterview.total_questions) {
            document.getElementById('nextBtn').textContent = 'Finish Interview';
        }
        document.getElementById('nextBtn').classList.remove('hidden');
        document.getElementById('submitBtn').classList.add('hidden');
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
        document.getElementById('answerText').disabled = false;
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Submit Answer';
        submitBtn.onclick = submitAnswer;
    } finally {
        isSubmitting = false;
    }
}

async function nextQuestion() {
    document.getElementById('nextBtn').classList.add('hidden');
    document.getElementById('submitBtn').classList.remove('hidden');
    document.getElementById('submitBtn').onclick = submitAnswer;

    if (questionCount >= currentInterview.total_questions) {
        await finishInterview();
        return;
    }

    await loadNextQuestion();
}

function showFeedback(result) {
    const panel = document.getElementById('feedbackPanel');
    const scoreBadge = document.getElementById('feedbackScore');
    const strengthsList = document.getElementById('feedbackStrengths');
    const weaknessesList = document.getElementById('feedbackWeaknesses');
    const suggestionsList = document.getElementById('feedbackSuggestions');

    if (result.score >= 7) {
        scoreBadge.className = 'feedback-score high';
    } else if (result.score >= 5) {
        scoreBadge.className = 'feedback-score medium';
    } else {
        scoreBadge.className = 'feedback-score low';
    }

    scoreBadge.textContent = `Score: ${result.score}/10`;

    if (result.feedback) {
        strengthsList.innerHTML = (result.feedback.strengths || [])
            .map(s => `<li>${s}</li>`).join('');
        weaknessesList.innerHTML = (result.feedback.weaknesses || [])
            .map(w => `<li>${w}</li>`).join('');
        suggestionsList.innerHTML = (result.feedback.suggestions || [])
            .map(s => `<li>${s}</li>`).join('');
    }

    panel.classList.remove('hidden');
}

function hideFeedback() {
    document.getElementById('feedbackPanel').classList.add('hidden');
}

function updateSidebar() {
    if (!currentInterview) return;

    const progress = currentInterview.total_questions > 0
        ? (questionCount / currentInterview.total_questions) * 100
        : 0;

    document.getElementById('progressFill').style.width = `${progress}%`;
    document.getElementById('sidebarRole').textContent = currentInterview.job_role;
    document.getElementById('sidebarDifficulty').textContent = currentInterview.difficulty;
    document.getElementById('sidebarType').textContent = currentInterview.interview_type.replace('_', ' ');
    document.getElementById('sidebarProgress').textContent = `${questionCount}/${currentInterview.total_questions}`;
}

async function finishInterview() {
    try {
        await api.interviews.complete(currentInterview.id);
        window.location.href = `/result?id=${currentInterview.id}`;
    } catch (error) {
        console.error('Failed to complete interview:', error);
        window.location.href = `/result?id=${currentInterview.id}`;
    }
}
