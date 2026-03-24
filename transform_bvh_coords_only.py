#!/usr/bin/env python3
"""
对 BVH 文件执行 Y ↔ -Z 坐标变换（仅位置，不变换旋转）

变换规则：
- 位置: (x, y, z) → (x, -z, y)
- 旋转: 保持不变
"""

from pathlib import Path


def transform_position(x, y, z):
    """变换位置坐标: (x, y, z) → (x, -z, y)"""
    return x, -z, y


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

    # 处理 MOTION 部分（仅变换位置，旋转保持不变）
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

                        # 旋转保持不变
                        new_values.extend([values[i + 3], values[i + 4], values[i + 5]])
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
    print("Applying Y <-> -Z coordinate transform (POSITIONS ONLY)")
    print("Rotation values unchanged")
    print("=" * 60)
    print()

    total_frames = 0

    for i, bvh_file in enumerate(bvh_files, 1):
        try:
            frames = process_bvh_file(bvh_file)
            total_frames += frames
            print(f"[{i}/{len(bvh_files)}] {bvh_file.parent.name}/{bvh_file.name} ({frames} frames)")
        except Exception as e:
            print(f"[{i}/{len(bvh_files)}] Error: {bvh_file.name} - {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print(f"Done! Processed {len(bvh_files)} files, {total_frames} frames total")
    print("=" * 60)


if __name__ == "__main__":
    split_dir = Path(r"e:\HKUSTGZ\HoloSoul\my_animated_drawing\examples\bvh\change\split")

    if not split_dir.exists():
        print(f"Directory not found: {split_dir}")
    else:
        process_directory(split_dir)
