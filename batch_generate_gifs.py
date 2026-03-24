#!/usr/bin/env python3
"""
批量生成 GIF 文件

使用已生成的 motion 配置文件批量渲染 GIF
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List


# ==================== 配置区 ====================

# 角色文件夹列表（相对于 examples/characters/）
CHARACTER_DIRS = [
    "sample",
    "sample_wu",
]

# GIF 输出目录
OUTPUT_DIR = "./output_gifs"

# 重定向配置文件（相对于 examples/config/retarget/）
RETARGET_CFG = "examples/config/retarget/male_ribbon_pfp.yaml"

# Motion 配置目录
MOTION_CONFIG_DIR = Path(r"e:\HKUSTGZ\HoloSoul\my_animated_drawing\examples\config\motion")

# ================================================


class BatchGifGenerator:
    """批量 GIF 生成器"""

    def __init__(self,
                 character_dirs: List[str],
                 output_dir: str,
                 retarget_cfg: str,
                 motion_config_dir: Path):
        self.character_dirs = character_dirs
        self.output_dir = Path(output_dir)
        self.retarget_cfg = retarget_cfg
        self.motion_config_dir = motion_config_dir
        self.generated_count = 0
        self.failed_count = 0

    def get_motion_configs(self):
        """获取所有 motion 配置文件"""
        # 只读取 split 相关的配置（排除原有的示例配置）
        config_files = []
        for f in self.motion_config_dir.glob("*.yaml"):
            # 只处理 split 目录的 BVH 对应的配置
            if any(name in f.stem for name in [
                "female_36pose", "female_lotus", "female_mediation",
                "male_36pose", "male_drum", "male_mediation", "male_pipa"
            ]):
                config_files.append(f)
        return sorted(config_files)

    def create_mvc_config(self, char_cfg: str, motion_cfg: str, mvc_cfg_path: Path):
        """创建 MVC 配置文件"""
        # 手动写入 YAML
        content = f"""scene:
  ANIMATED_CHARACTERS:
    - character_cfg: {char_cfg}
      motion_cfg: {motion_cfg}
      retarget_cfg: {self.retarget_cfg}
view:
  USE_MESA: true
controller:
  MODE: video_render
  OUTPUT_VIDEO_PATH: DUMMY_PATH
"""
        with open(mvc_cfg_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def generate_gif(self, character: str, motion_config: Path, mvc_cfg_path: Path):
        """生成单个 GIF"""
        char_name = Path(character).name
        motion_name = motion_config.stem
        gif_name = f"{char_name}_{motion_name}.gif"
        gif_path = self.output_dir / gif_name

        # 更新 MVC 配置中的输出路径
        self._update_mvc_output(mvc_cfg_path, gif_path)

        print(f"  生成: {gif_name}")

        # 调用渲染
        try:
            result = subprocess.run(
                [sys.executable, "-c", f"from animated_drawings import render; render.start('{mvc_cfg_path}')"],
                capture_output=True,
                text=True
                # 移除超时限制
            )

            if result.returncode == 0:
                self.generated_count += 1
                return True
            else:
                print(f"    错误: {result.stderr[:200] if result.stderr else '未知错误'}")
                self.failed_count += 1
                return False

        except subprocess.TimeoutExpired:
            print(f"    超时（已移除超时限制）")
            self.failed_count += 1
            return False
        except Exception as e:
            print(f"    异常: {e}")
            self.failed_count += 1
            return False

    def _update_mvc_output(self, mvc_cfg_path: Path, output_path: Path):
        """更新 MVC 配置中的输出路径"""
        with open(mvc_cfg_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        with open(mvc_cfg_path, 'w', encoding='utf-8') as f:
            for line in lines:
                if "OUTPUT_VIDEO_PATH:" in line:
                    f.write(f"  OUTPUT_VIDEO_PATH: {output_path}\n")
                else:
                    f.write(line)

    def run(self):
        """执行批量生成"""
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 临时配置目录
        temp_cfg_dir = self.output_dir / "_temp_cfg"
        temp_cfg_dir.mkdir(exist_ok=True)

        # 获取所有 motion 配置
        motion_configs = self.get_motion_configs()

        total_tasks = 0

        print("=" * 60)
        print("批量 GIF 生成器")
        print("=" * 60)
        print(f"角色数量: {len(self.character_dirs)}")
        print(f"动作数量: {len(motion_configs)}")
        print(f"总任务数: {len(self.character_dirs) * len(motion_configs)}")
        print(f"输出目录: {self.output_dir}")
        print("=" * 60)
        print()

        for character in self.character_dirs:
            char_cfg_path = f"examples/characters/{character}/char_cfg.yaml"

            if not Path(char_cfg_path).exists():
                print(f"跳过角色（配置不存在）: {character}")
                continue

            print(f"角色: {character}")
            print("-" * 40)

            for motion_config in motion_configs:
                total_tasks += 1

                # 创建 MVC 配置
                mvc_cfg_path = temp_cfg_dir / f"{character}_{motion_config.stem}_mvc.yaml"
                self.create_mvc_config(
                    char_cfg_path,
                    str(motion_config).replace("\\", "/"),
                    mvc_cfg_path
                )

                # 生成 GIF
                self.generate_gif(character, motion_config, mvc_cfg_path)

            print()

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_cfg_dir, ignore_errors=True)

        # 输出统计
        print("=" * 60)
        print("生成完成!")
        print(f"总任务数: {total_tasks}")
        print(f"成功: {self.generated_count}")
        print(f"失败: {self.failed_count}")
        print(f"输出目录: {self.output_dir.absolute()}")
        print("=" * 60)


def main():
    """主函数"""
    generator = BatchGifGenerator(
        character_dirs=CHARACTER_DIRS,
        output_dir=OUTPUT_DIR,
        retarget_cfg=RETARGET_CFG,
        motion_config_dir=MOTION_CONFIG_DIR
    )
    generator.run()


if __name__ == "__main__":
    main()
