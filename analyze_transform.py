#!/usr/bin/env python3
"""
分析 male_ribbon_part2_30fps_rotated.bvh 的实际变换方式
"""

import numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation


# 读取原版和旋转版的第一帧数据
original_file = r"e:\HKUSTGZ\HoloSoul\my_animated_drawing\examples\bvh\change\male_ribbon_part2_30fps.bvh"
rotated_file = r"e:\HKUSTGZ\HoloSoul\my_animated_drawing\examples\bvh\change\male_ribbon_part2_30fps_rotated.bvh"


def read_first_frame(filepath):
    """读取第一帧数据"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if line.strip() and not line.startswith('HIERARCHY') and not line.startswith('ROOT') and \
           not line.startswith('JOINT') and not line.startswith('OFFSET') and \
           not line.startswith('CHANNELS') and not line.startswith('End') and \
           not line.startswith('{') and not line.startswith('}') and \
           not line.startswith('MOTION') and not line.startswith('Frames') and \
           not line.startswith('Frame'):
            if 'Frames' not in line and 'Frame' not in line:
                values = [float(x) for x in line.strip().split()]
                return values

    return None


# 读取数据
original_data = read_first_frame(original_file)
rotated_data = read_first_frame(rotated_file)

if original_data and rotated_data:
    print("=" * 60)
    print("第一帧 ROOT 关节数据对比")
    print("=" * 60)

    # 位置 (索引 0-2)
    print("\n位置:")
    print(f"原版: X={original_data[0]:.6f}, Y={original_data[1]:.6f}, Z={original_data[2]:.6f}")
    print(f"旋转: X={rotated_data[0]:.6f}, Y={rotated_data[1]:.6f}, Z={rotated_data[2]:.6f}")

    # 验证 Y <-> -Z 变换
    expected_y = -original_data[2]
    expected_z = original_data[1]
    print(f"\n预期 (Y=-Z): Y={expected_y:.6f}, Z={expected_z:.6f}")
    print(f"实际旋转:     Y={rotated_data[1]:.6f}, Z={rotated_data[2]:.6f}")
    print(f"匹配: Y={abs(expected_y - rotated_data[1]) < 0.001}, Z={abs(expected_z - rotated_data[2]) < 0.001}")

    # 旋转 (索引 3-5)
    print("\n旋转 (Z, X, Y):")
    print(f"原版: Z={original_data[3]:.6f}, X={original_data[4]:.6f}, Y={original_data[5]:.6f}")
    print(f"旋转: Z={rotated_data[3]:.6f}, X={rotated_data[4]:.6f}, Y={rotated_data[5]:.6f}")

    # 尝试不同的变换方式
    print("\n" + "=" * 60)
    print("尝试推导旋转变换公式")
    print("=" * 60)

    z_orig, x_orig, y_orig = original_data[3], original_data[4], original_data[5]
    z_rot, x_rot, y_rot = rotated_data[3], rotated_data[4], rotated_data[5]

    # 方法1: 检查是否只是简单的加法/乘法
    print(f"\nZ轴差异: {z_rot - z_orig:.6f}")
    print(f"X轴差异: {x_rot - x_orig:.6f}")
    print(f"Y轴差异: {y_rot - y_orig:.6f}")

    # 方法2: 检查是否旋转变换
    print("\n方法2: 尝试 90度旋转")
    # -90度 X轴旋转的欧拉角变换
    R_orig = Rotation.from_euler('ZYX', [z_orig, x_orig, y_orig], degrees=True)
    R_minus90_x = Rotation.from_euler('X', [-90], degrees=True)
    R_combined = R_minus90_x * R_orig
    euler_result = R_combined.as_euler('ZYX', degrees=True)
    print(f"计算结果: Z={euler_result[0]:.6f}, X={euler_result[1]:.6f}, Y={euler_result[2]:.6f}")
    print(f"实际旋转: Z={z_rot:.6f}, X={x_rot:.6f}, Y={y_rot:.6f}")
