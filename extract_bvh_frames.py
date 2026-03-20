#!/usr/bin/env python3
"""
截取 BVH 文件的中间 N 帧
"""
import sys
import argparse

def extract_middle_frames(input_file, output_file, num_frames=2000):
    """
    从 BVH 文件中截取中间的 N 帧

    Args:
        input_file: 输入 BVH 文件路径
        output_file: 输出 BVH 文件路径
        num_frames: 要截取的帧数
    """
    with open(input_file, 'r') as f:
        lines = f.readlines()

    # 解析文件
    hierarchy_lines = []
    motion_section_found = False
    motion_lines = []
    frames_line_idx = -1
    frame_time_line_idx = -1
    total_frames = 0
    frame_time = 0.0

    for i, line in enumerate(lines):
        if not motion_section_found:
            hierarchy_lines.append(line)
            if 'MOTION' in line:
                motion_section_found = True
        else:
            motion_lines.append(line)
            if line.startswith('Frames:'):
                frames_line_idx = len(motion_lines) - 1
                total_frames = int(line.split(':')[1].strip())
            elif line.startswith('Frame Time:'):
                frame_time_line_idx = len(motion_lines) - 1
                frame_time = float(line.split(':')[1].strip())

    print(f"原始文件总帧数: {total_frames}")
    print(f"帧时间: {frame_time}")

    # 计算要截取的帧范围（中间 2000 帧）
    if total_frames <= num_frames:
        print(f"警告：总帧数 ({total_frames}) 小于请求的帧数 ({num_frames})，将使用所有帧")
        start_frame = 0
        end_frame = total_frames
    else:
        start_frame = (total_frames - num_frames) // 2
        end_frame = start_frame + num_frames

    print(f"截取帧范围: {start_frame} - {end_frame} (共 {end_frame - start_frame} 帧)")

    # 构建输出内容
    output_lines = []

    # 1. 写入 HIERARCHY 部分
    output_lines.extend(hierarchy_lines)

    # 2. 写入 MOTION 部分
    output_lines.append('MOTION\n')
    output_lines.append(f'Frames: {end_frame - start_frame}\n')
    output_lines.append(f'Frame Time: {frame_time}\n')

    # 3. 写入帧数据（只写入指定范围的帧）
    # 每一帧的数据从 frame_time_line_idx + 1 开始
    frame_data_start_idx = frame_time_line_idx + 1

    for frame_idx in range(start_frame, end_frame):
        frame_line_idx = frame_data_start_idx + frame_idx
        if frame_line_idx < len(motion_lines):
            output_lines.append(motion_lines[frame_line_idx])

    # 写入输出文件
    with open(output_file, 'w') as f:
        f.writelines(output_lines)

    print(f"成功写入: {output_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='截取 BVH 文件的中间 N 帧')
    parser.add_argument('input_file', help='输入 BVH 文件路径')
    parser.add_argument('output_file', help='输出 BVH 文件路径')
    parser.add_argument('-n', '--num_frames', type=int, default=2000,
                        help='要截取的帧数 (默认: 2000)')

    args = parser.parse_args()

    extract_middle_frames(args.input_file, args.output_file, args.num_frames)
