# LangChain / LangGraph 学习项目

使用 Python 3.12 和 uv，围绕八周路线逐步学习 Agent 工作流、RAG、MCP、多智能体、评估、人工介入与部署。

教学方式、常用 API 清单与阶段验收标准见 [AGENTS.md](AGENTS.md)。当前仅配置核心依赖与学习环境，尚未选择模型供应商。

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

## 常用命令

```powershell
# 查看已安装的框架版本，不需要模型凭据
uv run python -c "from importlib.metadata import version; print('langchain', version('langchain')); print('langgraph', version('langgraph'))"

# 运行后续创建的练习脚本，将路径替换为实际文件
uv run python path\to\lesson.py

# 按课程需要添加依赖，例如数据验证库
uv add pydantic

# 查看仓库状态
git status
```

模型调用需要相应供应商适配包、凭据和可用模型名称，后续课程按实际服务配置。图结构、提示词模板和本地工具等练习可以先离线运行。

## Git 与本地文件

仓库以 `main` 为初始分支。`AGENTS.md`、README、`.python-version`、`pyproject.toml` 和 `uv.lock` 应纳入版本控制。虚拟环境、凭据与本地数据库由 `.gitignore` 排除。

初始化不创建首次提交或远程仓库。需要保存一个学习节点时再按用户要求提交。

## 官方资料

- [uv 项目管理](https://docs.astral.sh/uv/guides/projects/)
- [LangChain 模型接口](https://docs.langchain.com/oss/python/langchain/models)
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
