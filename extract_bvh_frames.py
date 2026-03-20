#!/usr/bin/env python3
"""
截取 BVH 文件的中间 N 帧，并支持抽帧
"""
import sys
import argparse

def extract_middle_frames(input_file, output_file, num_frames=2000, skip=1):
    """
    从 BVH 文件中截取中间的 N 帧，并支持抽帧

    Args:
        input_file: 输入 BVH 文件路径
        output_file: 输出 BVH 文件路径
        num_frames: 要截取的帧数
        skip: 抽帧间隔（1=不跳过，2=每隔1帧取1帧即30fps，3=每隔2帧取1帧即20fps）
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
    print(f"原始帧时间: {frame_time}")
    print(f"原始FPS: {1.0/frame_time:.2f}")
    print(f"抽帧间隔: {skip} (1=不跳过，2=每隔1帧取1帧)")

    # 计算要截取的帧范围（中间 N 帧，抽帧后）
    # 需要读取的总帧数要乘以 skip
    if total_frames <= num_frames * skip:
        print(f"警告：总帧数 ({total_frames}) 不足，将使用所有帧")
        start_frame = 0
        end_frame = total_frames
    else:
        start_frame = (total_frames - num_frames * skip) // 2
        end_frame = start_frame + num_frames * skip

    # 计算抽帧后的实际帧数
    actual_num_frames = (end_frame - start_frame) // skip
    if (end_frame - start_frame) % skip != 0:
        actual_num_frames += 1

    print(f"读取帧范围: {start_frame} - {end_frame} (共 {end_frame - start_frame} 帧)")
    print(f"抽帧后帧数: {actual_num_frames}")
    print(f"新帧时间: {frame_time * skip}")
    print(f"新FPS: {1.0/(frame_time * skip):.2f}")

    # 构建输出内容
    output_lines = []

    # 1. 写入 HIERARCHY 部分（包括 MOTION 行）
    output_lines.extend(hierarchy_lines)

    # 2. 写入帧数和帧时间（帧时间需要乘以 skip）
    output_lines.append(f'Frames: {actual_num_frames}\n')
    output_lines.append(f'Frame Time: {frame_time * skip}\n')

    # 3. 写入帧数据（只写入指定范围的帧，并按 skip 间隔抽取）
    frame_data_start_idx = frame_time_line_idx + 1

    frame_count = 0
    for frame_idx in range(start_frame, end_frame, skip):
        frame_line_idx = frame_data_start_idx + frame_idx
        if frame_line_idx < len(motion_lines):
            output_lines.append(motion_lines[frame_line_idx])
            frame_count += 1

    print(f"实际写入帧数: {frame_count}")

    # 写入输出文件
    with open(output_file, 'w') as f:
        f.writelines(output_lines)

    print(f"成功写入: {output_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='截取 BVH 文件的中间 N 帧，并支持抽帧')
    parser.add_argument('input_file', help='输入 BVH 文件路径')
    parser.add_argument('output_file', help='输出 BVH 文件路径')
    parser.add_argument('-n', '--num_frames', type=int, default=2000,
                        help='要截取的帧数 (默认: 2000)')
    parser.add_argument('-s', '--skip', type=int, default=2,
                        help='抽帧间隔 (默认: 2，即从60fps变为30fps)')

    args = parser.parse_args()

    extract_middle_frames(args.input_file, args.output_file, args.num_frames, args.skip)
