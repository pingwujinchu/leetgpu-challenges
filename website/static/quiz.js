// LeetGPU Quiz Functionality

let quizData = {
    questions: [],
    currentQuestion: 0,
    answers: {},
    startTime: null,
    timerInterval: null
};

// Start quiz
async function startQuiz() {
    const difficulty = document.getElementById('quiz-difficulty').value;
    const count = document.getElementById('quiz-count').value;
    
    try {
        const response = await fetch(`/api/quiz/generate?difficulty=${difficulty}&count=${count}`);
        const data = await response.json();
        
        quizData.questions = data.questions;
        quizData.currentQuestion = 0;
        quizData.answers = {};
        quizData.startTime = Date.now();
        
        // Hide setup, show quiz
        document.getElementById('quiz-setup').style.display = 'none';
        document.getElementById('quiz-container').style.display = 'block';
        
        // Update total
        document.getElementById('quiz-total').textContent = data.total;
        
        // Create navigation dots
        createNavigationDots();
        
        // Start timer
        startTimer();
        
        // Load first question
        loadQuestion(0);
    } catch (error) {
        console.error('Error starting quiz:', error);
        alert('启动测验失败，请稍后再试');
    }
}

// Create navigation dots
function createNavigationDots() {
    const navDots = document.getElementById('quiz-nav-dots');
    navDots.innerHTML = '';
    
    quizData.questions.forEach((q, index) => {
        const dot = document.createElement('div');
        dot.className = 'nav-dot';
        dot.textContent = index + 1;
        dot.onclick = () => loadQuestion(index);
        navDots.appendChild(dot);
    });
    
    updateNavigationDots();
}

// Update navigation dots
function updateNavigationDots() {
    const dots = document.querySelectorAll('.nav-dot');
    dots.forEach((dot, index) => {
        dot.classList.remove('active');
        if (quizData.answers[index] !== undefined) {
            dot.classList.add('answered');
        }
        if (index === quizData.currentQuestion) {
            dot.classList.add('active');
        }
    });
}

