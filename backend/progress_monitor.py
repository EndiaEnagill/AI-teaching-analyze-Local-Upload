import os
import time
import threading
import functools
import subprocess
import json
import ffmpeg
from datetime import datetime, timedelta

class JSONProgressMonitor:
    """进度监控器，进度以json格式日志进行保存"""

    def __init__(self, log_file_path, total_steps, step_time_estimates, step_names, audio_duration, dynamic_steps=None):
        self.log_file_path = log_file_path  # 日志保存的地址，通常和分析结果保存在一起
        self.total_steps = total_steps  # 总处理步骤数
        self.step_time_estimates = step_time_estimates  # 每个步骤的处理时间比
        self.step_names = step_names  # 每个步骤的名称/代号
        self.audio_duration = audio_duration  # 要处理的视频长度
        self.dynamic_steps = dynamic_steps or {}  # 动态步骤配置
        self.current_step = 0  # 当前完成步骤数量
        self.start_time = None  # 分析开始的现实时间
        self.step_start_time = None
        self.is_running = False  # 分析函数运行状态
        self.monitor_thread = None
        self.completed_steps_time = 0  # ？
        
        # 日志数据结构
        self.log_data = {
            "metadata": {
                "project": "音频内容分析",    #这里可以考虑传入课程名称
                "created_time": datetime.now().isoformat(),
                "total_steps": total_steps,
                "audio_duration_seconds": audio_duration,  # 记录视频总时长
                "audio_duration_formatted": self._format_time(audio_duration) if audio_duration > 0 else "未知",
                "dynamic_steps": dynamic_steps  # 记录哪些步骤是动态的
            },
            "progress_entries": []  # 用来记录日志
        }

        self._init_log_file()

    def _init_log_file(self):
        """初始化json日志文件"""

        # 记录日志地址，若地址不存在则新建
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 写入初始数据结构
        self._write_log_file()

    def _write_log_file(self):
        """将日志数据写入文件"""
        with open(self.log_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.log_data, f, ensure_ascii=False, indent = 2)

    def _add_progress_entry(self, entry_type = "progress"):
        """添加进度条目到日志数据"""
        current_timestamp = datetime.now().isoformat()
        elapsed_time = time.time() - self.start_time if self.start_time else 0

        progress_percentage = (self.current_step / self.total_steps) * 100  # 按百分比计算的整体进度
        estimated_remaining = self._calculate_estimated_time()  #计算预估剩余时间

        entry = {
            "timestamp": current_timestamp,
            "timestamp_readable": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "type": entry_type,
            "step_current": self.current_step,
            "step_total": self.total_steps,
            "progress_percentage": round(progress_percentage, 1),
            "step_name": self.step_names.get(self.current_step, "进行中"),
            "estimated_remaining": estimated_remaining,
            "elapsed_seconds": round(elapsed_time, 2),
            "elapsed_formatted": str(timedelta(seconds=int(elapsed_time)))
        }

        self.log_data["progress_entries"].append(entry)  #将新记录添加到日志中
        self._write_log_file()

        # 同时在控制台输出（测试用，可删除）
        print(f"[{entry['timestamp_readable']}] 步骤 {self.current_step}/{self.total_steps} ({progress_percentage:.1f}%) - {entry['step_name']} | 预估剩余: {estimated_remaining['formatted']}")

    def _calculate_estimated_time(self):
        """基于预设的处理时间比计算剩余时间"""
        if self.current_step == 0:
            total_estimated = sum(self.step_time_estimates.values())
            return {
                "seconds": total_estimated,
                "formatted": self._format_time(total_estimated)
            }
        
        remaining_seconds = 0
        for step in range(self.current_step + 1, self.total_steps + 1):
            if step in self.step_time_estimates:
                remaining_seconds += self.step_time_estimates[step]

        # 结合实际耗时进行动态调整
        if self.current_step > 0:
            elapsed_time = time.time() - self.start_time
            completed_estimated = 0
            for step in self.step_time_estimates:
                completed_estimated += self.step_time_estimates[step]

            if completed_estimated > 0:
                adjustment_factor = elapsed_time / completed_estimated
                remaining_seconds *= adjustment_factor

        return {
            "seconds": round(remaining_seconds, 2),
            "formatted": self._format_time(remaining_seconds)
        }
    
    def _format_time(self, seconds):
        """格式化时间展示"""
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            return f"{int(seconds/60)}分钟"
        else:
            hours = int(seconds/3600)
            minutes = int((seconds % 3600)/60)
            return f"{hours}小时{minutes}分钟"
        
    def _monitor_loop(self):
        """设定监控循环，定期更新日志"""
        while self.is_running:

        # ----------------- 时间间隔设置 -------------------------------------
            time.sleep(60) # 以秒为单位设置
        # ----------------- 时间间隔设置 -------------------------------------
            if self.is_running:
                self._add_progress_entry(entry_type="auto_update")

    def start(self):
        """开始监控"""
        self.start_time = time.time()
        self.step_start_time = self.start_time
        self.is_running = True
        self.current_step = 0

        # 记录开始条目
        self._add_progress_entry(entry_type="start")

        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def update_step(self, step_number, step_name=None):
        """更新当前步骤"""
        self.current_step = step_number
        if step_name and step_number in self.step_names:
            self.step_names[step_number] = step_name

    def skip_step(self, step_number, reason="跳过步骤"):
        """跳过指定步骤（适用于教案分析时未上传教案的情况）"""
        if step_number in self.step_time_estimates:
            # 将跳过步骤的时间设为0
            self.step_time_estimates[step_number] = 0
            # 更新步骤名称为跳过状态
            if step_number in self.step_names:
                self.step_names[step_number] = f"{self.step_names[step_number]} ({reason})"
        
        # 添加跳过记录
        skip_entry = {
            "timestamp": datetime.now().isoformat(),
            "timestamp_readable": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "type": "skip",
            "step_skipped": step_number,
            "reason": reason
        }
        
        if "skip_entries" not in self.log_data:
            self.log_data["skip_entries"] = []
        self.log_data["skip_entries"].append(skip_entry)
        self._write_log_file()
        
        print(f"步骤 {step_number} 已跳过: {reason}")

    def stop(self, success=True, error_message=None):
        """停止监控"""
        self.is_running = False
        self.current_step = self.total_steps if success else 0
        
        # 添加完成条目
        completion_entry = {
            "timestamp": datetime.now().isoformat(),
            "timestamp_readable": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "type": "completion",
            "status": "success" if success else "error",
            "error_message": error_message,
            "total_elapsed_seconds": round(time.time() - self.start_time, 2),
            "total_elapsed_formatted": str(timedelta(seconds=int(time.time() - self.start_time)))
        }
        
        self.log_data["completion"] = completion_entry
        self._write_log_file()
        
        status_msg = "成功" if success else f"失败: {error_message}"
        print(f"处理完成! 状态: {status_msg}, 总用时: {completion_entry['total_elapsed_formatted']}")

