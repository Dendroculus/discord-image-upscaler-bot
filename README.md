<div align="center">

  EN | [中文](./docs/readmeCN.md)
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

# ✨ Discord Image Upscaler Bot 

</div>

Discord Image Upscaler Bot is a simple, reliable tool that accepts image attachments via a slash command, enqueues AI upscaling jobs in PostgreSQL, processes them with Real-ESRGAN in a separate worker, and returns the upscaled image to the original channel while cleaning up local files. It is built with Python and discord.py and designed to be run as two cooperating processes so the bot remains responsive while the heavy lifting runs on CPU/GPU in a worker.

## 🎥 Demo

| Original (Low Res) | Real-ESRGAN Upscaled (4x) |
| :---: | :---: |
| <img src="https://github.com/Dendroculus/discord-image-upscaler-bot/blob/main/assets/previews/ado.jpg" width="300"> | <img src="https://github.com/Dendroculus/discord-image-upscaler-bot/blob/main/assets/previews/ado_upscaled.png" width="300"> |

<details>
  <summary><b>🎥 Click to watch the preview (20 s) </b></summary>

  <img src="https://github.com/Dendroculus/discord-image-upscaler-bot/blob/main/assets/previews/Preview.gif">
</details>  

## ✨ Key Features

- 🚀 400% AI Upscaling using `RealESRGAN_x4plus` and `RealESRGAN_x4plus_anime_6B`.
- ☁️ Cloud-native results uploaded to **Azure Blob Storage** with permanent CDN links.
- 🛡️ Crash-resilient with heartbeat and auto-recovery for stale jobs.
- 🔒 Concurrency-safe using PostgreSQL `FOR UPDATE SKIP LOCKED`.
- 🧠 Smart caching via a `ModelRegistry` to manage VRAM (dynamic load/unload).

## 🏗️ Architecture

<img src="https://github.com/Dendroculus/discord-image-upscaler-bot/blob/main/assets/ArchitectureDiagram.png">

## 📂 Project Structure

```bash
Discord-Image-Upscaler-Bot/
├── bot.py                     # Entry point for the Discord Bot (Producer)
├── worker.py                  # Entry point for the Background Worker (Consumer)
├── database.py                # Async Database Interface
├── .env                       # Secrets and configs
│
├── cogs/                      # Discord Slash Commands
│   └── UpScale.py
│
├── constants/                 # Static configurations
│   ├── configs.py             # Constant Values
│   ├── Emojis.py              # Emoji definitions
│   └── ModelRegistry.py       # Dynamic model loader
│
├── services/                  # External service adapters
│   ├── StorageService.py      # Azure Blob logic
│   └── NotificationService.py # Discord embed logic
│
├── utils/                     # Core utilities
│   └── ImageProcessing.py     # AI inference engine
│
└── models/                    # Pre-trained .pth weights
```

## 🚀 Quick start

Getting started should be straightforward even if you're new to Discord bots. First, clone the repository to your machine and open a terminal in that folder. Create a virtual environment and activate it (for example `python -m venv .venv` then `source .venv/bin/activate` on macOS/Linux or `.venv\Scripts\activate` on Windows). Install runtime dependencies with `pip install -r requirements.txt`. Create a `.env` file at the project root containing at least `DISCORD_TOKEN` and `POSTGRE_CONN_STRING` (example below). Download the Real-ESRGAN model weights and place them in a `models/` folder next to the code. When everything is in place, run the worker in one terminal with `python worker.py` so it can poll for jobs, and run the bot in another terminal with `python bot.py` so it can accept slash command requests and deliver completed images. If you want a quick copy-paste for `.env`, use this as a starting point:


### Here's a small snippet to set up the environment and install dependencies to help you started easily:
```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment in macOS / Linux
source .venv/bin/activate

# Activate the virtual environment in Windows (cmd / PowerShell)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

```env
DISCORD_TOKEN=your_token_here
POSTGRE_CONN_STRING=postgres://user:password@localhost:5432/upscaler
AZURE_CONNECTION_STRING=your_azure_connection_string_here
```

If something goes wrong, check the logs from both processes: the worker prints processing and model errors, and the bot prints delivery and permission errors.

## ⚙️ Prerequisites

This project requires Python 3.8+ and a PostgreSQL instance reachable by the worker and bot. For GPU acceleration you need a CUDA-capable GPU, a matching CUDA build of PyTorch and the proper NVIDIA drivers; without a GPU the code will run on CPU only. Make sure the Real-ESRGAN weight files are present in `models/` using the expected filenames or update `utils/ImageProcessing.py` to point to your files.

## 🛠️ Configuration

The bot reads configuration from environment variables. The two required variables are `DISCORD_TOKEN` for the bot token and `POSTGRE_CONN_STRING` for the PostgreSQL DSN. You can use `python-dotenv` in development to load a `.env` file automatically. Adjust other runtime parameters (paths, tile sizes, polling intervals) by editing the corresponding modules if you need custom behavior.

## 🧾 Models

The code expects two model files by default: `RealESRGAN_x4plus.pth` for general photos and `RealESRGAN_x4plus_anime_6B.pth` for anime/illustration upscaling. Put those files into a `models/` directory at the repository root. The worker chooses a tiled processing mode automatically for very large images to reduce memory pressure.

## ▶️ Running locally

Start the worker with `python worker.py` to begin polling for queued jobs and performing upscales. Start the bot with `python bot.py` to register the `/upscale` slash command and run the delivery loop. Use `/upscale` in a server where the bot is invited; upload an image attachment and choose the model type. The command will confirm a queued job ID and the worker will process the image and save the output into `output/`; the bot will then post the upscaled image into the originating channel and remove the local file. Make sure your device is capable of running the models, ideally with a CUDA-capable GPU and sufficient VRAM (4GB+ recommended).

Or if you want to quit that hassle, you can use the batch files provided in the repository root : [Batch File Link ](https://github.com/Dendroculus/discord-image-upscaler-bot/blob/main/start_upscaler.bat)

## 🗂️ Commands

The only user-facing command is `/upscale` which accepts an `image` attachment and a `type` choice between "General Photo" and "Anime / Illustration". The command validates the file type, enqueues a job, and replies with a job number; results are posted back to the same channel once processing completes.

## 🛠 Built With

Built with Python and discord.py for the bot. Real-ESRGAN (using basicsr's RRDBNet) and PyTorch handle the upscaling — the code will use your GPU when available (and FP16 to save memory where supported). OpenCV and NumPy handle image I/O, requests downloads attachments, asyncpg stores jobs in PostgreSQL, and python-dotenv loads local config during development. For production, run the bot and worker as separate processes using Docker, systemd, or Kubernetes.

## 🤝 Contributing

Contributions are welcome! Please read `CONTRIBUTING.md` for the contribution process and code of conduct. When opening PRs, include tests where applicable and a short description of the change.

## 📜 License

This project is licensed under the MIT License. See the `LICENSE` file for full terms and any attribution requirements for included models.

## 🙏 Acknowledgements

- **Real-ESRGAN** for the upscaling models and research.
- **discord.py** for the bot framework.

## ✉️ Contact

Open an issue for bugs or feature requests, or start a discussion if you want help with deployment or extensions.
