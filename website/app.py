#!/usr/bin/env python3
"""
LeetGPU Online Testing Website - Flask Backend
Supports different GPU models and provides a quiz interface for GPU programming challenges
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
import json
import os
from pathlib import Path

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# Load challenges metadata
CHALLENGES_FILE = 'challenges.json'
challenges_data = []

def load_challenges():
    global challenges_data
    try:
        with open(CHALLENGES_FILE, 'r') as f:
            challenges_data = json.load(f)
        print(f"Loaded {len(challenges_data)} challenges")
    except FileNotFoundError:
        print(f"Warning: {CHALLENGES_FILE} not found. Run generate_challenge_metadata.py first.")
        challenges_data = []

@app.route('/')
def index():
    """Main page - Challenge list"""
    return render_template('index.html')

@app.route('/api/challenges')
def get_challenges():
    """Get all challenges with optional filtering"""
    difficulty = request.args.get('difficulty', None)
    search = request.args.get('search', '').lower()
    
    filtered_challenges = challenges_data
    
    # Filter by difficulty
    if difficulty:
        filtered_challenges = [c for c in filtered_challenges if c['difficulty'] == difficulty]
    
    # Filter by search term
    if search:
        filtered_challenges = [
            c for c in filtered_challenges 
            if search in c['name'].lower() or search in c.get('description', '').lower()
        ]
    
    return jsonify(filtered_challenges)

@app.route('/api/challenge/<path:challenge_id>')
def get_challenge(challenge_id):
    """Get detailed challenge information"""
    challenge = next((c for c in challenges_data if c['id'] == challenge_id), None)
    
    if not challenge:
        return jsonify({'error': 'Challenge not found'}), 404
    
    # Load the HTML content
    html_path = os.path.join('..', challenge['path'], 'challenge.html')
    try:
        with open(html_path, 'r') as f:
            challenge['html_content'] = f.read()
    except FileNotFoundError:
        challenge['html_content'] = '<p>Challenge description not found</p>'
    
    return jsonify(challenge)

@app.route('/api/quiz/generate')
def generate_quiz():
    """Generate a random quiz based on difficulty and count"""
    difficulty = request.args.get('difficulty', 'all')
    count = int(request.args.get('count', 10))
    
    import random
    
    # Filter by difficulty
    if difficulty == 'all':
        quiz_pool = challenges_data
    else:
        quiz_pool = [c for c in challenges_data if c['difficulty'] == difficulty]
    
    # Randomly select challenges
    selected = random.sample(quiz_pool, min(count, len(quiz_pool)))
    
    # Create quiz questions
    quiz_questions = []
    for idx, challenge in enumerate(selected):
        quiz_questions.append({
            'id': idx + 1,
            'challenge_id': challenge['id'],
            'name': challenge['name'],
            'difficulty': challenge['difficulty'],
            'description': challenge.get('description', '')
        })
    
    return jsonify({
        'questions': quiz_questions,
        'total': len(quiz_questions)
    })

@app.route('/api/stats')
def get_stats():
    """Get overall statistics"""
    stats = {
        'total': len(challenges_data),
        'by_difficulty': {},
        'frameworks': set()
    }
    
    for challenge in challenges_data:
        diff = challenge['difficulty']
        stats['by_difficulty'][diff] = stats['by_difficulty'].get(diff, 0) + 1
        
        for fw in challenge.get('frameworks', []):
            stats['frameworks'].add(fw)
    
    stats['frameworks'] = sorted(list(stats['frameworks']))
    
    return jsonify(stats)

@app.route('/api/gpu-models')
def get_gpu_models():
    """Get list of supported GPU models"""
    gpu_models = {
        'nvidia': [
            {'name': 'RTX 4090', 'compute': '8.9', 'memory': '24GB'},
            {'name': 'RTX 4080', 'compute': '8.9', 'memory': '16GB'},
            {'name': 'RTX 3090', 'compute': '8.6', 'memory': '24GB'},
            {'name': 'RTX 3080', 'compute': '8.6', 'memory': '10GB'},
            {'name': 'A100', 'compute': '8.0', 'memory': '40GB/80GB'},
            {'name': 'H100', 'compute': '9.0', 'memory': '80GB'},
            {'name': 'V100', 'compute': '7.0', 'memory': '16GB/32GB'},
            {'name': 'T4', 'compute': '7.5', 'memory': '16GB'},
        ],
        'amd': [
            {'name': 'MI300X', 'compute': 'CDNA3', 'memory': '192GB'},
            {'name': 'MI250X', 'compute': 'CDNA2', 'memory': '128GB'},
            {'name': 'RX 7900 XTX', 'compute': 'RDNA3', 'memory': '24GB'},
            {'name': 'RX 6900 XT', 'compute': 'RDNA2', 'memory': '16GB'},
        ],
        'intel': [
            {'name': 'Data Center GPU Max 1550', 'compute': 'Xe-HPC', 'memory': '128GB'},
            {'name': 'Arc A770', 'compute': 'Xe-HPG', 'memory': '16GB'},
        ],
        'apple': [
            {'name': 'M3 Max', 'compute': 'Apple Silicon', 'memory': 'Unified 128GB'},
            {'name': 'M2 Ultra', 'compute': 'Apple Silicon', 'memory': 'Unified 192GB'},
        ]
    }
    return jsonify(gpu_models)

@app.route('/quiz')
def quiz_page():
    """Quiz interface page"""
    return render_template('quiz.html')

@app.route('/challenge/<path:challenge_id>')
def challenge_page(challenge_id):
    """Individual challenge detail page"""
    return render_template('challenge.html', challenge_id=challenge_id)

if __name__ == '__main__':
    # Load challenges on startup
    load_challenges()
    
    # Run the app
    print("\n" + "="*60)
    print("🚀 LeetGPU Online Testing Website")
    print("="*60)
    print(f"📊 Loaded {len(challenges_data)} challenges")
    print("🌐 Server starting at http://localhost:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