def get_audio_duration(video_path):
    """获取视频文件时长（秒）"""
    try:
        probe = ffmpeg.probe(video_path)
        stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        duration = float(stream['duration'])
        return duration
    except Exception as e:
        print(f"无法获取视频时长，使用默认比例: {e}")
        return 0
    
def calculate_dynamic_step_times(audio_duration, step_time_ratios=None, base_step_names=None, outline_path=None):
    """
    基于音频时长和outline_path动态计算各步骤预估时间
    
    Args:
        audio_duration: 音频时长（秒）
        step_time_ratios: 用户定义的时间比例
        base_step_names: 基础步骤名称
        outline_path: 教案文件路径，为None时跳过相关步骤
    
    Returns:
        total_steps, step_time_estimates, step_names, dynamic_steps
    """
    # 默认时间比例（基于音频时长的比例）
    default_ratios = {
        1: 0.1,   # 字幕转录
        2: 0.05,  # 视频图谱
        3: 0.02,  # 教案图谱
        4: 0.08,  # 新教案
        5: 0.05   # 报告生成
    }
    
    # 默认步骤名称
    default_names = {
        0: "开始处理",
        1: "字幕转录",
        2: "生成视频图谱", 
        3: "生成教案图谱",
        4: "生成新教案",
        5: "生成报告",
        6: "处理完成"
    }

    # 使用用户提供的参数或默认值
    time_ratios = step_time_ratios.copy() if step_time_ratios else default_ratios.copy()
    step_names = base_step_names.copy() if base_step_names else default_names.copy()

    # 动态步骤配置
    dynamic_steps = {}

    # 检测outline_path是否为None, 动态调整时间估计
    if outline_path is None:
        steps_to_skip = [4]

        for step in steps_to_skip:
            if step in time_ratios:
                time_ratios[step] = 0
                step_names[step] = {
                    "skipped": True,
                    "reason": "未上传教案相关文件",
                    "original_ratio": default_ratios.get(step, 0)
                }
                print(f"步骤 {step} ({step_names[step]}) 已跳过，因为未上传教案相关文件")

    # 计算各步骤预估时间（秒）
    step_time_estimates = {}
    for step, ratio in time_ratios.items():
        step_time_estimates[step] = audio_duration * ratio

    total_steps = len([step for step, ratio in time_ratios.items()])

    return total_steps, step_time_estimates, step_names, dynamic_steps

