# 参与 Discord Image Upscaler Bot 的贡献

<a id="zh-intro"></a>

感谢您有兴趣为本项目做出贡献！本文档将说明如何在本地运行项目、我们要的首选开发工作流，以及如何提交改进（错误修复、新功能、文档、测试、翻译等）。在开启 Issue 或提交 Pull Request 之前，请务必阅读本文档。

## 目录
- [我们期待的贡献](#zh-we-need)
- [获取代码](#zh-getting-code)
- [本地开发（快速开始）](#zh-local-dev)
- [环境与必要资源](#zh-env)
- [代码风格与测试](#zh-style-tests)
- [进行修改](#zh-making-changes)
- [提交 Issue](#zh-submitting-issue)
- [提交 Pull Request](#zh-submitting-pr)
- [添加 / 更新模型](#zh-models)
- [安全与敏感数据](#zh-security)
- [社区与行为准则](#zh-conduct)

---

<a id="zh-we-need"></a>
## 我们期待的贡献
我们需要以下类型的贡献：

- 修复 Bug 或崩溃
- 提升稳定性、性能或用户体验 (UX)
- 添加测试或文档
- 添加有用的开发工具（Linters、CI、脚本）
- 改进模型处理、缓存或资源安全性

我们欢迎所有的贡献者——无论贡献大小。请保持更改专注并提供良好的文档。

---

<a id="zh-getting-code"></a>
## 获取代码
1. 在 GitHub 上 Fork 本仓库。
2. 将您的 Fork 克隆到本地：
   git clone https://github.com/Dendroculus/discord-image-upscaler-bot
3. 从 main 分支创建一个功能分支：
   git checkout -b feat/meaningful-name

---

<a id="zh-local-dev"></a>
## 本地开发（快速开始）
本项目设计为两个相互协作的进程运行：

- `bot.py` — Discord 机器人（生产者）
- `worker.py` — 后台放大工作进程（消费者）

推荐 Python 版本：3.8+

创建并激活虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

准备好 `.env`（见下一节），并下载 Real-ESRGAN 模型权重到 `models/` 目录后，在不同终端分别运行：

```bash
python worker.py
python bot.py
```

---

<a id="zh-env"></a>
## 环境与必要资源
创建一个 `.env` 文件，至少包含以下内容：

- DISCORD_TOKEN — 您的机器人 Token
- POSTGRE_CONN_STRING — PostgreSQL 连接字符串 (DSN)
- AZURE_CONNECTION_STRING — 用于 Azure 上传（如果使用）

示例 `.env`：

```env
DISCORD_TOKEN=your_token_here
POSTGRE_CONN_STRING=postgres://user:password@localhost:5432/upscaler
AZURE_CONNECTION_STRING=your_azure_connection_string_here
```

模型权重（放入 `models/`）：

- `RealESRGAN_x4plus.pth` (通用)
- `RealESRGAN_x4plus_anime_6B.pth` (动漫)

如果您使用不同的文件名，请更新 `constants/ModelRegistry.py`。

数据库：确保 PostgreSQL 可访问；`worker.py` / `bot.py` 会在首次运行时自动创建缺失表。

---

<a id="zh-style-tests"></a>
## 代码风格与测试
请保持更改的一致性和整洁。

- 格式化：使用 `black` 和 `isort`
- 代码检查：`flake8` 或 `ruff`
- 类型提示：尽量补充或保留类型注解
- 文档字符串：为公共函数/类添加 docstring

建议 pre-commit 钩子（可选）：
- black
- isort
- flake8 / ruff

测试：
- 使用 `pytest` 编写单元测试
- 将慢或需要 GPU 的测试标记（例如 `@pytest.mark.slow`）
- 本地运行： pytest

---

<a id="zh-making-changes"></a>
## 进行修改
- 提交小而专注的 PR
- 被要求时进行 rebase 或 squash 以保持提交历史整洁
- 确保通过格式化和 Lint 检查

常改动文件示例：
- `database.py`
- `worker.py`
- `bot.py` / `cogs/UpScale.py`
- `utils/ImageProcessing.py`
- `constants/ModelRegistry.py`

如更改环境变量名称，请同时更新 `README.md` 与本文件。

---

<a id="zh-submitting-issue"></a>
## 提交 Issue
在开启 Issue 时，请包含：
- 清晰的标题与摘要
- 复现步骤（命令、输入、配置）
- 期望行为与实际行为
- 日志或堆栈（隐去密钥）
- OS / Python 版本 / GPU（如相关）
- 示例图片（如适用）

并在适当时标记为 `bug`、`enhancement` 或 `question`。

---

<a id="zh-submitting-pr"></a>
## 提交 Pull Request
步骤：
1. Fork 并创建功能分支
2. 实现更改并运行测试与格式化工具
3. 推送分支并针对 `main` 提交 PR

在 PR 描述中：
- 说明问题与解决方案
- 提供修改前/后的行为对比
- 列出所需的环境或模型更改
- 关联 Issue（例如 fixes #123）

PR 检查清单：
- [ ] 更改原子且聚焦
- [ ] 代码已格式化（black）且导入已排序（isort）
- [ ] 添加或更新类型注解与 docstring（如适用）
- [ ] 为重要逻辑添加单元测试
- [ ] 更新 README 或 CONTRIBUTING（若公共行为更改）

---

<a id="zh-models"></a>
## 添加 / 更新模型
如添加或重命名模型权重文件：
- 更新 `constants/ModelRegistry.py`
- 确保推理代码懒加载模型并考虑显存驱逐策略
- 在 CPU 与 CUDA 上尽可能验证模型
- 在 PR 中说明模型来源与许可（如适用）

---

<a id="zh-security"></a>
## 安全与敏感数据
- 切勿将 `.env`、凭证或密钥提交到仓库
- 发现安全问题时，请通过私有渠道负责任地披露
- 如果误提交密钥，请立即撤销并清理提交历史，通知维护者

---

<a id="zh-conduct"></a>
## 社区与行为准则
请友好且尊重地交流。鼓励建设性讨论。如尚未加入，请考虑添加 `CODE_OF_CONDUCT.md` 来明确社区行为规范。

---

非常感谢您的贡献！如果您需要，我可以为您在仓库中创建一个包含本文件的 PR（需要目标分支信息）。欢迎提出改进或翻译校正建议。