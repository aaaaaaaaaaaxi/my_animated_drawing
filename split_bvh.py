#!/usr/bin/env python3
"""
将 BVH 文件平均分成两个部分
"""
import sys
import argparse

def split_bvh(input_file, output_file1, output_file2):
    """
    将 BVH 文件平均分成两个部分

    Args:
        input_file: 输入 BVH 文件路径
        output_file1: 第一个输出文件路径
        output_file2: 第二个输出文件路径
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

    # 计算分割点
    mid_frame = (total_frames + 1) // 2
    print(f"分割点: 第 {mid_frame} 帧")

    # 帧数据起始位置
    frame_data_start_idx = frame_time_line_idx + 1

    # 写入第一个文件（前半部分）
    print(f"\n写入第一个文件: {output_file1}")
    output_lines1 = []
    output_lines1.extend(hierarchy_lines)
    output_lines1.append(f'Frames: {mid_frame}\n')
    output_lines1.append(f'Frame Time: {frame_time}\n')

    for frame_idx in range(0, mid_frame):
        frame_line_idx = frame_data_start_idx + frame_idx
        if frame_line_idx < len(motion_lines):
            output_lines1.append(motion_lines[frame_line_idx])

    with open(output_file1, 'w') as f:
        f.writelines(output_lines1)
    print(f"第一个文件帧数: {mid_frame}")

    # 写入第二个文件（后半部分）
    print(f"\n写入第二个文件: {output_file2}")
    output_lines2 = []
    output_lines2.extend(hierarchy_lines)
    output_lines2.append(f'Frames: {total_frames - mid_frame}\n')
    output_lines2.append(f'Frame Time: {frame_time}\n')

    for frame_idx in range(mid_frame, total_frames):
        frame_line_idx = frame_data_start_idx + frame_idx
        if frame_line_idx < len(motion_lines):
            output_lines2.append(motion_lines[frame_line_idx])

    with open(output_file2, 'w') as f:
        f.writelines(output_lines2)
    print(f"第二个文件帧数: {total_frames - mid_frame}")

    print(f"\n完成！文件已分割为两部分")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='将 BVH 文件平均分成两个部分')
    parser.add_argument('input_file', help='输入 BVH 文件路径')
    parser.add_argument('output_file1', help='第一个输出文件路径（前半部分）')
    parser.add_argument('output_file2', help='第二个输出文件路径（后半部分）')

    args = parser.parse_args()

    split_bvh(args.input_file, args.output_file1, args.output_file2)
