#!/usr/bin/env python3
"""
根据运动幅度将 BVH 文件切分成单独的动作片段。

检测逻辑：
1. 计算每帧相对于前一帧的运动幅度
2. 幅度小 = 动作间隔/过渡
3. 幅度突增 = 新动作开始
4. 每个动作前后保留间隔帧
"""

import os
import re
import numpy as np
from pathlib import Path
from typing import List, Tuple


class BVHParser:
    """解析 BVH 文件"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.hierarchy = []
        self.frames = []
        self.num_frames = 0
        self.frame_time = 0.0
        self.joint_names = []
        self.joint_channels = []
        self._parse()

    def _parse(self):
        """解析 BVH 文件"""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 解析 HIERARCHY 部分
        in_hierarchy = True
        hierarchy_lines = []
        motion_start = 0

        for i, line in enumerate(lines):
            if 'MOTION' in line:
                in_hierarchy = False
                motion_start = i + 1
                break
            if in_hierarchy:
                hierarchy_lines.append(line)

        self.hierarchy = ''.join(hierarchy_lines)

        # 解析帧数和时间
        for i in range(motion_start, len(lines)):
            if 'Frames:' in lines[i]:
                self.num_frames = int(lines[i].split(':')[1].strip())
            elif 'Frame Time:' in lines[i]:
                self.frame_time = float(lines[i].split(':')[1].strip())
            elif lines[i].strip() and not lines[i].startswith('Frames') and not lines[i].startswith('Frame'):
                # 开始是数据
                data_start = i
                break

        # 解析运动数据
        for i in range(data_start, len(lines)):
            if lines[i].strip():
                frame_data = [float(x) for x in lines[i].strip().split()]
                self.frames.append(frame_data)

        # 提取关节名称和通道信息
        self._extract_joint_info(hierarchy_lines)

    def _extract_joint_info(self, hierarchy_lines):
        """从层级信息中提取关节名称和通道数"""
        hierarchy_text = ''.join(hierarchy_lines)
        # 找出所有 JOINT 定义
        joint_pattern = r'JOINT\s+(\w+)'
        self.joint_names = re.findall(joint_pattern, hierarchy_text)

        # 找出 CHANNELS 定义
        channel_pattern = r'CHANNELS\s+(\d+)'
        channel_matches = re.findall(channel_pattern, hierarchy_text)
        self.joint_channels = [int(c) for c in channel_matches]


class BVHSplitter:
    """根据运动幅度切分 BVH 文件"""

    def __init__(self, bvh_file: str, output_dir: str = None,
                 motion_threshold: float = 0.05,
                 min_motion_frames: int = 30,
                 padding_frames: int = 15):
        """
        Args:
            bvh_file: BVH 文件路径
            output_dir: 输出目录
            motion_threshold: 运动幅度阈值（归一化后）
            min_motion_frames: 最小动作帧数
            padding_frames: 动作前后保留的间隔帧数
        """
        self.bvh_file = bvh_file
        self.output_dir = output_dir or str(Path(bvh_file).parent / 'split')
        self.motion_threshold = motion_threshold
        self.min_motion_frames = min_motion_frames
        self.padding_frames = padding_frames

        self.parser = BVHParser(bvh_file)
        self.motion_scores = []

    def calculate_motion_score(self) -> np.ndarray:
        """计算每帧的运动幅度分数"""
        frames = np.array(self.parser.frames)
        n_frames = len(frames)

        # 计算相邻帧之间的差异
        frame_diff = np.abs(np.diff(frames, axis=0))

        # 对每个通道求和作为运动分数
        motion_scores = np.sum(frame_diff, axis=1)

        # 归一化到 [0, 1]
        if motion_scores.max() > 0:
            motion_scores = motion_scores / motion_scores.max()

        # 在开头补一个值（与第一帧相同）
        motion_scores = np.insert(motion_scores, 0, motion_scores[0] if len(motion_scores) > 0 else 0)

        self.motion_scores = motion_scores
        return motion_scores

    def detect_segments(self) -> List[Tuple[int, int, str]]:
        """检测动作片段"""
        motion_scores = self.calculate_motion_score()
        segments = []

        # 状态机：0 = 静止/间隔, 1 = 运动中
        state = 0
        segment_start = 0
        motion_count = 0

        for i, score in enumerate(motion_scores):
            if state == 0:
                # 静止状态，检测运动开始
                if score > self.motion_threshold:
                    # 检查是否有持续的运动
                    if self._check_sustained_motion(motion_scores, i):
                        state = 1
                        # 动作开始，向前取 padding 帧
                        segment_start = max(0, i - self.padding_frames)
                        motion_count = 1

            else:  # state == 1
                # 运动状态，检测运动结束
                if score <= self.motion_threshold:
                    motion_count += 1
                    # 连续多帧低运动才认为结束
                    if motion_count >= self.min_motion_frames:
                        # 动作结束，向后取 padding 帧
                        segment_end = min(len(motion_scores), i + self.padding_frames)
                        duration = segment_end - segment_start

                        if duration >= self.min_motion_frames * 2:
                            # 生成动作描述
                            avg_motion = np.mean(motion_scores[segment_start:segment_end])
                            desc = self._generate_description(segment_start, segment_end, avg_motion)
                            segments.append((segment_start, segment_end, desc))

                        state = 0
                        motion_count = 0
                else:
                    motion_count = 0

        return segments

    def _check_sustained_motion(self, scores: np.ndarray, start_idx: int) -> bool:
        """检查是否有持续的运动（不是瞬时抖动）"""
        window = 10
        end_idx = min(len(scores), start_idx + window)
        window_scores = scores[start_idx:end_idx]
        return np.mean(window_scores) > self.motion_threshold * 0.7

    def _generate_description(self, start: int, end: int, avg_motion: float) -> str:
        """生成动作描述"""
        duration_sec = (end - start) * self.parser.frame_time

        # 根据平均运动幅度和时长描述动作类型
        if avg_motion > 0.3:
            intensity = "high"
        elif avg_motion > 0.15:
            intensity = "medium"
        else:
            intensity = "low"
        duration_desc = f"{duration_sec:.1f}s"

        return f"{intensity}_{duration_desc}"

    def split_and_save(self):
        """切分并保存 BVH 文件"""
        segments = self.detect_segments()

        if not segments:
            print(f"未检测到明显的动作片段: {self.bvh_file}")
            return

        # 创建输出目录
        base_name = Path(self.bvh_file).stem
        output_dir = Path(self.output_dir) / base_name
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n处理文件: {self.bvh_file}")
        print(f"检测到 {len(segments)} 个动作片段")
        print(f"输出目录: {output_dir}\n")

        for i, (start, end, desc) in enumerate(segments):
            self._save_segment(output_dir, i, start, end, desc)

        # 保存分析图
        self._save_analysis_plot(output_dir, segments)

    def _save_segment(self, output_dir: Path, index: int, start: int, end: int, desc: str):
        """保存单个片段"""
        base_name = Path(self.bvh_file).stem
        output_name = f"{base_name}_seg{index:02d}_{desc}.bvh"
        output_path = output_dir / output_name

        # 获取片段帧数据
        segment_frames = self.parser.frames[start:end]
        num_frames = len(segment_frames)

        # 写入 BVH 文件
        with open(output_path, 'w', encoding='utf-8') as f:
            # 写入 HIERARCHY
            f.write(self.parser.hierarchy)

            # 写入 MOTION
            f.write("MOTION\n")
            f.write(f"Frames: {num_frames}\n")
            f.write(f"Frame Time: {self.parser.frame_time:.6f}\n")

            # 写入帧数据
            for frame in segment_frames:
                f.write(' '.join([f'{v:.6f}' for v in frame]) + '\n')

        duration = (end - start) * self.parser.frame_time
        print(f"  片段 {index}: {desc} | 帧 {start}-{end} | {duration:.1f}秒 | {output_name}")

    def _save_analysis_plot(self, output_dir: Path, segments: List[Tuple[int, int, str]]):
        """保存运动分析图"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib

            matplotlib.use('Agg')  # 无头模式

            fig, ax = plt.subplots(figsize=(15, 5))

            frames = np.arange(len(self.motion_scores))
            ax.plot(frames, self.motion_scores, linewidth=0.8, alpha=0.7, label='运动幅度')
            ax.axhline(y=self.motion_threshold, color='r', linestyle='--', label=f'阈值 ({self.motion_threshold})')

            # 标记片段
            colors = plt.cm.tab10(np.linspace(0, 1, len(segments)))
            for i, (start, end, desc) in enumerate(segments):
                ax.axvspan(start, end, alpha=0.2, color=colors[i])
                ax.text((start + end) / 2, 0.95, f"{i}:{desc}",
                       ha='center', va='top', fontsize=8,
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))

            ax.set_xlabel('帧数')
            ax.set_ylabel('归一化运动幅度')
            ax.set_title(f'动作检测分析 - {Path(self.bvh_file).name}')
            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.set_ylim([0, 1.1])

            base_name = Path(self.bvh_file).stem
            plt.tight_layout()
            plt.savefig(output_dir / f'{base_name}_analysis.png', dpi=150)
            plt.close()

            print(f"\n分析图已保存: {output_dir / base_name}_analysis.png")

        except ImportError:
            print("\n未安装 matplotlib，跳过分析图生成")