// Start timer
function startTimer() {
    quizData.timerInterval = setInterval(() => {
        const elapsed = Date.now() - quizData.startTime;
        const minutes = Math.floor(elapsed / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        
        document.getElementById('quiz-timer').textContent = 
            `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }, 1000);
}

// Load question
async function loadQuestion(index) {
    quizData.currentQuestion = index;
    const question = quizData.questions[index];
    
    // Update progress
    document.getElementById('quiz-current').textContent = index + 1;
    
    // Load challenge details
    try {
        const response = await fetch(`/api/challenge/${question.challenge_id}`);
        const challenge = await response.json();
        
        const questionDiv = document.getElementById('quiz-question');
        questionDiv.innerHTML = `
            <div class="challenge-header">
                <h2>${question.name}</h2>
                <div class="challenge-meta">
                    <span class="difficulty-badge difficulty-${question.difficulty}">
                        ${question.difficulty}
                    </span>
                    <span style="color: var(--text-muted);">题目 ${index + 1}/${quizData.questions.length}</span>
                </div>
            </div>
            <div class="challenge-content">
                ${challenge.html_content || question.description}
            </div>
            <div class="quiz-answer-section">
                <h3>你的理解程度</h3>
                <div class="answer-options">
                    <label class="answer-option">
                        <input type="radio" name="understanding" value="1" 
                            ${quizData.answers[index] === 1 ? 'checked' : ''}>
                        <span>完全不理解</span>
                    </label>
                    <label class="answer-option">
                        <input type="radio" name="understanding" value="2"
                            ${quizData.answers[index] === 2 ? 'checked' : ''}>
                        <span>部分理解</span>
                    </label>
                    <label class="answer-option">
                        <input type="radio" name="understanding" value="3"
                            ${quizData.answers[index] === 3 ? 'checked' : ''}>
                        <span>基本理解</span>
                    </label>
                    <label class="answer-option">
                        <input type="radio" name="understanding" value="4"
                            ${quizData.answers[index] === 4 ? 'checked' : ''}>
                        <span>完全理解</span>
                    </label>
                    <label class="answer-option">
                        <input type="radio" name="understanding" value="5"
                            ${quizData.answers[index] === 5 ? 'checked' : ''}>
                        <span>能够实现</span>
                    </label>
                </div>
            </div>
        `;
        
        // Add event listeners to radio buttons
        document.querySelectorAll('input[name="understanding"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                quizData.answers[index] = parseInt(e.target.value);
                updateNavigationDots();
            });
        });
        
        // Update button visibility
        document.getElementById('prev-btn').style.display = index === 0 ? 'none' : 'inline-block';
        document.getElementById('next-btn').style.display = 
            index === quizData.questions.length - 1 ? 'none' : 'inline-block';
        document.getElementById('submit-btn').style.display = 
            index === quizData.questions.length - 1 ? 'inline-block' : 'none';
        
        updateNavigationDots();
    } catch (error) {
        console.error('Error loading question:', error);
        questionDiv.innerHTML = '<p class="error">加载题目失败</p>';
    }
}

// Navigate to previous question
function previousQuestion() {
    if (quizData.currentQuestion > 0) {
        loadQuestion(quizData.currentQuestion - 1);
    }
}

// Navigate to next question
function nextQuestion() {
    if (quizData.currentQuestion < quizData.questions.length - 1) {
        loadQuestion(quizData.currentQuestion + 1);
    }
}

// Submit quiz
function submitQuiz() {
    // Stop timer
    clearInterval(quizData.timerInterval);
    
    // Calculate results
    const totalTime = Date.now() - quizData.startTime;
    const answeredCount = Object.keys(quizData.answers).length;
    const avgScore = answeredCount > 0 
        ? Object.values(quizData.answers).reduce((a, b) => a + b, 0) / answeredCount 
        : 0;
    
    // Categorize by difficulty
    const byDifficulty = {};
    quizData.questions.forEach((q, index) => {
        const diff = q.difficulty;
        if (!byDifficulty[diff]) {
            byDifficulty[diff] = { total: 0, answered: 0, score: 0 };
        }
        byDifficulty[diff].total++;
        if (quizData.answers[index] !== undefined) {
            byDifficulty[diff].answered++;
            byDifficulty[diff].score += quizData.answers[index];
        }
    });
    
    // Hide quiz, show results
    document.getElementById('quiz-container').style.display = 'none';
    document.getElementById('quiz-results').style.display = 'block';
    
    // Display results
    const minutes = Math.floor(totalTime / 60000);
    const seconds = Math.floor((totalTime % 60000) / 1000);
    
    let resultsHTML = `
        <div class="result-stat">
            <h3>总体成绩</h3>
            <p>完成题数: ${answeredCount} / ${quizData.questions.length}</p>
            <p>用时: ${minutes}分${seconds}秒</p>
            <p>平均理解度: ${avgScore.toFixed(2)} / 5.0</p>
        </div>
        <div class="result-breakdown">
            <h3>按难度统计</h3>
    `;
    
    Object.entries(byDifficulty).forEach(([diff, stats]) => {
        const avgDiffScore = stats.answered > 0 ? stats.score / stats.answered : 0;
        resultsHTML += `
            <div class="difficulty-result difficulty-${diff}">
                <h4>${diff.toUpperCase()}</h4>
                <p>完成: ${stats.answered} / ${stats.total}</p>
                <p>平均理解度: ${avgDiffScore.toFixed(2)} / 5.0</p>
            </div>
        `;
    });
    
    resultsHTML += '</div>';
    
    // Add recommendations
    if (avgScore < 2.5) {
        resultsHTML += `
            <div class="recommendation">
                <h3>📚 学习建议</h3>
                <p>建议从简单题目开始，逐步提升GPU编程基础知识。</p>
            </div>
        `;
    } else if (avgScore < 4.0) {
        resultsHTML += `
            <div class="recommendation">
                <h3>💪 学习建议</h3>
                <p>继续保持！可以尝试更多中等难度的题目来提升技能。</p>
            </div>
        `;
    } else {
        resultsHTML += `
            <div class="recommendation">
                <h3>🎉 学习建议</h3>
                <p>太棒了！可以挑战困难题目，进一步提升GPU编程能力。</p>
            </div>
        `;
    }
    
    document.getElementById('results-summary').innerHTML = resultsHTML;
}
