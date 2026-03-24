#!/usr/bin/env python3
"""
将 BVH 文件绕 X 轴旋转 270 度

修改所有帧数据中的 Xrotation 通道（在每个关节的 6 通道中是索引 4）
"""

import os
import re
from pathlib import Path


def process_bvh_file(bvh_path: Path):
    """处理单个 BVH 文件"""
    with open(bvh_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    # 分离 HIERARCHY 和 MOTION 部分
    motion_start = 0
    for i, line in enumerate(lines):
        if 'MOTION' in line:
            motion_start = i
            break

    hierarchy_lines = lines[:motion_start + 1]
    motion_lines = lines[motion_start + 1:]

    # 找到帧数据开始位置
    frame_data_start = 0
    num_frames = 0

    for i, line in enumerate(motion_lines):
        if line.strip() and not line.startswith('Frames') and not line.startswith('Frame'):
            frame_data_start = i
            break
        if 'Frames:' in line:
            num_frames = int(line.split(':')[1].strip())

    # 修改帧数据
    modified_motion = motion_lines[:frame_data_start]
    frame_data = motion_lines[frame_data_start:]

    for line in frame_data:
        if line.strip():
            values = line.strip().split()
            # 只修改 ROOT 关节的 Xrotation
            # ROOT 有 6 个通道：Xpos Ypos Zpos Zrot Xrot Yrot
            # Xrotation 是索引 4
            try:
                original = float(values[4])
                # 加 270 度
                values[4] = str(original + 270.0)
            except (ValueError, IndexError):
                pass

            modified_motion.append(' '.join(values))
        else:
            modified_motion.append(line)

    # 写回文件
    new_content = '\n'.join(hierarchy_lines + modified_motion)

    with open(bvh_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return num_frames


def process_directory(split_dir: Path):
    """处理目录下所有 BVH 文件"""
    bvh_files = list(split_dir.rglob('*.bvh'))

    print(f"找到 {len(bvh_files)} 个 BVH 文件")
    print("=" * 60)

    total_frames = 0

    for i, bvh_file in enumerate(bvh_files, 1):
        try:
            frames = process_bvh_file(bvh_file)
            total_frames += frames
            print(f"[{i}/{len(bvh_files)}] {bvh_file.name} ({frames} 帧)")
        except Exception as e:
            print(f"[{i}/{len(bvh_files)}] 错误: {bvh_file.name} - {e}")

    print("=" * 60)
    print(f"完成! 处理了 {len(bvh_files)} 个文件，共 {total_frames} 帧")


if __name__ == "__main__":
    split_dir = Path(r"e:\HKUSTGZ\HoloSoul\my_animated_drawing\examples\bvh\change\split")

    if not split_dir.exists():
        print(f"目录不存在: {split_dir}")
    else:
        process_directory(split_dir)
