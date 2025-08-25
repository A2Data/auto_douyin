# -*- coding: utf-8 -*-

"""
工具模块
提供各种辅助功能
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Optional


def get_title_and_hashtags(filename: str) -> Tuple[str, List[str]]:
    """
    从视频文件获取标题和话题标签

    Args:
        filename: 视频文件路径

    Returns:
        Tuple[str, List[str]]: 标题和话题标签列表
    """
    # 获取视频标题和话题标签的txt文件名
    txt_filename = filename.replace(".mp4", ".txt")

    # 检查txt文件是否存在
    if not os.path.exists(txt_filename):
        # 如果不存在，使用视频文件名作为标题
        video_path = Path(filename)
        title = video_path.stem
        hashtags = []
        return title, hashtags

    try:
        # 读取txt文件
        with open(txt_filename, "r", encoding="utf-8") as f:
            content = f.read()

        # 解析内容
        lines = content.strip().split("\n")
        if len(lines) >= 2:
            title = lines[0].strip()
            hashtags_line = lines[1].strip()
            # 解析话题标签
            hashtags = [tag.strip() for tag in hashtags_line.replace("#", "").split(" ") if tag.strip()]
        elif len(lines) == 1:
            title = lines[0].strip()
            hashtags = []
        else:
            # 如果文件为空，使用视频文件名作为标题
            video_path = Path(filename)
            title = video_path.stem
            hashtags = []

        return title, hashtags

    except Exception as e:
        # 如果读取失败，使用视频文件名作为标题
        video_path = Path(filename)
        title = video_path.stem
        hashtags = []
        return title, hashtags


def generate_schedule_time_next_day(total_videos: int,
                                    videos_per_day: int = 1,
                                    daily_times: List[int] = None,
                                    start_days: int = 0) -> List[datetime]:
    """
    生成视频发布时间安排

    Args:
        total_videos: 总视频数量
        videos_per_day: 每天发布视频数量
        daily_times: 每天发布的时间点（小时）
        start_days: 从几天后开始发布

    Returns:
        List[datetime]: 发布时间列表
    """
    if videos_per_day <= 0:
        raise ValueError("每天发布视频数量必须大于0")

    if daily_times is None:
        # 默认发布时间点
        daily_times = [6, 11, 14, 16, 22]

    if videos_per_day > len(daily_times):
        raise ValueError("每天发布视频数量不能超过可用时间点数量")

    # 生成发布时间安排
    schedule = []
    current_time = datetime.now()

    for video_index in range(total_videos):
        # 计算是第几天和当天的第几个视频
        day_index = video_index // videos_per_day + start_days + 1  # +1表示从明天开始
        daily_video_index = video_index % videos_per_day

        # 计算具体的发布时间
        hour = daily_times[daily_video_index]
        publish_time = current_time.replace(
            hour=hour,
            minute=0,
            second=0,
            microsecond=0
        ) + timedelta(days=day_index)

        schedule.append(publish_time)

    return schedule


def validate_video_file(video_path: str) -> bool:
    """
    验证视频文件是否有效

    Args:
        video_path: 视频文件路径

    Returns:
        bool: 文件是否有效
    """
    if not os.path.exists(video_path):
        return False

    # 检查文件大小
    file_size = os.path.getsize(video_path)
    if file_size == 0:
        return False

    # 检查文件扩展名
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v']
    file_extension = Path(video_path).suffix.lower()

    return file_extension in video_extensions


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小

    Args:
        size_bytes: 字节数

    Returns:
        str: 格式化后的文件大小
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.2f} {size_names[i]}"


def get_video_info(video_path: str) -> dict:
    """
    获取视频文件信息

    Args:
        video_path: 视频文件路径

    Returns:
        dict: 视频信息
    """
    if not os.path.exists(video_path):
        return {"error": "文件不存在"}

    file_path = Path(video_path)
    file_size = os.path.getsize(video_path)

    # 获取文件时间
    created_time = datetime.fromtimestamp(os.path.getctime(video_path))
    modified_time = datetime.fromtimestamp(os.path.getmtime(video_path))

    # 尝试获取标题和标签
    try:
        title, tags = get_title_and_hashtags(video_path)
    except:
        title, tags = file_path.stem, []

    return {
        "filename": file_path.name,
        "path": str(file_path.absolute()),
        "size": file_size,
        "size_formatted": format_file_size(file_size),
        "extension": file_path.suffix,
        "created_time": created_time.strftime("%Y-%m-%d %H:%M:%S"),
        "modified_time": modified_time.strftime("%Y-%m-%d %H:%M:%S"),
        "title": title,
        "tags": tags,
        "is_valid": validate_video_file(video_path)
    }


def create_video_txt_file(video_path: str, title: str, tags: List[str]) -> str:
    """
    为视频文件创建对应的txt文件

    Args:
        video_path: 视频文件路径
        title: 视频标题
        tags: 话题标签列表

    Returns:
        str: txt文件路径
    """
    txt_path = video_path.replace(".mp4", ".txt")

    # 格式化标签
    tags_str = " ".join([f"#{tag}" for tag in tags])

    # 写入文件
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"{title}\n")
        f.write(f"{tags_str}\n")

    return txt_path


def scan_video_directory(directory: str) -> List[dict]:
    """
    扫描目录中的视频文件

    Args:
        directory: 目录路径

    Returns:
        List[dict]: 视频文件信息列表
    """
    if not os.path.exists(directory):
        return []

    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v']
    video_files = []

    for file_path in Path(directory).glob("*"):
        if file_path.is_file() and file_path.suffix.lower() in video_extensions:
            video_info = get_video_info(str(file_path))
            video_files.append(video_info)

    # 按修改时间排序
    video_files.sort(key=lambda x: x['modified_time'], reverse=True)

    return video_files


def clean_filename(filename: str) -> str:
    """
    清理文件名中的非法字符

    Args:
        filename: 原始文件名

    Returns:
        str: 清理后的文件名
    """
    # 定义非法字符
    illegal_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']

    # 替换非法字符
    clean_name = filename
    for char in illegal_chars:
        clean_name = clean_name.replace(char, '_')

    return clean_name


def ensure_directory_exists(directory: str) -> bool:
    """
    确保目录存在

    Args:
        directory: 目录路径

    Returns:
        bool: 目录是否存在或创建成功
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception:
        return False


