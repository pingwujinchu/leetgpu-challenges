// LeetGPU Online Testing Website - Main JavaScript

let allChallenges = [];
let currentFilter = 'all';
let currentGPU = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', async () => {
    await loadStats();
    await loadChallenges();
    await loadGPUModels();
    setupEventListeners();
});

// Load statistics
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        document.getElementById('total-challenges').textContent = stats.total;
        document.getElementById('easy-challenges').textContent = stats.by_difficulty.easy || 0;
        document.getElementById('medium-challenges').textContent = stats.by_difficulty.medium || 0;
        document.getElementById('hard-challenges').textContent = stats.by_difficulty.hard || 0;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load all challenges
async function loadChallenges(difficulty = null, search = '') {
    try {
        let url = '/api/challenges';
        const params = new URLSearchParams();
        if (difficulty) params.append('difficulty', difficulty);
        if (search) params.append('search', search);
        
        if (params.toString()) url += '?' + params.toString();
        
        const response = await fetch(url);
        allChallenges = await response.json();
        
        displayChallenges(allChallenges);
    } catch (error) {
        console.error('Error loading challenges:', error);
        document.getElementById('challenges-grid').innerHTML = 
            '<p class="error">加载失败，请稍后再试</p>';
    }
}

// Display challenges in grid
function displayChallenges(challenges) {
    const grid = document.getElementById('challenges-grid');
    
    if (challenges.length === 0) {
        grid.innerHTML = '<p class="loading">没有找到相关题目</p>';
        return;
    }
    
    grid.innerHTML = challenges.map(challenge => `
        <div class="challenge-card" onclick="viewChallenge('${challenge.id}')">
            <div class="challenge-meta">
                <span class="difficulty-badge difficulty-${challenge.difficulty}">
                    ${challenge.difficulty}
                </span>
                <span style="color: var(--text-muted); font-size: 0.9rem;">
                    #${challenge.id}
                </span>
            </div>
            <h3>${challenge.name}</h3>
            <p>${challenge.description || '暂无描述'}</p>
            ${challenge.frameworks && challenge.frameworks.length > 0 ? `
                <div class="frameworks-tags">
                    ${challenge.frameworks.slice(0, 3).map(fw => 
                        `<span class="framework-tag">${fw}</span>`
                    ).join('')}
                    ${challenge.frameworks.length > 3 ? 
                        `<span class="framework-tag">+${challenge.frameworks.length - 3}</span>` : ''}
                </div>
            ` : ''}
        </div>
    `).join('');
}

// Load GPU models
async function loadGPUModels() {
    try {
        const response = await fetch('/api/gpu-models');
        const gpuModels = await response.json();
        
        const select = document.getElementById('gpu-select');
        
        // Create optgroups for each vendor
        Object.entries(gpuModels).forEach(([vendor, models]) => {
            const optgroup = document.createElement('optgroup');
            optgroup.label = vendor.toUpperCase();
            
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = `${vendor}:${model.name}`;
                option.textContent = `${model.name} (${model.compute}, ${model.memory})`;
                option.dataset.compute = model.compute;
                option.dataset.memory = model.memory;
                option.dataset.vendor = vendor;
                optgroup.appendChild(option);
            });
            
            select.appendChild(optgroup);
        });
    } catch (error) {
        console.error('Error loading GPU models:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            const difficulty = e.target.dataset.difficulty;
            currentFilter = difficulty;
            loadChallenges(difficulty === 'all' ? null : difficulty, 
                          document.getElementById('search-input').value);
        });
    });
    
    // Search input
    const searchInput = document.getElementById('search-input');
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            loadChallenges(
                currentFilter === 'all' ? null : currentFilter,
                e.target.value
            );
        }, 300);
    });
    
    // GPU selector
    document.getElementById('gpu-select').addEventListener('change', (e) => {
        if (e.target.value) {
            const option = e.target.selectedOptions[0];
            currentGPU = {
                name: e.target.value.split(':')[1],
                vendor: option.dataset.vendor,
                compute: option.dataset.compute,
                memory: option.dataset.memory
            };
            displayGPUInfo(currentGPU);
        } else {
            currentGPU = null;
            document.getElementById('gpu-info').style.display = 'none';
        }
    });
}

// Display GPU information
function displayGPUInfo(gpu) {
    const gpuInfo = document.getElementById('gpu-info');
    const gpuDetails = document.getElementById('gpu-details');
    
    gpuDetails.innerHTML = `
        <div class="gpu-detail-item">
            <span>型号:</span>
            <strong>${gpu.name}</strong>
        </div>
        <div class="gpu-detail-item">
            <span>厂商:</span>
            <strong>${gpu.vendor.toUpperCase()}</strong>
        </div>
        <div class="gpu-detail-item">
            <span>计算能力:</span>
            <strong>${gpu.compute}</strong>
        </div>
        <div class="gpu-detail-item">
            <span>显存:</span>
            <strong>${gpu.memory}</strong>
        </div>
    `;
    
    gpuInfo.style.display = 'block';
}

// View challenge detail
function viewChallenge(challengeId) {
    window.location.href = `/challenge/${challengeId}`;
}

// Utility function to get difficulty color
function getDifficultyColor(difficulty) {
    const colors = {
        easy: '#22c55e',
        medium: '#eab308',
        hard: '#ef4444'
    };
    return colors[difficulty] || '#6366f1';
}
