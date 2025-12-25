<div align="center">

  [EN](../README.md) | 中文
</div>

<div align="center">

# ✨ Discord Image Upscaler Bot
</div>
(Discord 图像放大机器人)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9.4-blue.svg" alt="Python 版本" />
  <img src="https://img.shields.io/badge/discord.py-v2.x-7289DA.svg?logo=discord&logoColor=white" alt="discord.py 框架" />
  <img src="https://img.shields.io/badge/证照-MIT-green.svg" alt="MIT 许可证" />
  <img src="https://img.shields.io/badge/状态-活跃-green.svg" alt="状态：活跃" />
  <img src="https://img.shields.io/badge/Azure%20Blob%20Storage-存储-0078D4.svg?logo=microsoftazure&logoColor=white" alt="Azure Blob 存储" />
</p>


Discord 图像放大机器人是一款简单且可靠的工具，它通过斜杠命令（Slash Command）接收图片附件，将 AI 放大任务放入 PostgreSQL 队列中，由独立的 Worker 进程使用 Real-ESRGAN 处理，最后将放大后的图片返回原频道并清理本地文件。本项目基于 Python 和 discord.py 构建，设计为双进程协同运行，确保在 Worker 利用 CPU/GPU 进行繁重处理时，Bot 依然保持响应。


## 🔍 功能介绍
- 通过 `/upscale` 斜杠命令接收图片附件与模型类型选择。
- 将任务写入 PostgreSQL 队列，独立 Worker 轮询并处理任务。
- 使用 Real-ESRGAN（可选 GPU/FP16）进行图像放大。
- 将处理结果上传至 Azure Blob（可选）并将结果发送回原 Discord 频道。
- 本地文件处理后自动清理，避免磁盘积累。

## 🚀 快速开始
1. 克隆仓库到本地并进入项目文件夹。
2. 创建并激活虚拟环境：
   - macOS / Linux:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (cmd / PowerShell):
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
4. 在项目根目录创建 `.env` 文件，至少包含：
   ```
   DISCORD_TOKEN=你的token
   POSTGRE_CONN_STRING=postgres://user:password@localhost:5432/upscaler
   ```
5. 下载 Real-ESRGAN 模型权重文件并放入 `models/` 目录（示例见下文）。
6. 启动两个进程：
   - 在一个终端运行：
     ```bash
     python worker.py
     ```
   - 在另一个终端运行：
     ```bash
     python bot.py
     ```

如果你想自动化这些步骤，可以使用仓库根目录提供的启动脚本（例如 Windows 的 `start_upscaler.bat`）。

## ⚙️ 前置要求
- Python 3.8+
- PostgreSQL 可被 Bot 和 Worker 访问
- 若使用 GPU 加速：NVIDIA 驱动 + 匹配 PyTorch CUDA 版本
- 在 `models/` 目录放置 Real-ESRGAN 权重文件，或修改 `utils/ImageProcessing.py` 指向你的模型文件

## 🧾 模型
默认期望以下模型（放在仓库根目录下的 `models/`）：
- `RealESRGAN_x4plus.pth` — 用于普通照片
- `RealESRGAN_x4plus_anime_6B.pth` — 用于动漫 / 插画

对于非常大的图片，Worker 会自动启用瓦片（tiled）处理以减小显存/内存压力。

## ▶️ 本地运行
- 启动 Worker：`python worker.py` — 轮询任务并执行放大
- 启动 Bot：`python bot.py` — 注册 `/upscale` 命令并负责发送结果
- 在服务器中使用 `/upscale` 上传图片并选择模型类型。命令会回复任务 ID；处理完成后，Bot 会把结果发送回原频道并删除本地临时文件。

## ☁️ 部署建议
- 建议将 Bot 与 Worker 分别作为独立服务运行（避免阻塞）。
- 对于小型部署：使用 Docker Compose，挂载 `models/` 与 `output/`。
- 生产部署建议使用 systemd / Docker / Kubernetes，生产数据库建议使用托管 PostgreSQL。
- 高吞吐场景：监控磁盘使用并清理旧条目与输出文件。

## 🗂️ 指令（Commands）
- /upscale
  - 参数：`image`（图片附件）、`type`（模型类型，选项：General Photo / 普通照片、Anime / Illustration / 动漫插画）
  - 行为：验证、入队并回复任务编号；完成后发送结果。

## 🛠 技术栈
Python · discord.py · Real-ESRGAN · PyTorch · basicsr · OpenCV · NumPy · requests · asyncpg · python-dotenv · Docker / systemd / Kubernetes

## 🤝 贡献
- Fork 仓库并创建分支
- 提交清晰的 Pull Request 并在 PR 描述中说明变更
- 尽量保持数据库迁移最小化与向后兼容

## 📜 许可证
本项目基于 MIT 许可证开源。请查看仓库中的 `LICENSE` 文件了解详细条款。

## 🙏 致谢
感谢 Real-ESRGAN、basicsr、PyTorch 及开源社区提供的工具与示例。

## ✉️ 联系方式
- Bug 或功能请求：请提交 Issue
- 部署帮助或功能讨论：请开启 Discussion