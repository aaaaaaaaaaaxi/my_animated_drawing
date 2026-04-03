#!/usr/bin/env python3
"""
批量渲染火柴人动画

将BVH文件渲染成火柴人动画（只显示骨骼线条）
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional


# ==================== 配置区 ====================

# BVH文件根目录
BVH_ROOT_DIR = Path("/hpc2hdd/home/ntang745/workspace/my_animated_drawing/examples/bvh/change/split")

# Motion配置目录（已存在的motion配置）
MOTION_CONFIG_DIR = Path("/hpc2hdd/home/ntang745/workspace/my_animated_drawing/examples/config/motion")

# Retarget配置文件
RETARGET_CFG = "examples/config/retarget/male_ribbon_pfp.yaml"

# GIF输出目录
OUTPUT_DIR = Path("/hpc2hdd/home/ntang745/workspace/my_animated_drawing/output_stick_figures")

# 项目根目录
PROJECT_ROOT = Path("/hpc2hdd/home/ntang745/workspace/my_animated_drawing")

# ================================================


class StickFigureRenderer:
    """火柴人动画渲染器"""

    # MVC配置模板
    MVC_TEMPLATE = """scene:
  ADD_FLOOR: false
  ADD_AD_RETARGET_BVH: true
  ANIMATED_CHARACTERS:
    - character_cfg: examples/characters/sample/char_cfg.yaml
      motion_cfg: {motion_cfg}
      retarget_cfg: {retarget_cfg}
view:
  USE_MESA: true
  CLEAR_COLOR: [1.0, 1.0, 1.0, 1.0]
  BACKGROUND_IMAGE: null
  WINDOW_DIMENSIONS: [500, 500]
  DRAW_AD_RIG: true
  DRAW_AD_TXTR: false
  DRAW_AD_COLOR: false
  DRAW_AD_MESH_LINES: false
  CAMERA_POS: [0.0, 0.7, 2.0]
  CAMERA_FWD: [0.0, 0.5, 2.0]
controller:
  MODE: video_render
  OUTPUT_VIDEO_PATH: {output_path}
  OUTPUT_VIDEO_CODEC: null
"""

    def __init__(self,
                 bvh_root_dir: Path,
                 motion_config_dir: Path,
                 retarget_cfg: str,
                 output_dir: Path,
                 project_root: Path):
        self.bvh_root_dir = bvh_root_dir
        self.motion_config_dir = motion_config_dir
        self.retarget_cfg = retarget_cfg
        self.output_dir = output_dir
        self.project_root = project_root
        self.rendered_count = 0
        self.failed_count = 0
        self.temp_cfg_dir = self.output_dir / "_temp_cfg"

    def _init_temp_dir(self):
        """初始化临时目录"""
        self.temp_cfg_dir.mkdir(parents=True, exist_ok=True)

    def _cleanup_temp_dir(self):
        """清理临时目录"""
        shutil.rmtree(self.temp_cfg_dir, ignore_errors=True)

    def get_bvh_files(self) -> List[Path]:
        """获取所有BVH文件"""
        bvh_files = []
        for subdir in self.bvh_root_dir.iterdir():
            if subdir.is_dir():
                for bvh_file in subdir.glob("*.bvh"):
                    bvh_files.append(bvh_file)
        return sorted(bvh_files)

    def get_motion_configs(self) -> List[Path]:
        """获取所有split相关的motion配置"""
        motion_configs = []
        keywords = [
            "female_36pose", "female_lotus", "female_mediation",
            "male_36pose", "male_drum", "male_mediation", "male_pipa"
        ]
        for f in self.motion_config_dir.glob("*.yaml"):
            if any(kw in f.stem for kw in keywords):
                motion_configs.append(f)
        return sorted(motion_configs)

    def create_motion_config(self, bvh_file: Path, output_path: Path):
        """为BVH文件创建motion配置"""
        content = f"""filepath: {bvh_file}
start_frame_idx: 0
end_frame_idx: 100000
groundplane_joint: LeftAnkle
forward_perp_joint_vectors:
  - - LeftShoulder
    - RightShoulder
  - - LeftHip
    - RightHip
