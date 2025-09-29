import argparse
from openai import OpenAI
import os
import json
import subprocess
import re
from tools.generate_doc_tree import *
from tools.video_transformer import *
from tools.generate_video_tree import *
from tools.generate_report import *
from tools.new_outline import *
from tools.generate_coverage import *

from progress_monitor import (
    default_dynamic_progress_monitor,
    custom_dynamic_progress_monitor,
    DEFAULT_TIME_RATIOS,
    DEFAULT_STEP_NAMES
)

# 自定义处理步骤和时间比以替代默认配置

CUSTOM_TIME_RATIOS = {
    1: 0.05,  # 视频转音频
    2: 0.1,   # 字幕转录
    3: 0.3,   # 视频图谱
    4: 0.3,   # 教案图谱
    5: 0.5,   # 新教案
    6: 0.6    # 报告生成
}

CUSTOM_STEP_NAMES = {
    0: "开始处理",
    1: "视频转音频",
    2: "字幕转录",
    3: "生成视频知识图谱", 
    4: "生成教案知识图谱",
    5: "生成新教案",
    6: "生成教学内容分析报告",
    7: "处理完成"
}

@custom_dynamic_progress_monitor(
    time_ratios=CUSTOM_TIME_RATIOS,
    step_names=CUSTOM_STEP_NAMES
)
def analyze_content(video_path, outline_path, progress_monitor=None, output_dir=None):
    """
    video_path: 视频存储的根目录
    """
    if output_dir is None:
        # output_dir = os.path.dirname(video_path)
        output_dir = video_path

    try:
        print(f'------{video_path}')
        # 1. 视频转音频
        progress_monitor.update_step(1, "视频转音频")
        generate_audio(video_path)
        print('视频转音频成功')

        # 2. 转录字幕
        progress_monitor.update_step(2, "字幕转录")
        audio_path = os.path.join(video_path, 'audio.mp3')
        subtitles = generate_subtitles(audio_path)

        print('字幕转录成功...')

        # 3. 生成视频图谱
        progress_monitor.update_step(3, "生成视频知识图谱")
        video_tree = generate_video_tree(subtitles)
        print('视频图谱生成成功...')

        # 4. 生成教案图谱（动态步骤）
        if outline_path is not None:
            progress_monitor.update_step(4, "生成教案知识图谱")
            outline_tree = generate_document_tree(outline_path)
            print('教案图谱生成成功...')
        else:
            # 跳过教案图谱生成
            progress_monitor.skip_step(4, "未上传教案相关文件")
            outline_tree = None
            print('跳过教案图谱生成（未上传教案相关文件）')

        # 5. 生成新教案
        progress_monitor.update_step(5, "生成新教案")
        new_outline = generate_outline(subtitles, video_tree)
        print('新教案生成成功...')

        # 6. 生成报告
        progress_monitor.update_step(6, "生成教学内容分析报告")
        report = generate_report(subtitles, video_tree, outline_tree)
        print('教学内容分析报告生成成功...')

        # 7. 完成
        progress_monitor.update_step(7, "处理完成")

        print(f"视频处理完成")
        result = {
            'subtitles': subtitles,
            'video_tree': video_tree,
            'outline_tree': outline_tree,
            'analysis': report,
            'new_outline': new_outline
        }

        # 保存结果到文件
        result_file = os.path.join(output_dir, f"result.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"结果已保存至: {result_file}")
        print(f"进度日志已保存至: {progress_monitor.log_file_path}")

        return result
    
    except Exception as e:
        progress_monitor.update_step(0, f"处理失败: {str(e)}")
        raise e

# # 测试用
# file_name = "D:/实验室/服务器3.0/data/test_data"

# outline_data = None
# result = analyze_content(file_name, outline_data)