def process_directory(input_dir: str, exclude_patterns: List[str] = None):
    """处理目录下的所有 BVH 文件"""
    input_path = Path(input_dir)

    if exclude_patterns is None:
        exclude_patterns = ['male_ribbon']

    bvh_files = [f for f in input_path.glob('*.bvh')
                 if not any(pat in f.name for pat in exclude_patterns)]

    print(f"找到 {len(bvh_files)} 个 BVH 文件待处理")
    print(f"排除模式: {exclude_patterns}\n")

    for bvh_file in sorted(bvh_files):
        print("=" * 60)
        try:
            splitter = BVHSplitter(
                str(bvh_file),
                motion_threshold=0.05,    # 运动检测阈值
                min_motion_frames=60,     # 最小静止帧数（增加到2.5秒@24fps）
                padding_frames=30         # 前后间隔帧数（增加到1.25秒）
            )
            splitter.split_and_save()
        except Exception as e:
            print(f"处理文件 {bvh_file.name} 时出错: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("所有文件处理完成！")


if __name__ == "__main__":
    # 处理 change 目录下除 male_ribbon 相关外的所有 BVH 文件
    process_directory(
        r"e:\HKUSTGZ\HoloSoul\my_animated_drawing\examples\bvh\change",
        exclude_patterns=['male_ribbon']  # 排除所有包含 male_ribbon 的文件
    )
