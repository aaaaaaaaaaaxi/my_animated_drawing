#!/usr/bin/env python3
"""
批量生成 GIF 文件 - 并行优化版

优化点：
1. 使用 multiprocessing 多进程并行渲染
2. 直接调用 render.start() 避免 subprocess 开销
3. 进程池复用，减少模块重复加载
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Tuple
from multiprocessing import Pool, cpu_count
import traceback

# ==================== 配置区 ====================

# 角色文件夹列表（相对于 examples/characters/）
CHARACTER_DIRS = [
    # "sample",
    "sample_wu",
]

# GIF 输出目录
OUTPUT_DIR = "./output_gifs"

# 重定向配置文件（相对于 examples/config/retarget/）
RETARGET_CFG = "examples/config/retarget/male_ribbon_pfp.yaml"

# Motion 配置目录
MOTION_CONFIG_DIR = Path(r"/hpc2hdd/home/ntang745/workspace/my_animated_drawing/examples/config/motion")

# 并行进程数（None 表示自动检测，建议设置为 CPU 核心数的 50%-75%）
NUM_WORKERS = None  # 或者设置具体数字，如 8

# ================================================


def get_motion_configs(motion_config_dir: Path) -> List[Path]:
    """获取所有 motion 配置文件"""
    config_files = []
    for f in motion_config_dir.glob("*.yaml"):
        # 只处理 split 目录的 BVH 对应的配置
        if any(name in f.stem for name in [
            "female_36pose", "female_lotus", "female_mediation",
            "male_36pose", "male_drum", "male_mediation", "male_pipa"
        ]):
            config_files.append(f)
    return sorted(config_files)


def create_mvc_config(char_cfg: str, motion_cfg: str, retarget_cfg: str, mvc_cfg_path: Path, output_path: Path):
    """创建 MVC 配置文件"""
    content = f"""scene:
  ANIMATED_CHARACTERS:
    - character_cfg: {char_cfg}
      motion_cfg: {motion_cfg}
      retarget_cfg: {retarget_cfg}
view:
  USE_MESA: true
controller:
  MODE: video_render
  OUTPUT_VIDEO_PATH: {output_path}
"""
    with open(mvc_cfg_path, 'w', encoding='utf-8') as f:
        f.write(content)


def render_single_gif(args: Tuple[str, Path, Path, str]) -> Tuple[str, bool, str]:
    """
    渲染单个 GIF（工作进程函数）

    Args:
        args: (character_name, motion_config, mvc_cfg_path, retarget_cfg)

    Returns:
        (gif_name, success, error_message)
    """
    character_name, motion_config, mvc_cfg_path, retarget_cfg = args

    char_name = character_name
    motion_name = motion_config.stem
    gif_name = f"{char_name}_{motion_name}.gif"

    try:
        # 在子进程中导入（只会导入一次，后续调用复用）
        from animated_drawings import render

        # 渲染
        render.start(str(mvc_cfg_path))

        return (gif_name, True, "")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        return (gif_name, False, error_msg)


class ParallelGifGenerator:
    """并行 GIF 生成器"""

    def __init__(self,
                 character_dirs: List[str],
                 output_dir: str,
                 retarget_cfg: str,
                 motion_config_dir: Path,
                 num_workers: int = None):
        self.character_dirs = character_dirs
        self.output_dir = Path(output_dir)
        self.retarget_cfg = retarget_cfg
        self.motion_config_dir = motion_config_dir
        self.num_workers = num_workers or max(1, cpu_count() // 2)  # 默认使用一半核心

    def run(self):
        """执行并行批量生成"""
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 临时配置目录
        temp_cfg_dir = self.output_dir / "_temp_cfg"
        temp_cfg_dir.mkdir(exist_ok=True)

        # 获取所有 motion 配置
        motion_configs = get_motion_configs(self.motion_config_dir)

        # 构建所有任务
        tasks = []
        for character in self.character_dirs:
            char_cfg_path = f"examples/characters/{character}/char_cfg.yaml"

            if not Path(char_cfg_path).exists():
                print(f"跳过角色（配置不存在）: {character}")
                continue

            for motion_config in motion_configs:
                char_name = Path(character).name
                motion_name = motion_config.stem
                gif_name = f"{char_name}_{motion_name}.gif"
                gif_path = self.output_dir / gif_name

                # 创建 MVC 配置
                mvc_cfg_path = temp_cfg_dir / f"{character}_{motion_name}_mvc.yaml"
                create_mvc_config(
                    char_cfg_path,
                    str(motion_config).replace("\\", "/"),
                    self.retarget_cfg,
                    mvc_cfg_path,
                    gif_path
                )

                tasks.append((character, motion_config, mvc_cfg_path, self.retarget_cfg))

        total_tasks = len(tasks)

        print("=" * 60)
        print("并行 GIF 生成器")
        print("=" * 60)
        print(f"角色数量: {len(self.character_dirs)}")
        print(f"动作数量: {len(motion_configs)}")
        print(f"总任务数: {total_tasks}")
        print(f"并行进程数: {self.num_workers}")
        print(f"输出目录: {self.output_dir}")
        print("=" * 60)
        print()

        # 使用进程池并行处理
        success_count = 0
        failed_count = 0
        failed_tasks = []

        import time
        start_time = time.time()

        with Pool(processes=self.num_workers) as pool:
            # 使用 imap_unordered 获取更快的响应
            results = pool.imap_unordered(render_single_gif, tasks)

            for i, (gif_name, success, error_msg) in enumerate(results, 1):
                if success:
                    success_count += 1
                    status = "✓"
                else:
                    failed_count += 1
                    failed_tasks.append((gif_name, error_msg))
                    status = "✗"

                # 显示进度
                elapsed = time.time() - start_time
                avg_time = elapsed / i
                remaining = (total_tasks - i) * avg_time
                print(f"[{i}/{total_tasks}] {status} {gif_name} | "
                      f"已用: {elapsed:.1f}s | 剩余约: {remaining:.1f}s")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_cfg_dir, ignore_errors=True)

        # 输出统计
        total_time = time.time() - start_time
        print()
        print("=" * 60)
        print("生成完成!")
        print(f"总任务数: {total_tasks}")
        print(f"成功: {success_count}")
        print(f"失败: {failed_count}")
        print(f"总耗时: {total_time:.1f}s ({total_time/60:.1f}分钟)")
        print(f"平均每个: {total_time/total_tasks:.2f}s")
        print(f"输出目录: {self.output_dir.absolute()}")
        print("=" * 60)

        if failed_tasks:
            print("\n失败任务列表:")
            for gif_name, error_msg in failed_tasks[:10]:  # 只显示前10个
                print(f"  - {gif_name}: {error_msg[:100]}")
            if len(failed_tasks) > 10:
                print(f"  ... 还有 {len(failed_tasks) - 10} 个失败任务")


def main():
    """主函数"""
    generator = ParallelGifGenerator(
        character_dirs=CHARACTER_DIRS,
        output_dir=OUTPUT_DIR,
        retarget_cfg=RETARGET_CFG,
        motion_config_dir=MOTION_CONFIG_DIR,
        num_workers=NUM_WORKERS
    )
    generator.run()


if __name__ == "__main__":
    main()
