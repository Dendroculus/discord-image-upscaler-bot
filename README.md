<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9.4-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/discord.py-v2.x-7289DA.svg?logo=discord&logoColor=white" alt="discord.py">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT">
  <img src="https://img.shields.io/badge/status-Active-green.svg" alt="Update Status">
  <img src="https://img.shields.io/badge/Azure%20Blob%20Storage-Storage-0078D4.svg?logo=microsoftazure&logoColor=white" alt="Azure Blob Storage">
</p>

<div align="center">

# ✨ Discord Image Upscaler Bot 

</div>

Discord Image Upscaler Bot is a simple, reliable tool that accepts image attachments via a slash command, enqueues AI upscaling jobs in PostgreSQL, processes them with Real-ESRGAN in a separate worker, and returns the upscaled image to the original channel while cleaning up local files. It is built with Python and discord.py and designed to be run as two cooperating processes so the bot remains responsive while the heavy lifting runs on CPU/GPU in a worker.

## 🔍 What it does

The bot exposes a single slash command that takes an image and a model type choice, validates the input, and writes a job record to a database. A separate worker process polls the database, downloads the image, runs the Real-ESRGAN upscaler, writes the resulting file to an output directory, and updates job status. The bot monitors completed jobs and posts results back into the channel that requested the job, then deletes the local file to avoid disk accumulation.

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
```

If something goes wrong, check the logs from both processes: the worker prints processing and model errors, and the bot prints delivery and permission errors.

## ⚙️ Prerequisites

This project requires Python 3.8+ and a PostgreSQL instance reachable by the worker and bot. For GPU acceleration you need a CUDA-capable GPU, a matching CUDA build of PyTorch and the proper NVIDIA drivers; without a GPU the code will run on CPU only. Make sure the Real-ESRGAN weight files are present in `models/` using the expected filenames or update `utils/ImageProcessing.py` to point to your files.

## 🛠️ Configuration

The bot reads configuration from environment variables. The two required variables are `DISCORD_TOKEN` for the bot token and `POSTGRE_CONN_STRING` for the PostgreSQL DSN. You can use `python-dotenv` in development to load a `.env` file automatically. Adjust other runtime parameters (paths, tile sizes, polling intervals) by editing the corresponding modules if you need custom behavior.

## 🧾 Models

The code expects two model files by default: `RealESRGAN_x4plus.pth` for general photos and `RealESRGAN_x4plus_anime_6B.pth` for anime/illustration upscaling. Put those files into a `models/` directory at the repository root. The worker chooses a tiled processing mode automatically for very large images to reduce memory pressure.

## ▶️ Running locally

Start the worker with `python worker.py` to begin polling for queued jobs and performing upscales. Start the bot with `python bot.py` to register the `/upscale` slash command and run the delivery loop. Use `/upscale` in a server where the bot is invited; upload an image attachment and choose the model type. The command will confirm a queued job ID and the worker will process the image and save the output into `output/`; the bot will then post the upscaled image into the originating channel and remove the local file.

Or if you want to quit that hassle, you can use the batch files provided in the repository root : [Batch File Link ](https://github.com/Dendroculus/discord-image-upscaler-bot/blob/main/start_upscaler.bat)
## ☁️ Deployment tips

Run the bot and worker as separate services so heavy processing does not block command handling. For small deployments, a Docker Compose setup with two services and a shared `models/` and `output/` volume is convenient. For production, consider separate systemd units, Docker containers orchestrated by a process manager, or Kubernetes Deployments with GPU node selection. A managed PostgreSQL instance reduces operational overhead. Monitor disk usage and prune old entries/output files if you expect high throughput.

## 🗂️ Commands

The only user-facing command is `/upscale` which accepts an `image` attachment and a `type` choice between "General Photo" and "Anime / Illustration". The command validates the file type, enqueues a job, and replies with a job number; results are posted back to the same channel once processing completes.

## 🧩 Development & structure

Core files:
- `bot.py`: Discord integration, command handling, and database interaction.
- `worker.py`: The main processing loop that polls the database, runs the AI engine, and manages Azure uploads.
- `database.py`: Asyncpg-backed persistence for job queues.
- `cogs/UpScale.py`: Discord slash command definition and handling.
- `loggers/BotLogger.py`: Centralized logging configuration using `rich` for beautiful console output and `TimedRotatingFileHandler` for daily log files.
- `utils/ImageProcessing.py`: Real-ESRGAN integration for image upscaling.
- `utils/Deliverer.py`: Handles uploading processed results to Azure Blob Storage and sending links back to Discord.
- `utils/PatchFix.py`: Compatibility shims for torchvision.

### 📂 Project Structure
```text
Discord-Image-Upscaler-Bot/
├── cogs/               # Discord command modules
├── loggers/            # Logging configuration (BotLogger.py)
├── logs/               # Auto-generated log files
│   ├── bot_logs/       # Discord bot logs (rotated daily)
│   └── worker_logs/    # AI worker logs (rotated daily)
├── models/             # Place .pth model files here
├── utils/              # Helper scripts (Deliverer, ImageProcessing)
├── bot.py              # Main Bot entry point
├── worker.py           # Background AI worker
└── start_upscaler.bat  # Launcher script

## 🛠 Built With

Built with Python and discord.py for the bot. Real-ESRGAN (using basicsr's RRDBNet) and PyTorch handle the upscaling — the code will use your GPU when available (and FP16 to save memory where supported). OpenCV and NumPy handle image I/O, requests downloads attachments, asyncpg stores jobs in PostgreSQL, and python-dotenv loads local config during development. For production, run the bot and worker as separate processes using Docker, systemd, or Kubernetes.

## 🤝 Contributing

Fork the repository, create a focused branch, and open a pull request describing your change. Smaller, well-tested changes are easier to review. Keep database migrations minimal and backward compatible when possible.

## 📜 License

This project is licensed under the MIT License. See the `LICENSE` file for full terms and any attribution requirements for included models.

## 🙏 Acknowledgements

Thanks to Real-ESRGAN and its contributors for the upscaling models, to basicsr and PyTorch for the model and runtime primitives, and to the open source community for the libraries and examples that made this project possible.

## ✉️ Contact

Open an issue for bugs or feature requests, or start a discussion if you want help with deployment or extensions.

built with ⚒️ Python · discord.py · Real-ESRGAN · PyTorch · basicsr · OpenCV · NumPy · requests · asyncpg · python-dotenv · Docker / systemd / Kubernetes