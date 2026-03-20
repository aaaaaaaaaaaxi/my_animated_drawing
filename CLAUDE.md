# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 提供在此代码库中工作的指导。

## 项目概述

Animated Drawings 是一个能够自动为儿童绘制的人物画添加动画的系统。它实现了 SIGGRAPH 2023 论文《A Method for Animating Children's Drawings of the Human Figure》中的算法。

该系统通过以下方式将 2D 绘画与 3D 动作捕捉数据结合：
- 基于机器学习的人物检测和姿态估计
- 从 2D 关节位置创建骨骼绑定
- ARAP（尽可能刚性）网格变形
- 从 3D BVH 文件到 2D 角色绑定的动作重定向

## 开发命令

### 安装
```bash
conda create --name animated_drawings python=3.8.13
conda activate animated_drawings
pip install -e .
```

### 运行动画
```python
from animated_drawings import render
render.start('./examples/config/mvc/interactive_window_example.yaml')
```

或通过命令行：
```bash
python animated_drawings/render.py <config_file>
```

### 测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_render.py

# 使用 CI 环境变量运行（跳过渲染测试）
IS_CI_RUNNER=True pytest
```

### 代码检查
```bash
flake8 . --ignore=E222,E402,E226,E241,E203,E202,E271,E201,E221,C901 --count --max-complexity=10 --max-line-length=200
```

### ML 模型服务器（用于绘画 → 动画）
```bash
# Docker 方式
cd torchserve
docker build -t docker_torchserve .
docker run -d --name docker_torchserve -p 8080:8080 -p 8081:8081 docker_torchserve

# macOS 本地方式
cd torchserve
./setup_macos.sh
torchserve --start --ts-config config.local.properties --foreground
```

### 将绘画转换为动画
```bash
# 在 examples 目录下
python image_to_animation.py drawings/garlic.png garlic_out
```

## 架构（MVC 模式）

项目遵循模型-视图-控制器架构：

### 模型层 (`animated_drawings/model/`)
- **`animated_drawing.py`**: 核心角色类，处理骨骼绑定设置、动画和 ARAP 网格变形
- **`retargeter.py`**: 将 3D BVH 动作数据映射到 2D 角色绑定
- **`arap.py`**: 尽可能刚性（ARAP）网格变形算法实现
- **`bvh.py`**: BioVision 层级动作文件解析器
- **`joint.py`**: 关节层级和变换管理
- **`scene.py`**: 场景管理

### 视图层 (`animated_drawings/view/`)
- **`window_view.py`**: 带相机控制的交互式 OpenGL 窗口（使用 GLFW）
- **`mesa_view.py`**: 用于文件导出的无头渲染（使用 OSMesa）

### 控制器层 (`animated_drawings/controller/`)
- **`interactive_controller.py`**: 实时交互控制（暂停/播放、时间导航）
- **`video_render_controller.py`**: 用于视频/GIF 导出的批量渲染

## 配置系统

所有动画都由 `examples/config/` 中的 YAML 配置文件驱动：

### MVC 配置（顶层）
控制场景、视图和控制器设置。继承自 `animated_drawings/mvc_base_cfg.yaml` 并覆盖指定参数。

关键参数：
- `scene.ANIMATED_CHARACTERS`: 角色/动作/重定向配置三元组列表
- `view.USE_MESA`: 启用无头渲染（服务器环境必需）
- `controller.MODE`: `'interactive'` 或 `'video_render'`
- `controller.OUTPUT_VIDEO_PATH`: video_render 模式的输出文件路径

### 角色配置
定义角色的骨骼结构：
- `skeleton`: 关节列表，每个关节包含 `loc`（像素位置）、`name` 和 `parent`
- 期望同一目录下有 `texture.png` 和 `mask.png`

### 动作配置
指定 BVH 动作文件参数：
- `filepath`: BVH 文件路径
- `forward_perp_joint_vectors`: 用于计算骨骼前向方向的关节对
- `up`: 骨骼的上方向（`+y` 或 `+z`）

### 重定向配置
将 BVH 动作映射到角色绑定：
- `bvh_projection_bodypart_groups`: 每个身体部位使用哪个投影平面（正面/矢状面/PCA）
- `char_joint_bvh_joints_mapping`: 将角色关节映射到 BVH 关节对
- `char_bodypart_groups`: 角色部位的渲染深度排序

## 关键工作流程

### 创建自定义动画

1. **使用预绑定角色**: 参考 `examples/characters/` 中的示例
2. **从绘画创建动画**: 需要 ML 模型服务器，然后运行 `image_to_animation.py`
3. **修复标注**: 运行 `fix_annotations.py` 启动 Web 界面来修正关节位置
4. **多个角色**: 在 `scene.ANIMATED_CHARACTERS` 中添加多个条目
5. **自定义 BVH**: 为新骨骼结构创建动作配置和重定向配置

### 无头渲染
对于远程服务器或 CI 环境，在配置中设置 `view.USE_MESA: True`。不能与 `controller.MODE: 'interactive'` 同时使用。

### 非标准骨骼
系统支持自定义骨骼配置（如 6 条手臂、4 条腿）。修改角色配置的骨骼和相应的重定向配置映射。参见 `six_arms_example.yaml` 和 `four_legs_example.yaml`。

## Python 版本

此项目需要 **Python 3.8.13** 确切版本。依赖项在 `setup.py` 中已固定。

## 文件结构说明

- `animated_drawings/mvc_base_cfg.yaml`: 请勿修改 - 所有 MVC 配置继承的基础配置
- `examples/config/mvc/` 中的示例配置文件展示了各种功能
- 测试资源位于 `tests/test_render_files/`
- `examples/characters/` 中的角色示例包含纹理、遮罩和配置文件