def create_dynamic_progress_monitor_decorator(log_file_path=None, step_time_ratios=None, base_step_names=None):
    """
    创建动态进度监控装饰器
    
    Args:
        log_file_path: 日志文件路径
        step_time_ratios: 步骤时间比例 {步骤号: 时间比例}
        base_step_names: 步骤名称 {步骤号: 步骤名称}
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取视频文件根路径和教案路径
            video_path = None
            outline_path = None
            
            # 从位置参数获取
            if args and len(args) > 0:
                video_path = args[0]
            if args and len(args) > 1:
                outline_path = args[1]
            
            # 从关键字参数获取
            if 'video_path' in kwargs:
                video_path = kwargs['video_path']
            if 'outline_path' in kwargs:
                outline_path = kwargs['outline_path']
            
            # 计算音频时长
            audio_duration = get_audio_duration(os.path.join(video_path, 'video.mp4')) if video_path else 0
            
            # 动态计算步骤时间
            total_steps, step_time_estimates, step_names, dynamic_steps = calculate_dynamic_step_times(
                audio_duration, step_time_ratios, base_step_names, outline_path
            )
            
            # 如果未指定日志文件路径，动态生成
            final_log_path = log_file_path
            if final_log_path is None and video_path:
                output_dir = video_path
                final_log_path = os.path.join(output_dir, f"progress.json")
            
            # 创建进度监控器
            monitor = JSONProgressMonitor(
                log_file_path=final_log_path,
                total_steps=total_steps,
                step_time_estimates=step_time_estimates,
                step_names=step_names,
                audio_duration=audio_duration,
                dynamic_steps=dynamic_steps
            )
            monitor.start()
            
            kwargs['progress_monitor'] = monitor
            
            try:
                result = func(*args, **kwargs)
                monitor.stop(success=True)
                return result
            except Exception as e:
                monitor.stop(success=False, error_message=str(e))
                raise e
        return wrapper
    return decorator

# 预定义的配置
DEFAULT_TIME_RATIOS = {
    1: 0.1,   # 字幕转录
    2: 0.05,  # 视频图谱
    3: 0.02,  # 教案图谱
    4: 0.08,  # 新教案
    5: 0.05   # 报告生成
}

DEFAULT_STEP_NAMES = {
    0: "开始处理",
    1: "字幕转录",
    2: "生成视频知识图谱", 
    3: "生成教案知识图谱",
    4: "生成新教案",
    5: "生成教学内容分析报告",
    6: "处理完成"
}

# 快速创建装饰器的便捷函数
def default_dynamic_progress_monitor(log_file_path=None):
    """使用默认配置创建动态进度监控装饰器"""
    return create_dynamic_progress_monitor_decorator(
        log_file_path=log_file_path,
        step_time_ratios=DEFAULT_TIME_RATIOS,
        base_step_names=DEFAULT_STEP_NAMES
    )

def custom_dynamic_progress_monitor(time_ratios, step_names, log_file_path=None):
    """使用自定义配置创建动态进度监控装饰器"""
    return create_dynamic_progress_monitor_decorator(
        log_file_path=log_file_path,
        step_time_ratios=time_ratios,
        base_step_names=step_names
    )