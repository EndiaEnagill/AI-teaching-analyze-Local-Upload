import os
import json
import random
import string
import re
from datetime import datetime

# 支持的文件格式
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'}
ALLOWED_OUTLINE_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'ppt', 'pptx'}

def allowed_file(filename, allowed_extensions):
    """检查文件格式"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def generate_task_id():
    """生成6位数字任务ID"""
    return ''.join(random.choices(string.digits, k=6))

def create_task_folder(data_dir, task_id, course_name):
    """创建任务文件夹"""
    # 清理课程名称中的非法字符
    safe_course_name = "".join(c for c in course_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_course_name = safe_course_name.replace(' ', '_')
    
    folder_name = f"{task_id}_{safe_course_name}"
    folder_path = os.path.join(data_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path, folder_name

def save_basic_info(folder_path, task_info):
    """保存基本信息到JSON文件"""
    info_file = os.path.join(folder_path, "basic_info.json")
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(task_info, f, ensure_ascii=False, indent=2)
    return info_file

def read_basic_info(folder_path):
    """读取基本信息"""
    info_file = os.path.join(folder_path, "basic_info.json")
    if os.path.exists(info_file):
        with open(info_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def read_progress_log(folder_path):
    """读取进度日志"""
    log_file = os.path.join(folder_path, "progress.json")
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def get_task_status(folder_path):
    """获取任务状态"""
    progress_data = read_progress_log(folder_path)
    basic_info = read_basic_info(folder_path)
    
    if not basic_info:
        return "未知"
    
    if not progress_data:
        return "等待开始"
    
    if 'completion' in progress_data:
        if progress_data['completion']['status'] == 'success':
            return "分析完成"
        else:
            return "分析失败"
    
    if 'progress_entries' in progress_data and progress_data['progress_entries']:
        return "分析中"
    
    return "等待开始"

def get_task_progress(folder_path):
    """获取任务进度信息"""
    progress_data = read_progress_log(folder_path)
    
    if not progress_data or 'progress_entries' not in progress_data:
        return {
            "current_step": 0,
            "total_steps": 0,
            "progress_percentage": 0,
            "estimated_remaining": "未知",
            "current_step_name": "等待开始"
        }
    
    entries = progress_data['progress_entries']
    if not entries:
        return {
            "current_step": 0,
            "total_steps": 0,
            "progress_percentage": 0,
            "estimated_remaining": "未知",
            "current_step_name": "等待开始"
        }
    
    latest_entry = entries[-1]
    
    return {
        "current_step": latest_entry.get('step_current', 0),
        "total_steps": latest_entry.get('step_total', 0),
        "progress_percentage": latest_entry.get('progress_percentage', 0),
        "estimated_remaining": latest_entry.get('estimated_remaining', {}).get('formatted', '未知'),
        "current_step_name": latest_entry.get('step_name', '进行中')
    }

def scan_existing_tasks(data_dir):
    """扫描现有任务（包括已完成的任务）"""
    tasks = {}
    if not os.path.exists(data_dir):
        return tasks
    
    print(f"    扫描数据目录: {data_dir}")
    found_count = 0
    
    for folder_name in os.listdir(data_dir):
        folder_path = os.path.join(data_dir, folder_name)
        if os.path.isdir(folder_path) and '_' in folder_name:
            task_id = folder_name.split('_')[0]
            if task_id.isdigit():
                basic_info = read_basic_info(folder_path)
                if basic_info:
                    status = get_task_status(folder_path)
                    progress = get_task_progress(folder_path)
                    
                    tasks[task_id] = {
                        "task_id": task_id,
                        "folder_path": folder_path,
                        "status": status,
                        "progress": progress,
                        "created_time": basic_info.get('upload_time', ''),
                        "analysis_started": False  # 标记为未开始分析（只显示）
                    }
                    
                    found_count += 1
                    # 显示系统当前存储的分析任务，当任务过多时，下行可注释，以减少输出
                    # print(f"  发现任务: {task_id} - {basic_info.get('course_name', '未知课程')} [{status}]")
    
    print(f"    扫描完成: 共找到 {found_count} 个任务（包括已完成的任务）")
    return tasks

def get_all_tasks_from_fs(data_dir):
    """直接从文件系统获取所有任务（用于API调用）"""
    tasks_list = []
    if not os.path.exists(data_dir):
        return tasks_list
    
    for folder_name in os.listdir(data_dir):
        folder_path = os.path.join(data_dir, folder_name)
        if os.path.isdir(folder_path) and '_' in folder_name:
            task_id = folder_name.split('_')[0]
            if task_id.isdigit():
                basic_info = read_basic_info(folder_path)
                if basic_info:
                    status = get_task_status(folder_path)
                    progress = get_task_progress(folder_path)
                    
                    task_data = {
                        "task_id": task_id,
                        "course_name": basic_info.get('course_name', '未知课程'),
                        "teacher": basic_info.get('teacher', '未知教师'),
                        "student_type": basic_info.get('student_type', '未知对象'),
                        "upload_time": basic_info.get('upload_time_readable', '未知时间'),
                        "status": status,
                        "progress": progress
                    }
                    tasks_list.append(task_data)
    
    # 按上传时间倒序排列
    tasks_list.sort(key=lambda x: x['upload_time'], reverse=True)
    return tasks_list