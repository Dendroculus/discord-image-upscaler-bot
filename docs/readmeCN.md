<div align="center">

  中文 | [EN](./README.md)
</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9.4-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/discord.py-v2.x-7289DA.svg?logo=discord&logoColor=white" alt="discord.py">
  <img src="https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Azure%20Blob%20Storage-Storage-0078D4.svg?logo=microsoftazure&logoColor=white" alt="Azure Blob Storage">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT">
  <img src="https://img.shields.io/badge/status-Active-green.svg" alt="Update Status">
</p>

<div align="center">

# ✨ Discord 图像放大机器人

</div>

Discord Image Upscaler Bot 是一个简单且可靠的工具，使用斜杠命令接收图像附件，将 AI 放大任务排入 PostgreSQL 队列，在单独的 Worker 中使用 Real-ESRGAN 进行处理，并将放大后的图像返回到原始频道，同时清理本地文件。该项目基于 Python 与 discord.py 构建，设计为以两个协作进程运行，这样当 Worker 在 CPU/GPU 上执行繁重计算时 Bot 仍能保持响应。

## 🎥 演示

| 原图（低分辨率） | Real-ESRGAN 放大（4x） |
| :---: | :---: |
| <img src="https://github.com/Dendroculus/discord-image-upscaler-bot/blob/main/assets/previews/ado.jpg" width="300"> | <img src="https://github.com/Dendroculus/discord-image-upscaler-bot/blob/main/assets/previews/ado_upscaled.png" width="300"> |

<details>
  <summary><b>🎥 点击观看预览（20 秒）</b></summary>


  <br>
  <video src="https://github-production-user-asset-6210df.s3.amazonaws.com/224712928/530954801-44ea77eb-489a-44e5-9b1d-ef48472f8dc3.mp4?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAVCODYLSA53PQK4ZA%2F20251230%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20251230T105413Z&X-Amz-Expires=300&X-Amz-Signature=16b5b57028579d73a7da4aedcbd399810068b719b89e1b75d0433a81614d684e&X-Amz-SignedHeaders=host">
    
</details>  

## ✨ 主要功能

- 🚀 使用 `RealESRGAN_x4plus` 与 `RealESRGAN_x4plus_anime_6B` 实现 400% AI 放大。
- ☁️ 处理结果云端上传到 **Azure Blob Storage**，提供永久的 CDN 链接。
- 🛡️ 具有心跳检测与过期任务自动恢复，具备崩溃恢复能力。
- 🔒 使用 PostgreSQL 的 `FOR UPDATE SKIP LOCKED` 实现并发安全。
- 🧠 通过 `ModelRegistry` 实现智能缓存以管理显存（动态加载/卸载模型）。

## 🏗️ 架构

<img src="https://github.com/Dendroculus/discord-image-upscaler-bot/blob/main/assets/ArchitectureDiagram.png">


## 📂 项目结构

```bash
Discord-Image-Upscaler-Bot/
├── bot.py                     # Discord 机器人的入口点 (Producer)
├── worker.py                  # 后台 Worker 的入口点 (Consumer)
├── database.py                # 异步数据库接口
├── .env                       # 秘钥和配置
│
├── cogs/                      # Discord 斜杠命令
│   └── UpScale.py
│
├── constants/                 # 静态配置
│   ├── configs.py             # 常量值
│   ├── Emojis.py              # 表情符号定义
│   └── ModelRegistry.py       # 动态模型加载器
│
├── services/                  # 外部服务适配器
│   ├── StorageService.py      # Azure Blob 逻辑
│   └── NotificationService.py # Discord 嵌入消息逻辑
│
├── utils/                     # 核心工具
│   └── ImageProcessing.py     # AI 推理引擎
│
└── models/                    # 预训练的 .pth 权重文件
```

## 🚀 快速开始

即使你是 Discord 机器人新手，上手也很简单。首先将仓库克隆到本地并打开终端。创建并激活虚拟环境（例如 `python -m venv .venv` 然后在 macOS/Linux 上运行 `source .venv/bin/activate`，或在 Windows 上运行 `.venv\Scripts\activate`）。通过 `pip install -r requirements.txt` 安装运行时依赖。在项目根目录创建一个 `.env` 文件，至少包含 `DISCORD_TOKEN` 与 `POSTGRE_CONN_STRING`（示例见下）。下载 Real-ESRGAN 模型权重并放入与代码并列的 `models/` 文件夹中。准备就绪后，在一个终端运行 `python worker.py` 以便开始轮询任务，在另一个终端运行 `python bot.py` 以便接收斜杠命令并发送处理结果。如果需要 `.env` 的快速复制粘贴示例，可使用下方作为起点：

