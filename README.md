# LangChain / LangGraph 学习项目

使用 Python 3.12 和 uv，围绕八周路线逐步学习 Agent 工作流、RAG、MCP、多智能体、评估、人工介入与部署。

教学方式、常用 API 清单与阶段验收标准见 [AGENTS.md](AGENTS.md)。模型信息已保存在根目录 `.env`，第 05 课已安装适配包并验证现有服务的文本、流式、批量、管道及异步调用。

初始验证环境：Python 3.12.13、LangChain 1.4.6、LangGraph 1.2.16。依赖更新后以 `uv.lock` 和实际查询结果为准。

## 环境准备

以下命令适用于项目根目录中的 PowerShell：

```powershell
uv python install 3.12
uv sync --locked
uv run python --version
```

`.python-version` 选择 Python 3.12，`pyproject.toml` 限制为 3.12 系列，`uv.lock` 锁定依赖版本。项目环境位于 `.venv`，`uv run` 会自动使用它，无需手动激活。

在 IDE 中选择 `.venv\Scripts\python.exe` 作为项目解释器。

## 怎么开始学习

先看 [教学组织与目录约定](docs/teaching-workflow.md)，再从 [课程索引](docs/lessons/README.md) 找到当前课。导师使用 [讲义模板](docs/lesson-template.md) 逐课备课。

新会话先看 [当前进度](docs/progress.md)，无需通读详细日志。当前在第 05 课管道练习查验阶段，待确认点与下一步以进度文件为准。首次学习从 [第 01 课](docs/lessons/01_state_node_edge.md) 开始，前四课均无需模型。

每课按“讲义初稿 → 导师示例与练习骨架 → 运行验证并完善讲义 → 学习者练习 → 讲评与记录”推进。讲义覆盖具体 API 的用法、预期输出、实际效果、限制和验收方式。

| 你要做的事 | 到哪里找 |
| --- | --- |
| 阅读每课讲义 | `docs/lessons/` |
| 运行导师示例 | `examples/<课号_主题>/demo.py` |
| 编写自己的练习 | `exercises/<课号_主题>/exercise.py` |
| 讲评时查看参考解答 | `solutions/<课号_主题>/solution.py` |
| 查看当前学习进度 | `docs/progress.md` |
| 按需追溯详细过程 | `docs/learning-log.md` |
| 后续开发完整项目 | `src/agent_learning/` |

第 01～05 课讲义、导师示例与练习已创建，后续课程逐课准备。第 05 课示例和练习已改为独立读取 `.env`，当前 14 项测试及独立练习的离线检查通过。学习者的当前验收状态与待巩固项见 [当前进度](docs/progress.md)，示例运行成功不代表学习者已验收。

## 常用命令

```powershell
# 查看已安装的框架版本，不需要模型凭据
uv run python -c "from importlib.metadata import version; print('langchain', version('langchain')); print('langgraph', version('langgraph'))"

# 运行第一课离线示例
uv run python examples/01_state_node_edge/demo.py

# 运行已完成的第一课练习
uv run python exercises/01_state_node_edge/exercise.py

# 比较第二课的默认覆盖与列表累积
uv run python examples/02_state_reducers/demo.py

# 运行第二课列表累积练习
uv run python exercises/02_state_reducers/exercise.py

# 第三课：模拟最多三次检索，并观察两种图状态流
uv run python examples/03_routing_loops/demo.py

# 运行第三课路由练习
uv run python exercises/03_routing_loops/exercise.py

# 第四课：格式化包含历史的消息模板，不调用模型
uv run python examples/04_prompt_messages/demo.py

# 理解模板后再观察消息 ID 的新增与更正
uv run python examples/04_prompt_messages/demo_message_state.py

# 第四课练习：模板代码已查验，消息状态与独立解释仍待确认
uv run python exercises/04_prompt_messages/exercise.py

# 第五课：先只检查配置，再发送一次真实模型请求
uv run python examples/05_model_calls/demo.py --mode check
uv run python examples/05_model_calls/demo.py

# 第五课练习：只补全管道组合，初态不发送请求
uv run python exercises/05_model_calls/exercise.py

# 离线检查路由、状态流、消息更新、模型配置与空响应；不代替学习者练习验收
uv run python -m unittest discover -s tests -p "test_*.py" -v

# 按课程需要添加依赖，例如数据验证库
uv add pydantic

# 查看仓库状态
git status
```

## 模型配置

你已配置的 `.env` 包含 `LLM_PROVIDER`、`LLM_MODEL`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_TIMEOUT_SECONDS`。格式示例见 [.env.example](.env.example)，保留自己的实际值。

当前 `openai_compatible` 标记在代码中映射为 LangChain 的 `openai` 适配器，并显式传入模型名、密钥、地址和超时。第 05 课已添加 `langchain-openai>=1.7.2`，使用 `uv sync --locked` 复现；`uv.lock` 记录本次安装时使用的 PyPI 镜像来源。

模型课程的命令统一为以下形式，路径替换为该课实际文件：

```powershell
uv run python path/to/model_lesson.py
```

每份模型示例与练习都独立使用 `dotenv_values` 直接读取根目录 `.env`，模型初始化写在当前文件中；不依赖 `--env-file`、其他示例文件或进程重启。`python-dotenv` 已纳入项目依赖。[官方说明](https://bbc2.github.io/python-dotenv/)

图结构、提示词模板和本地工具练习无需模型服务。真实调用、工具调用能力和结构化输出能力分别验证，不能仅凭配置齐全就视为已可用。

## Git 与本地文件

仓库以 `main` 为初始分支。`AGENTS.md`、README、`.python-version`、`pyproject.toml` 和 `uv.lock` 应纳入版本控制。虚拟环境、凭据与本地数据库由 `.gitignore` 排除。

初始化不创建首次提交或远程仓库。需要保存一个学习节点时再按用户要求提交。

## 官方资料

- [uv 项目管理](https://docs.astral.sh/uv/guides/projects/)
- [LangChain 模型接口](https://docs.langchain.com/oss/python/langchain/models)
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