def get_thumbnail_path(video_path: str) -> Optional[str]:
    """
    获取视频对应的缩略图路径

    Args:
        video_path: 视频文件路径

    Returns:
        Optional[str]: 缩略图路径，如果不存在则返回None
    """
    video_file = Path(video_path)
    thumbnail_extensions = ['.png', '.jpg', '.jpeg']

    for ext in thumbnail_extensions:
        thumbnail_path = video_file.with_suffix(ext)
        if thumbnail_path.exists():
            return str(thumbnail_path)

    return None


def validate_schedule_time(schedule_time: str) -> Optional[datetime]:
    """
    验证并解析定时发布时间

    Args:
        schedule_time: 时间字符串 (格式: YYYY-MM-DD HH:MM)

    Returns:
        Optional[datetime]: 解析后的时间对象，如果格式错误则返回None
    """
    try:
        return datetime.strptime(schedule_time, "%Y-%m-%d %H:%M")
    except ValueError:
        return None


if __name__ == "__main__":
    # 测试工具函数
    print("测试工具函数...")

    # 测试时间生成
    schedule_times = generate_schedule_time_next_day(5, 2, [9, 15, 21])
    print("生成的发布时间:")
    for i, time in enumerate(schedule_times):
        print(f"  视频{i + 1}: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 测试文件大小格式化
    print(f"\n文件大小格式化:")
    print(f"  1024 bytes = {format_file_size(1024)}")
    print(f"  1048576 bytes = {format_file_size(1048576)}")
    print(f"  1073741824 bytes = {format_file_size(1073741824)}")

    # 测试文件名清理
    print(f"\n文件名清理:")
    dirty_filename = "测试视频<>:\"*?.mp4"
    clean_name = clean_filename(dirty_filename)
    print(f"  原文件名: {dirty_filename}")
    print(f"  清理后: {clean_name}")

    print("\n工具函数测试完成")