### 下面是一个在本地设置环境并安装依赖的简短脚本示例：
```bash
# 创建虚拟环境
python -m venv .venv

# 在 macOS / Linux 中激活虚拟环境
source .venv/bin/activate

# 在 Windows (cmd / PowerShell) 中激活虚拟环境
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

```env
DISCORD_TOKEN=your_token_here
POSTGRE_CONN_STRING=postgres://user:password@localhost:5432/upscaler
AZURE_CONNECTION_STRING=your_azure_connection_string_here
```

如果出现问题，请检查两个进程的日志：Worker 会打印处理与模型错误，Bot 会打印交付与权限错误。

## ⚙️ 先决条件

本项目需要 Python 3.8+，并且 Worker 与 Bot 均能访问 PostgreSQL 实例。若需 GPU 加速，则需支持 CUDA 的 GPU、与之匹配的 PyTorch CUDA 构建以及正确的 NVIDIA 驱动；无 GPU 时代码将在 CPU 上运行。请确保 Real-ESRGAN 权重文件存在于 `models/` 中并使用期望的文件名，或在 `utils/ImageProcessing.py` 中更新路径以指向你的权重文件。

## 🛠️ 配置

机器人从环境变量读取配置。两个必需变量为 `DISCORD_TOKEN`（机器人令牌）和 `POSTGRE_CONN_STRING`（PostgreSQL DSN）。在开发时可使用 `python-dotenv` 自动加载 `.env` 文件。若需自定义行为，可编辑相应模块来调整运行时参数（路径、瓦片大小、轮询间隔等）。

## 🧾 模型

默认情况下，代码期望两个模型文件存在于仓库根目录的 `models/` 文件夹：
- `RealESRGAN_x4plus.pth`（一般照片）
- `RealESRGAN_x4plus_anime_6B.pth`（动漫/插画）

对于非常大的图像，Worker 会自动选择瓦片（tiled）处理模式以降低显存压力。

## ▶️ 本地运行

运行 Worker：`python worker.py`，开始轮询队列并执行放大任务。运行 Bot：`python bot.py`，注册 `/upscale` 斜杠命令并运行交付循环。在邀请了机器人服务器中使用 `/upscale`，上传图像附件并选择模型类型。该命令会确认一个排队的任务 ID；Worker 会处理图像并将输出保存到 `output/`；Bot 随后会把放大后的图像发布回原始频道并删除本地文件。请确保你的设备能够运行模型，推荐配备支持 CUDA 且显存充足（建议 4GB+）的 GPU。

或者如果你想省去这些步骤，可以使用仓库根目录提供的批处理文件： [Batch File Link](https://github.com/Dendroculus/discord-image-upscaler-bot/blob/main/start_upscaler.bat)

## 🗂️ 命令

唯一对用户的命令是 `/upscale`，接受一个 `image` 附件以及在 “General Photo” 与 “Anime / Illustration” 之间的 `type` 选项。该命令会验证文件类型、将任务入队，并回复任务编号；处理完成后结果会发布回相同频道。

## 🛠 构建于

Bot 部分使用 Python 与 discord.py 构建。Real-ESRGAN（基于 basicsr 的 RRDBNet）与 PyTorch 负责放大处理——代码在可用时会使用 GPU（并在支持时使用 FP16 来节省显存）。OpenCV 与 NumPy 处理图像 I/O，requests 下载附件，asyncpg 在 PostgreSQL 中存储任务，python-dotenv 在开发时加载本地配置。生产环境建议使用 Docker、systemd 或 Kubernetes 将 Bot 与 Worker 作为独立进程运行。

## 🤝 贡献

欢迎贡献！请阅读 [CONTRIBUTINGcn.md](CONTRIBUTINGcn.md) 以了解贡献流程与行为准则。提交 PR 时，请在适用位置包含测试并在说明中简要描述更改内容。

## 📜 许可证

本项目采用 MIT 许可证。有关包含模型的完整条款和任何归属要求，请参阅 `LICENSE` 文件。

## 🙏 致谢

- **Real-ESRGAN** 提供放大模型与研究成果。
- **discord.py** 提供机器人框架。

## ✉️ 联系方式

如遇错误或有新功能请求，请提交 Issue；若需要部署或扩展方面的帮助，请发起 Discussion。