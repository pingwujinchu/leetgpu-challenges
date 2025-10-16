#!/usr/bin/env python3
"""
LeetGPU Online Testing Website - Flask Backend (Master Node)
主节点服务器 - 负责任务分发和资源监控
Supports different GPU models and provides a quiz interface for GPU programming challenges
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
from pathlib import Path
import numpy as np

# 导入主从架构模块
from config import GPU_WORKERS, MASTER_HOST, MASTER_PORT
from task_manager import TaskManager
from gpu_monitor import GPUMonitor
import requests

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)  # 启用CORS支持

# Load challenges metadata
CHALLENGES_FILE = 'challenges.json'
challenges_data = []

# 初始化任务管理器和GPU监控器
task_manager = None
gpu_monitor = None

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


# ============= 主从架构新增API =============

@app.route('/api/submit-task', methods=['POST'])
def submit_task():
    """提交GPU任务到Worker节点"""
    data = request.json
    
    if not data:
        return jsonify({'error': '缺少任务数据'}), 400
    
    code = data.get('code')
    inputs = data.get('inputs', [])
    grid_size = tuple(data.get('grid_size', [1]))
    block_size = tuple(data.get('block_size', [1]))
    gpu_model = data.get('gpu_model')
    
    if not code:
        return jsonify({'error': '缺少代码'}), 400
    
    # 提交任务
    task_id = task_manager.submit_task(
        code=code,
        inputs=inputs,
        grid_size=grid_size,
        block_size=block_size,
        gpu_model=gpu_model
    )
    
    return jsonify({
        'task_id': task_id,
        'status': 'queued',
        'message': '任务已提交到队列'
    })


@app.route('/api/task/<task_id>')
def get_task_status_route(task_id):
    """获取任务状态"""
    status = task_manager.get_task_status(task_id)
    
    if not status:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify(status)


@app.route('/api/tasks')
def get_all_tasks_route():
    """获取所有任务状态"""
    tasks = task_manager.get_all_tasks()
    return jsonify({
        'total': len(tasks),
        'tasks': tasks
    })


@app.route('/api/gpu/resources')
def get_gpu_resources():
    """获取所有GPU节点的资源使用情况"""
    resources = []
    
    # 获取所有Worker的状态
    worker_status = task_manager.get_worker_status()
    
    for worker in GPU_WORKERS:
        try:
            # 获取Worker的GPU状态
            url = f"http://{worker['host']}:{worker['port']}/gpu/status"
            response = requests.get(url, timeout=2)
            
            if response.status_code == 200:
                gpu_status = response.json()
                
                # 查找对应的worker状态
                ws = next((w for w in worker_status if w['id'] == worker['id']), {})
                
                resources.append({
                    'worker_id': worker['id'],
                    'worker_name': worker['name'],
                    'gpu_model': worker['gpu_model'],
                    'gpu_memory_total': worker['gpu_memory'],
                    'compute_capability': worker['compute_capability'],
                    'status': ws.get('status', 'unknown'),
                    'online': ws.get('online', False),
                    'gpu_utilization': gpu_status.get('gpu_utilization', 0),
                    'memory_utilization': gpu_status.get('memory_utilization', 0),
                    'memory_used': gpu_status.get('memory_used', 0),
                    'memory_free': gpu_status.get('memory_free', 0),
                    'temperature': gpu_status.get('temperature', 0),
                    'power_usage': gpu_status.get('power_usage', 0),
                    'timestamp': gpu_status.get('timestamp', '')
                })
        except Exception as e:
            # Worker不可访问，返回离线状态
            ws = next((w for w in worker_status if w['id'] == worker['id']), {})
            resources.append({
                'worker_id': worker['id'],
                'worker_name': worker['name'],
                'gpu_model': worker['gpu_model'],
                'gpu_memory_total': worker['gpu_memory'],
                'compute_capability': worker['compute_capability'],
                'status': 'offline',
                'online': False,
                'error': str(e)
            })
    
    return jsonify({
        'total_workers': len(resources),
        'resources': resources
    })


@app.route('/api/workers')
def get_workers():
    """获取所有Worker节点信息"""
    worker_status = task_manager.get_worker_status()
    return jsonify({
        'total': len(worker_status),
        'workers': worker_status
    })


@app.route('/api/cluster/stats')
def get_cluster_stats():
    """获取集群统计信息"""
    worker_status = task_manager.get_worker_status()
    tasks = task_manager.get_all_tasks()
    
    # 统计任务状态
    task_stats = {}
    for task in tasks:
        status = task['status']
        task_stats[status] = task_stats.get(status, 0) + 1
    
    # 统计Worker状态
    online_workers = sum(1 for w in worker_status if w['online'])
    busy_workers = sum(1 for w in worker_status if w['status'] == 'busy')
    
    return jsonify({
        'total_workers': len(worker_status),
        'online_workers': online_workers,
        'busy_workers': busy_workers,
        'available_workers': online_workers - busy_workers,
        'total_tasks': len(tasks),
        'task_stats': task_stats,
        'gpu_models': list(set(w['gpu_model'] for w in GPU_WORKERS))
    })


if __name__ == '__main__':
    # Load challenges on startup
    load_challenges()
    
    # 初始化任务管理器和GPU监控器
    print("初始化任务管理系统...")
    task_manager = TaskManager(GPU_WORKERS)
    task_manager.start_dispatcher()
    
    print("初始化GPU监控系统...")
    gpu_monitor = GPUMonitor(simulation_mode=True)
    gpu_monitor.start_monitoring(interval=2.0)
    
    # Run the app
    print("\n" + "="*60)
    print("🚀 LeetGPU Online Testing Website - Master Node")
    print("="*60)
    print(f"📊 Loaded {len(challenges_data)} challenges")
    print(f"🖥️  Configured {len(GPU_WORKERS)} GPU Worker nodes")
    print(f"🌐 Server starting at http://{MASTER_HOST}:{MASTER_PORT}")
    print("="*60)
    print("\nGPU Workers:")
    for worker in GPU_WORKERS:
        print(f"  - {worker['name']}: {worker['gpu_model']} @ {worker['host']}:{worker['port']}")
    print("="*60 + "\n")
    
    try:
        app.run(debug=True, host=MASTER_HOST, port=MASTER_PORT)
    finally:
        # 清理资源
        print("\n关闭服务...")
        task_manager.stop_dispatcher()
        gpu_monitor.stop_monitoring()
        print("服务已停止")
