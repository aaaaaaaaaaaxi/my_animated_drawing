#!/usr/bin/env python3
"""
对 BVH 文件执行 Y ↔ -Z 坐标变换

变换规则：
- X 保持不变
- Y → -Z
- Z → Y

这与 male_ribbon_part2_30fps_rotated.bvh 的变换一致
"""

import numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation


def transform_position(x, y, z):
    """变换位置坐标: (x, y, z) → (x, -z, y)"""
    return x, -z, y


def transform_euler_zxy(z_deg, x_deg, y_deg):
    """
    变换 Z-X-Y 欧拉角以匹配 Y ↔ -Z 坐标变换

    使用旋转矩阵确保正确的变换
    """
    # 创建原始旋转矩阵 (Z-X-Y 顺序)
    R_original = Rotation.from_euler('ZYX', [z_deg, x_deg, y_deg], degrees=True).as_matrix()

    # 创建 Y ↔ -Z 变换矩阵 (绕 X 轴 -90°)
    R_transform = np.array([
        [1, 0, 0],
        [0, 0, 1],
        [0, -1, 0]
    ])

    # 组合变换: R_new = R_transform @ R_original
    R_new = R_transform @ R_original

    # 转换回欧拉角 (Z-X-Y)
    euler = Rotation.from_matrix(R_new).as_euler('ZYX', degrees=True)
    return euler[0], euler[1], euler[2]


def process_bvh_file(bvh_path: Path):
    """处理单个 BVH 文件"""
    with open(bvh_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

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

    # 处理 HIERARCHY 部分（变换 OFFSET）
    transformed_hierarchy = []
    for line in hierarchy_lines:
        if 'OFFSET' in line and '{' not in line and '}' not in line:
            # 提取 OFFSET 值
            parts = line.strip().split()
            if len(parts) >= 4:
                try:
                    x = float(parts[1])
                    y = float(parts[2])
                    z = float(parts[3])

                    # 应用 Y ↔ -Z 变换
                    new_x, new_y, new_z = transform_position(x, y, z)

                    # 重建行
                    indent = '\t' * (len(parts[0]) - len(parts[0].lstrip()))
                    new_line = f"{indent}{parts[0]} {new_x:.6f} {new_y:.6f} {new_z:.6f}"
                    transformed_hierarchy.append(new_line)
                    continue
                except (ValueError, IndexError):
                    pass
        transformed_hierarchy.append(line)

    # 处理 MOTION 部分（变换帧数据）
    output_lines = motion_lines[:frame_data_start]

    for line in motion_lines[frame_data_start:]:
        if line.strip():
            values = line.strip().split()
            new_values = []

            # 每个关节有 6 个通道：Xpos Ypos Zpos Zrot Xrot Yrot
            for i in range(0, len(values), 6):
                if i + 5 < len(values):
                    try:
                        # 变换位置
                        x_pos = float(values[i])
                        y_pos = float(values[i + 1])
                        z_pos = float(values[i + 2])
                        new_x, new_y, new_z = transform_position(x_pos, y_pos, z_pos)
                        new_values.extend([f"{new_x:.6f}", f"{new_y:.6f}", f"{new_z:.6f}"])

                        # 变换旋转
                        z_rot = float(values[i + 3])
                        x_rot = float(values[i + 4])
                        y_rot = float(values[i + 5])
                        new_z, new_x, new_y = transform_euler_zxy(z_rot, x_rot, y_rot)
                        new_values.extend([f"{new_z:.6f}", f"{new_x:.6f}", f"{new_y:.6f}"])
                    except (ValueError, IndexError):
                        # 如果出错，保留原值
                        new_values.extend(values[i:i + 6])
                else:
                    new_values.extend(values[i:])

            output_lines.append(' '.join(new_values))
        else:
            output_lines.append(line)

    # 写回文件
    new_content = '\n'.join(transformed_hierarchy) + '\n' + '\n'.join(output_lines)

    with open(bvh_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return num_frames


def process_directory(split_dir: Path):
    """处理目录下所有 BVH 文件"""
    bvh_files = list(split_dir.rglob('*.bvh'))

    print(f"Found {len(bvh_files)} BVH files")
    print("=" * 60)
    print("Applying Y <-> -Z coordinate transform")
    print("Same as male_ribbon_part2_30fps_rotated.bvh")
    print("=" * 60)
    print()

    total_frames = 0

    for i, bvh_file in enumerate(bvh_files, 1):
        try:
            frames = process_bvh_file(bvh_file)
            total_frames += frames
            print(f"[{i}/{len(bvh_files)}] {bvh_file.parent.name}/{bvh_file.name} ({frames} 帧)")
        except Exception as e:
            print(f"[{i}/{len(bvh_files)}] 错误: {bvh_file.name} - {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print(f"Done! Processed {len(bvh_files)} files, {total_frames} frames total")
    print("=" * 60)


if __name__ == "__main__":
    split_dir = Path(r"e:\HKUSTGZ\HoloSoul\my_animated_drawing\examples\bvh\change\split")

    if not split_dir.exists():
        print(f"目录不存在: {split_dir}")
    else:
        process_directory(split_dir)
