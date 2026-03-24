#!/usr/bin/env python3
"""
为 split 目录下的所有 BVH 文件生成正确的 motion 配置

关键参数：
- up: +z  (原始 BVH 文件 Z 轴是上方向)
"""

import os
from pathlib import Path


SPLIT_DIR = Path(r"e:\HKUSTGZ\HoloSoul\my_animated_drawing\examples\bvh\change\split")
OUTPUT_DIR = Path(r"e:\HKUSTGZ\HoloSoul\my_animated_drawing\examples\config\motion")


def get_frame_count(bvh_file: Path) -> int:
    """从 BVH 文件读取帧数"""
    with open(bvh_file, 'r') as f:
        for line in f:
            if line.startswith("Frames:"):
                return int(line.split(":")[1].strip())
    return 0


def create_motion_config(bvh_file: Path) -> str:
    """创建 motion 配置内容"""
    frames = get_frame_count(bvh_file)

    # 生成相对于 examples 目录的路径
    rel_path = bvh_file.relative_to(Path(r"e:\HKUSTGZ\HoloSoul\my_animated_drawing"))
    filepath = str(rel_path).replace("\\", "/")

    config = f"""filepath: {filepath}
start_frame_idx: 0
end_frame_idx: {frames - 1}
groundplane_joint: LeftAnkle
forward_perp_joint_vectors:
  - - LeftShoulder
    - RightShoulder
  - - LeftHip
    - RightHip
scale: 0.025
up: +z
"""
    return config


def generate_all_configs():
    """为所有 BVH 文件生成配置"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    bvh_files = list(SPLIT_DIR.rglob("*.bvh"))

    print(f"Found {len(bvh_files)} BVH files")
    print("=" * 60)
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"up axis: +z (original BVH coordinate system)")
    print("=" * 60)
    print()

    for i, bvh_file in enumerate(bvh_files, 1):
        # 生成配置文件名
        config_name = f"{bvh_file.stem}.yaml"
        config_path = OUTPUT_DIR / config_name

        # 创建配置
        config_content = create_motion_config(bvh_file)

        # 写入文件
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)

        print(f"[{i}/{len(bvh_files)}] {config_name}")

    print()
    print("=" * 60)
    print(f"Done! Generated {len(bvh_files)} motion config files")
    print("=" * 60)


if __name__ == "__main__":
    generate_all_configs()
