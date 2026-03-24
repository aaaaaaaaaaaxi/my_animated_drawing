#!/usr/bin/env python3
"""
使用 XYZ 欧拉角旋转方式对 BVH 文件进行 X 轴 270° 旋转

使用旋转矩阵确保与 Blender 中的效果一致
"""

import os
import numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation


def euler_to_matrix(z_deg, x_deg, y_deg):
    """将 BVH 的 Z-X-Y 欧拉角转换为旋转矩阵"""
    # 创建旋转对象，使用 'ZYX' 顺序（对应 BVH 的 Z-X-Y 通道）
    r = Rotation.from_euler('ZYX', [z_deg, x_deg, y_deg], degrees=True)
    return r.as_matrix()


def matrix_to_euler_zxy(matrix):
    """将旋转矩阵转换回 BVH 的 Z-X-Y 欧拉角"""
    r = Rotation.from_matrix(matrix)
    # 使用 'ZYX' 顺序获取欧拉角
    euler = r.as_euler('ZYX', degrees=True)
    return euler[0], euler[1], euler[2]  # z, x, y


def rotate_x_270_matrix(z_deg, x_deg, y_deg):
    """
    对给定的旋转应用 X 轴 270° 旋转

    这相当于：R_new = R_x(270°) @ R_original
    """
    # 获取原始旋转矩阵
    R_original = euler_to_matrix(z_deg, x_deg, y_deg)

    # 创建 X 轴 270° 旋转矩阵
    R_x_270 = Rotation.from_euler('X', [270], degrees=True).as_matrix()

    # 组合旋转：先应用原始旋转，再应用 X 轴旋转
    R_new = R_x_270 @ R_original

    # 转换回欧拉角
    return matrix_to_euler_zxy(R_new)


def process_bvh_file(bvh_path: Path):
    """处理单个 BVH 文件"""
    with open(bvh_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 分离 HIERARCHY 和 MOTION 部分
    hierarchy_lines = []
    motion_start_idx = 0

    for i, line in enumerate(lines):
        if 'MOTION' in line:
            motion_start_idx = i
            break
        hierarchy_lines.append(line)

    hierarchy_lines.append(lines[motion_start_idx])  # 保留 MOTION 行
    motion_lines = lines[motion_start_idx + 1:]

    # 找到帧数据开始位置
    frame_data_start = 0
    num_frames = 0

    for i, line in enumerate(motion_lines):
        if line.strip() and not line.startswith('Frames') and not line.startswith('Frame'):
            frame_data_start = i
            break
        if 'Frames:' in line:
            num_frames = int(line.split(':')[1].strip())

    # 处理帧数据
    output_lines = motion_lines[:frame_data_start]

    for line in motion_lines[frame_data_start:]:
        if line.strip():
            values = line.strip().split()

            # ROOT 关节的 6 个通道：Xpos Ypos Zpos Zrot Xrot Yrot
            try:
                # 提取 ROOT 的旋转值
                z_rot = float(values[3])
                x_rot = float(values[4])
                y_rot = float(values[5])

                # 应用 X 轴 270° 旋转（使用旋转矩阵）
                new_z, new_x, new_y = rotate_x_270_matrix(z_rot, x_rot, y_rot)

                # 更新值
                values[3] = f"{new_z:.6f}"
                values[4] = f"{new_x:.6f}"
                values[5] = f"{new_y:.6f}"

            except (ValueError, IndexError) as e:
                pass

            output_lines.append(' '.join(values))
        else:
            output_lines.append(line)

    # 写回文件
    new_content = ''.join(hierarchy_lines) + ''.join(output_lines)

    with open(bvh_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return num_frames


def process_directory(split_dir: Path):
    """处理目录下所有 BVH 文件"""
    bvh_files = list(split_dir.rglob('*.bvh'))

    print(f"找到 {len(bvh_files)} 个 BVH 文件")
    print("=" * 60)
    print("使用 XYZ 欧拉角旋转矩阵方式")
    print("ROOT 关节绕 X 轴旋转 270°")
    print("=" * 60)
    print()

    total_frames = 0

    for i, bvh_file in enumerate(bvh_files, 1):
        try:
            frames = process_bvh_file(bvh_file)
            total_frames += frames
            print(f"[{i}/{len(bvh_files)}] {bvh_file.name} ({frames} 帧)")
        except Exception as e:
            print(f"[{i}/{len(bvh_files)}] 错误: {bvh_file.name} - {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print(f"完成! 处理了 {len(bvh_files)} 个文件，共 {total_frames} 帧")
    print("=" * 60)


if __name__ == "__main__":
    split_dir = Path(r"e:\HKUSTGZ\HoloSoul\my_animated_drawing\examples\bvh\change\split")

    if not split_dir.exists():
        print(f"目录不存在: {split_dir}")
    else:
        process_directory(split_dir)
