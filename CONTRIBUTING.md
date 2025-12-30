# Contributing to Discord Image Upscaler Bot

<a id="en-intro"></a>

Thanks for your interest in contributing! This document explains how to get the project running locally, the development workflow we prefer, and how to submit improvements (bug fixes, new features, docs, tests, translations, etc.). Please read it before opening issues or submitting pull requests.

## Table of contents
- [What we look for](#en-what-we-look-for)
- [Getting the code](#en-getting-the-code)
- [Local development (quick start)](#en-local-development-quick-start)
- [Environment & required assets](#en-environment--required-assets)
- [Coding style & tests](#en-coding-style--tests)
- [Making changes](#en-making-changes)
- [Submitting an issue](#en-submitting-an-issue)
- [Submitting a pull request](#en-submitting-a-pull-request)
- [Adding / updating models](#en-adding--updating-models)
- [Security & sensitive data](#en-security--sensitive-data)
- [Community & conduct](#en-community--conduct)

---

<a id="en-what-we-look-for"></a>
## What we look for
Contributions that:
- Fix bugs or crashes
- Improve stability, performance, or UX
- Add tests or documentation
- Add useful developer tooling (linters, CI, scripts)
- Improve model handling, caching, or resource safety

We welcome all contributors — big or small. Keep changes focused and well-documented.

---

<a id="en-getting-the-code"></a>
## Getting the code
1. Fork the repo on GitHub.
2. Clone your fork locally:
   git clone https://github.com/Dendroculus/discord-image-upscaler-bot
3. Create a feature branch from `main`:
   git checkout -b feat/meaningful-name

---

<a id="en-local-development-quick-start"></a>
## Local development (quick start)
This project is designed to run as two cooperative processes:
- `bot.py` — the Discord bot (producer)
- `worker.py` — background upscaling worker (consumer)

Recommended Python: 3.8+

1. Create and activate a virtual environment:
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

2. Install requirements:
   pip install -r requirements.txt

3. Populate a `.env` file in the project root (see next section).

4. Download Real-ESRGAN weights and place them under `models/` (see "Environment & required assets").

5. Start processes (in separate terminals):
   python worker.py
   python bot.py

---

<a id="en-environment--required-assets"></a>
## Environment & required assets
Create a `.env` file with at least:
- DISCORD_TOKEN — your bot token
- POSTGRE_CONN_STRING — PostgreSQL DSN (e.g. postgres://user:pass@host:5432/db)
- AZURE_CONNECTION_STRING — for Azure uploads (if used)

Example `.env` snippet:
```env
DISCORD_TOKEN=your_token_here
POSTGRE_CONN_STRING=postgres://user:password@localhost:5432/upscaler
AZURE_CONNECTION_STRING=your_azure_connection_string_here
```

Model weights (put in `models/`):
- `RealESRGAN_x4plus.pth` (general)
- `RealESRGAN_x4plus_anime_6B.pth` (anime)
If you use different filenames, update `constants/ModelRegistry.py`.

Database:
- Ensure PostgreSQL is reachable. `worker.py` and `bot.py` will create the required table if missing.

---

<a id="en-coding-style--tests"></a>
## Coding style & tests
Please keep changes consistent and clean.

- Formatting: Use `black` and `isort`.
- Linting: `flake8` or similar is recommended.
- Type hints: Add or preserve type hints where possible.
- Docstrings: Keep public functions/classes documented.

Suggested pre-commit hooks:
- black
- isort
- flake8

Tests:
- Add tests with `pytest` where practical. If you add code, include unit tests for the most important logic.
- Run tests locally:
  pytest

If you add heavy GPU testing (model inference), consider marking tests as slow and document hardware needs.

---

<a id="en-making-changes"></a>
## Making changes
- Make small, focused PRs.
- Rebase/squash commits for a clean history if requested.
- Ensure your branch passes formatting and lint checks.

Files you may need to touch frequently:
- `database.py` — DB queue logic
- `worker.py` — job lifecycle
- `bot.py` / `cogs/UpScale.py` — commands and interaction flows
- `utils/ImageProcessing.py` — inference and resource handling
- `constants/ModelRegistry.py` — model file locations and names

If you change environment variable names, update README and `.env` examples.

---

<a id="en-submitting-an-issue"></a>
## Submitting an issue
When opening an issue, include:
- Clear title and short summary
- Steps to reproduce (commands, inputs, environment)
- Expected vs actual behavior
- Logs or stack traces (redact secrets)
- OS / Python version / GPU (if relevant)
- Attach sample images if appropriate (and allowed)

Label the issue as `bug`, `enhancement`, or `question` when relevant.

---

<a id="en-submitting-a-pull-request"></a>
## Submitting a pull request
1. Fork, branch, and implement your change.
2. Ensure tests and linters pass.
3. Push your branch and open a PR against `main` with a descriptive title.
4. In the PR description:
   - Explain the problem and your solution
   - Include before/after behavior and relevant logs
   - List any environment or model changes required
   - Mention related issues (e.g., fixes #123)

PR checklist:
- [ ] Changes are atomic and isolated to the purpose stated
- [ ] Code formatted (black) and imports sorted (isort)
- [ ] Type hints and docstrings added where applicable
- [ ] Unit tests added/updated
- [ ] README or CONTRIBUTING updated if public behavior changed

---

<a id="en-adding--updating-models"></a>
## Adding / updating models
If you add or rename model files:
- Update `constants/ModelRegistry.py` and any docs.
- Ensure inference code loads models lazily and eviction behavior is considered to avoid VRAM OOMs.
- Test on both CPU and CUDA (if possible).

---

<a id="en-security--sensitive-data"></a>
## Security & sensitive data
- Never commit `.env` or secrets to the repo.
- If you discover a security vulnerability (e.g., token leak), please responsibly disclose it by opening a private issue or contacting a repo maintainer instead of posting details publicly.

---

<a id="en-community--conduct"></a>
## Community & conduct
Be respectful and constructive. We encourage collaboration and civil discussion. If you don't already have one, consider adding a `CODE_OF_CONDUCT.md` to clarify expectations for community behavior.

---