scale: 0.025
up: +z
"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def create_mvc_config(self, motion_cfg: str, output_gif: Path) -> Path:
        """创建MVC配置文件"""
        mvc_cfg_path = self.temp_cfg_dir / f"{output_gif.stem}_mvc.yaml"
        content = self.MVC_TEMPLATE.format(
            motion_cfg=motion_cfg,
            retarget_cfg=self.retarget_cfg,
            output_path=output_gif
        )
        with open(mvc_cfg_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return mvc_cfg_path

    def render(self, mvc_cfg_path: Path, output_gif: Path) -> bool:
        """执行渲染"""
        print(f"  渲染: {output_gif.name}")

        try:
            result = subprocess.run(
                [sys.executable, "-c",
                 f"from animated_drawings import render; render.start('{mvc_cfg_path}')"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )

            if result.returncode == 0 and output_gif.exists():
                self.rendered_count += 1
                return True
            else:
                error_msg = result.stderr[:200] if result.stderr else '未知错误'
                print(f"    错误: {error_msg}")
                self.failed_count += 1
                return False

        except Exception as e:
            print(f"    异常: {e}")
            self.failed_count += 1
            return False

    def render_with_existing_config(self, motion_config: Path) -> bool:
        """使用已有motion配置渲染"""
        output_gif = self.output_dir / f"{motion_config.stem}.gif"

        if output_gif.exists():
            print(f"  跳过（已存在）: {output_gif.name}")
            return True

        mvc_cfg_path = self.create_mvc_config(str(motion_config), output_gif)
        return self.render(mvc_cfg_path, output_gif)

    def render_bvh_directly(self, bvh_file: Path) -> bool:
        """直接渲染BVH文件"""
        parent_dir = bvh_file.parent.name
        output_gif = self.output_dir / f"{parent_dir}_{bvh_file.stem}.gif"

        if output_gif.exists():
            print(f"  跳过（已存在）: {output_gif.name}")
            return True

        # 创建临时motion配置
        temp_motion_cfg = self.temp_cfg_dir / f"{bvh_file.stem}_motion.yaml"
        self.create_motion_config(bvh_file, temp_motion_cfg)

        mvc_cfg_path = self.create_mvc_config(str(temp_motion_cfg), output_gif)
        return self.render(mvc_cfg_path, output_gif)

    def run(self, use_existing_configs: bool = True):
        """执行批量渲染"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._init_temp_dir()

        print("=" * 60)
        print("火柴人动画批量渲染器")
        print("=" * 60)

        if use_existing_configs:
            motion_configs = self.get_motion_configs()
            total = len(motion_configs)
            print(f"动作数量: {total}")
            print(f"输出目录: {self.output_dir}")
            print("=" * 60)
            print()

            for i, motion_config in enumerate(motion_configs, 1):
                print(f"[{i}/{total}] {motion_config.name}")
                self.render_with_existing_config(motion_config)
        else:
            bvh_files = self.get_bvh_files()
            total = len(bvh_files)
            print(f"BVH文件数量: {total}")
            print(f"输出目录: {self.output_dir}")
            print("=" * 60)
            print()

            for i, bvh_file in enumerate(bvh_files, 1):
                print(f"[{i}/{total}] {bvh_file.name}")
                self.render_bvh_directly(bvh_file)

        self._cleanup_temp_dir()

        print()
        print("=" * 60)
        print("渲染完成!")
        print(f"成功: {self.rendered_count}")
        print(f"失败: {self.failed_count}")
        print(f"输出目录: {self.output_dir}")
        print("=" * 60)


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='批量渲染火柴人动画')
    parser.add_argument('--all', action='store_true', help='处理所有BVH文件（不仅是已有配置的）')
    args = parser.parse_args()

    renderer = StickFigureRenderer(
        bvh_root_dir=BVH_ROOT_DIR,
        motion_config_dir=MOTION_CONFIG_DIR,
        retarget_cfg=RETARGET_CFG,
        output_dir=OUTPUT_DIR,
        project_root=PROJECT_ROOT
    )
    renderer.run(use_existing_configs=not args.all)


if __name__ == "__main__":
    main()
