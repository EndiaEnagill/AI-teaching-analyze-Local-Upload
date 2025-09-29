import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import threading
from datetime import datetime
from werkzeug.utils import secure_filename

# 导入分析函数和工具函数
from analyze import analyze_content
from utils import (
    allowed_file, generate_task_id, create_task_folder, save_basic_info, 
    read_basic_info, get_task_status, get_task_progress, scan_existing_tasks,
    get_all_tasks_from_fs, ALLOWED_VIDEO_EXTENSIONS, ALLOWED_OUTLINE_EXTENSIONS
)

# 禁用Flask和Werkzeug的访问日志
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
CORS(app)

def log_important(message):
    """只记录重要的系统信息"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}")

# 配置项目关键路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
DATA_DIR = os.path.join(BASE_DIR, 'data')
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

log_important(f"项目根目录: {BASE_DIR}")
log_important(f"数据目录: {DATA_DIR}")
log_important(f"前端目录: {FRONTEND_DIR}")

print(f"项目根目录: {BASE_DIR}")
print(f"数据存储目录: {DATA_DIR}")

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FRONTEND_DIR, exist_ok=True)

# 全局任务存储
active_tasks = {}
task_lock = threading.Lock()

def run_analysis(task_id, folder_path, outline_path):
    """运行分析任务的线程函数"""
    try:
        with task_lock:
            if task_id in active_tasks:
                active_tasks[task_id]['status'] = "分析中"
        
        print(f"🚀 开始分析任务 {task_id}")
        
        # 调用分析函数
        result = analyze_content(
            video_path=folder_path,
            outline_path=outline_path,
            output_dir=folder_path
        )
        
        print(f"✅ 分析任务完成 {task_id}")
        
    except Exception as e:
        print(f"❌ 分析任务失败 {task_id}: {e}")
        with task_lock:
            if task_id in active_tasks:
                active_tasks[task_id]['status'] = "分析失败"

# 静态文件服务
@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """服务静态文件"""
    # 检查文件是否存在
    file_path = os.path.join(FRONTEND_DIR, path)
    
    # 如果是根路径，返回index.html
    if path == '':
        return send_from_directory(FRONTEND_DIR, 'index.html')
    
    # 如果请求的是具体文件且存在，直接返回
    if os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    
    # 如果请求的是目录，检查是否有index.html
    if os.path.isdir(file_path):
        index_path = os.path.join(file_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(FRONTEND_DIR, os.path.join(path, 'index.html'))
    
    # 对于前端路由，返回index.html（支持Vue/React路由）
    if not path.startswith('api/') and not path.startswith('data/'):
        return send_from_directory(FRONTEND_DIR, 'index.html')
    
    # 数据文件
    if path.startswith('data/'):
        return send_from_directory(DATA_DIR, path[5:])
    
    return "页面不存在", 404

# 显式定义关键静态文件路由
@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'css'), filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'js'), filename)

@app.route('/upload.html')
def serve_upload():
    return send_from_directory(FRONTEND_DIR, 'upload.html')

# API 路由
@app.route('/api/upload', methods=['POST'])
def upload_video():
    """上传视频和教案"""
    try:
        # 获取表单数据
        course_name = request.form.get('course_name', '').strip()
        teacher = request.form.get('teacher', '').strip()
        student_type = request.form.get('student_type', '').strip()
        
        # 验证必填字段
        if not course_name or not teacher or not student_type:
            return jsonify({
                "success": False,
                "message": "请填写所有必填字段"
            }), 400
        
        # 获取文件
        video_file = request.files.get('video_file')
        outline_file = request.files.get('outline_file')
        
        if not video_file or video_file.filename == '':
            return jsonify({
                "success": False,
                "message": "请上传视频文件"
            }), 400
        
        # 验证视频文件格式
        if not allowed_file(video_file.filename, ALLOWED_VIDEO_EXTENSIONS):
            return jsonify({
                "success": False,
                "message": f"不支持的视频格式。支持格式: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
            }), 400
        
        # 验证教案文件格式（如果提供了的话）
        if outline_file and outline_file.filename != '':
            if not allowed_file(outline_file.filename, ALLOWED_OUTLINE_EXTENSIONS):
                return jsonify({
                    "success": False,
                    "message": f"不支持的教案格式。支持格式: {', '.join(ALLOWED_OUTLINE_EXTENSIONS)}"
                }), 400
        
        # 生成任务ID
        task_id = generate_task_id()
        
        # 创建存储文件夹
        folder_path, folder_name = create_task_folder(DATA_DIR, task_id, course_name)
        
        # 保存视频文件
        video_save_path = os.path.join(folder_path, "video.mp4")
        video_file.save(video_save_path)
        
        # 保存教案文件（如果有）
        outline_save_path = None
        if outline_file and outline_file.filename:
            original_ext = os.path.splitext(outline_file.filename)[1]
            outline_filename = f"outline{original_ext}"
            outline_save_path = os.path.join(folder_path, outline_filename)
            outline_file.save(outline_save_path)
        
        # 创建任务信息
        task_info = {
            "task_id": task_id,
            "course_name": course_name,
            "teacher": teacher,
            "student_type": student_type,
            "folder_name": folder_name,
            "upload_time": datetime.now().isoformat(),
            "upload_time_readable": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "video_file": "video.mp4",
            "outline_file": os.path.basename(outline_save_path) if outline_save_path else None
        }
        
        # 保存基本信息
        save_basic_info(folder_path, task_info)
        
        # 记录到活跃任务
        with task_lock:
            active_tasks[task_id] = {
                "task_id": task_id,
                "folder_path": folder_path,
                "status": "等待开始",
                "progress": get_task_progress(folder_path),
                "created_time": datetime.now().isoformat()
            }
        
        # 启动分析任务
        analysis_thread = threading.Thread(
            target=run_analysis,
            args=(task_id, folder_path, outline_save_path),
            daemon=True
        )
        analysis_thread.start()
        
        return jsonify({
            "success": True,
            "message": "上传成功，开始分析",
            "task_id": task_id,
            "data": {
                "task_id": task_id,
                "course_name": course_name,
                "teacher": teacher,
                "student_type": student_type
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"上传失败: {str(e)}"
        }), 500

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取所有任务列表（包括已完成的任务）"""
    try:
        # 直接从文件系统获取所有任务
        all_tasks = get_all_tasks_from_fs(DATA_DIR)
        
        # 更新活跃任务的状态（确保实时性）
        with task_lock:
            for task in all_tasks:
                task_id = task['task_id']
                if task_id in active_tasks:
                    # 更新活跃任务的最新状态
                    active_tasks[task_id]['status'] = task['status']
                    active_tasks[task_id]['progress'] = task['progress']
        
        return jsonify({
            "success": True,
            "data": all_tasks
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取任务列表失败: {str(e)}"
        }), 500

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取特定任务详情"""
    try:
        # 直接从文件系统获取任务信息
        all_tasks = get_all_tasks_from_fs(DATA_DIR)
        task_data = next((task for task in all_tasks if task['task_id'] == task_id), None)
        
        if task_data:
            # 查找文件夹路径
            folder_pattern = f"{task_id}_*"
            folder_path = None
            for folder_name in os.listdir(DATA_DIR):
                if folder_name.startswith(f"{task_id}_"):
                    folder_path = os.path.join(DATA_DIR, folder_name)
                    break
            
            return jsonify({
                "success": True,
                "data": {
                    "task_id": task_id,
                    "course_name": task_data['course_name'],
                    "teacher": task_data['teacher'],
                    "student_type": task_data['student_type'],
                    "upload_time": task_data['upload_time'],
                    "status": task_data['status'],
                    "progress": task_data['progress'],
                    "folder_path": folder_path
                }
            })
        
        return jsonify({
            "success": False,
            "message": "任务不存在"
        }), 404
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取任务详情失败: {str(e)}"
        }), 500

@app.route('/api/tasks/<task_id>/progress', methods=['GET'])
def get_task_progress_api(task_id):
    """获取任务进度"""
    try:
        # 直接从文件系统获取最新进度
        all_tasks = get_all_tasks_from_fs(DATA_DIR)
        task_data = next((task for task in all_tasks if task['task_id'] == task_id), None)
        
        if task_data:
            return jsonify({
                "success": True,
                "data": {
                    "status": task_data['status'],
                    "progress": task_data['progress']
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": "任务不存在"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"获取任务进度失败: {str(e)}"
        }), 500

# 健康检查
@app.route('/api/health', methods=['GET'])
def health_check():
    all_tasks = get_all_tasks_from_fs(DATA_DIR)
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "total_tasks": len(all_tasks),
        "active_tasks": len(active_tasks)
    })

if __name__ == '__main__':
    # 扫描并显示所有现有任务
    print("🚀 启动视频分析平台...")
    
    # 扫描现有任务
    with task_lock:
        existing_tasks = scan_existing_tasks(DATA_DIR)
        active_tasks.update(existing_tasks)
    
    # 显示统计信息
    all_tasks = get_all_tasks_from_fs(DATA_DIR)
    status_count = {}
    for task in all_tasks:
        status = task['status']
        status_count[status] = status_count.get(status, 0) + 1
    
    print(f"    任务统计: {status_count}")
    print("✅ 服务已启动: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)