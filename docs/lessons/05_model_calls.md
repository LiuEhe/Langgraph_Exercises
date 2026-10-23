# 第 05 课：从消息模板到真实模型输入输出

> 备课状态：可学习（2026-10-23，真实模型各模式此前已验证；当前直接读取配置、独立练习离线检查与全套 14 项测试通过；关闭思考参数尚未发送请求验证）。根据当前进度衔接第 04 课，继续第一阶段。导师验证与学习者验收分开记录。

## 本课目标与场景

上一课能把“系统规则、历史消息、当前问题”组织好，但没有生成新回答。本课把“请用一句话解释 State”发送给现有配置中的真实模型，观察返回值，并用同一输入理解不同调用方式。

核心目标：能解释 `变量字典 → ChatPromptValue → 模型 → AIMessage → 文本` 的数据变化，并独立把模板、模型和输出解析器组合起来。

工具调用、结构化输出、Agent 循环留到后课。这里是固定执行顺序的模型调用；模型没有决定下一步的权限。本课不需要 LangGraph，普通 Python 顺序调用即可。

## 前置知识与运行条件

- 已有证据：第 04 课模板练习经反馈修正后查验通过；消息 ID 更新和独立解释仍待验收，不因本课备课自动补记为掌握。
- 能阅读消息列表、字典、函数、`for` 循环；异步（asynchronous）作为补充阅读。
- 实测环境：Python 3.12.13、LangChain 1.4.6、langchain-core 1.6.12、LangGraph 1.2.16、langchain-openai 1.7.2、openai 3.37.0。
- 新增依赖：`uv add langchain-openai` 连接现有兼容服务；`uv add python-dotenv` 用于在当前脚本直接读取 `.env`。当前 python-dotenv 为 1.2.4，不安装到系统 Python。
- 根目录已有 `.env`，只在命令中显式加载，不复制或覆盖。协议兼容不保证流式、工具调用等能力全部支持。

## 文件位置与运行命令

配套文件已创建，所有命令从项目根目录执行：

| 类型 | 位置 |
| --- | --- |
| [导师示例](../../examples/05_model_calls/demo.py) | `examples/05_model_calls/demo.py` |
| [学习者练习](../../exercises/05_model_calls/exercise.py) | `exercises/05_model_calls/exercise.py` |
| [配置与空响应测试](../../tests/test_05_model_config.py) | `tests/test_05_model_config.py` |

```powershell
# 安装或复现环境：首次引入适配包由导师执行 uv add，之后使用锁文件
uv sync --locked

# 只校验配置和构造模型对象，不发送请求
uv run python examples/05_model_calls/demo.py --mode check

# 默认 invoke：一次真实请求
uv run python examples/05_model_calls/demo.py

# 按需要逐个运行，不会由默认命令自动全部调用
uv run python examples/05_model_calls/demo.py --mode stream
uv run python examples/05_model_calls/demo.py --mode batch
uv run python examples/05_model_calls/demo.py --mode chain
uv run python examples/05_model_calls/demo.py --mode async

# 练习只要求完成一道管道组合任务；初态应提示尚未实现
uv run python exercises/05_model_calls/exercise.py
```

当前示例和练习各自直接读取根目录 `.env`，无需 `--env-file`。不重启脚本，不动态加载其他教学脚本。检查配置、构造模型和构造管道均不生成回答。

```python
from pathlib import Path
from dotenv import dotenv_values

env_path = Path(__file__).resolve().parents[2] / ".env"
config = dotenv_values(env_path)
```

`dotenv_values` 从 `dotenv` 导入，所属依赖是 `python-dotenv`。输入是文件路径，返回键值映射，例如 `config["LLM_PROVIDER"]` 为 `"openai_compatible"`；不修改 `os.environ`，也不请求模型。这里的 `Path(...).parents[2]` 从脚本位置定位项目根目录。缺少文件时配置映射为空，本课会据此提示缺少哪些配置；不要打印整个映射，以免显示凭据。默认以 UTF-8 读取，支持 `.env` 的引号和注释，详见 [python-dotenv 官方文档](https://bbc2.github.io/python-dotenv/)。

## 先看数据与执行顺序

```text
.env → dotenv_values → 配置字典 ──显式映射──> ChatOpenAI 模型对象
                                 │
变量字典 → prompt.invoke → ChatPromptValue → model.invoke → AIMessage
                                                           │
                                                  parser.invoke → str
```

主示例不传历史：系统规则加当前问题共两条消息，便于隔离首次服务验证。后续要传历史时仍需显式提供，模型对象不会自动替你记住上次输入。

| 表达式 | 这一步做什么 | 返回什么 | 发送模型请求？ |
| --- | --- | --- | --- |
| `prompt.invoke({"concept": "State"})` | 替换模板变量 | `ChatPromptValue`，`.to_messages()` 是消息列表 | 否 |
| `init_chat_model(...)` | 构造供应商模型客户端 | 本课预期 `ChatOpenAI` | 否 |
| `model.invoke(prompt_value)` | 请求模型生成回答 | 预期 `AIMessage` | 是，一次 |
| `parser.invoke(response)` | 从已有消息提取文本 | 字符串；当前版本实测为 `str` 的子类 `TextAccessor` | 否 |
| `chain = prompt \| model \| parser` | 组合执行顺序 | `RunnableSequence` | 否 |
| `chain.invoke({"concept": "State"})` | 实际依次执行三步 | 字符串；当前版本实测为 `TextAccessor` | 是，一次 |

## 配置怎样变成模型参数

这些 `LLM_*` 名称属于本项目，LangChain 不会自行识别它们。

| 环境变量 | 显式传入的参数 | 本课检查 |
| --- | --- | --- |
| `LLM_PROVIDER` | `openai_compatible` 映射到 `model_provider="openai"` | 非空且匹配本课支持的标记 |
| `LLM_MODEL` | `model` | 非空，不在日志中打印实际值 |
| `LLM_API_KEY` | `api_key` | 非空，不在异常或示例输出中显示 |
| `LLM_BASE_URL` | `base_url` | 有效的 HTTP(S) 地址；不显示实际值 |
| `LLM_TIMEOUT_SECONDS` | `timeout` | 转为有限正浮点数，拒绝 `0`、负数、`nan`、`inf`、非数字 |

模型初始化的关键片段如下，完整配置校验位于导师示例：

```python
from pathlib import Path
from dotenv import dotenv_values
from langchain.chat_models import init_chat_model

# 下面假定值已通过示例中的校验，不单独运行这一片段。
config = dotenv_values(Path(__file__).resolve().parents[2] / ".env")
model = init_chat_model(
    model=config["LLM_MODEL"],
    model_provider="openai",
    api_key=config["LLM_API_KEY"],
    base_url=config["LLM_BASE_URL"],
    timeout=float(config["LLM_TIMEOUT_SECONDS"]),
    max_tokens=512,
    max_retries=0,
    use_responses_api=False,
    stream_usage=False,
    extra_body={"enable_thinking": False},
)
```

`init_chat_model` 是函数；调用后得到模型对象，再调用对象的 `invoke` 等方法。显式选择 `openai` 是选择适配实现，实际连接地址由 `base_url` 决定。直接 `from langchain_openai import ChatOpenAI` 构造也是可用方案；统一初始化入口适合保持上层接口一致，但不统一底层模型能力。

- `timeout` 控制客户端等待，不是输出长度，也不是整个脚本的硬性运行时间上限。
- `max_tokens=512` 限制每次生成预算，不等于 512 个汉字；部分推理模型的预算也可能消耗在推理上。适配包可能将它映射为 `max_completion_tokens`，须以实际服务支持为准。首次使用 128 的实测出现预算全部用于推理、正文为空，故本课调整到 512；这也不是所有模型通用的保证值。
- `max_retries=0` 关闭适配器自动重试，便于核对请求数量。失败时脚本退出，不悄悄换模型或无限重试。
- `use_responses_api=False` 显式使用兼容的 Chat Completions 路径；`stream_usage=False` 避免假定兼容服务支持流式用量扩展。后者不代表调用没有 token 消耗。
- 本课不指定 `temperature`，避免在首次接入时假定所有模型都接受该参数；不承诺确定性回答。
- 思考模式默认关闭：`extra_body={"enable_thinking": False}`。`extra_body` 将供应商的扩展参数传入请求，`False` 表示关闭当前 Qwen 接口的思考模式；这不是所有 OpenAI 兼容服务通用的参数。[官方说明](https://www.alibabacloud.com/help/zh/model-studio/deep-thinking)。此设置在先前实测后补入，尚未重新发送请求验证；下方耗时与 token 记录仍属于修改前的调用。

## 最小调用：输入消息，输出 AIMessage

```python
from langchain.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一名 LangGraph 导师。请用简体中文简短回答。"),
    ("human", "请用一句话解释 {concept}，不超过 40 个汉字。"),
])
prompt_value = prompt.invoke({"concept": "State"})
response = model.invoke(prompt_value)
print(type(response).__name__)
print(response.content)
```

这里复用前课模板接口：`from_messages` 返回模板，`prompt.invoke` 返回 `ChatPromptValue`。模型既可以接收此对象，也可以接收 `prompt_value.to_messages()` 得到的消息列表；本课主示例使用后者，便于打印输入角色。

`response` 预期为 `AIMessage`，不是字符串，也不是整个图状态。检查方式：

| 属性 | 当前输入下应怎样理解 |
| --- | --- |
| `.type` | 预期 `"ai"`，表示助手角色 |
| `.content` | 本次生成内容；本课预期为非空文本，但通用接口也允许内容块列表 |
| `.tool_calls` | 本课没有绑定工具，预期 `[]`；不能由此推断已验证工具能力 |
| `.usage_metadata` | 若服务返回标准用量，通常含 `input_tokens`、`output_tokens`、`total_tokens`；也可能为 `None` |
| `.response_metadata.get("finish_reason")` | 若服务提供，`stop` 表示正常结束，`length` 表示达到生成上限；没有该字段时不自行编造 |

与上一课手工构造的 `AIMessage(content="示例历史")` 相比，这里只有实际执行模型请求才产生新的服务返回。单凭对象类型无法证明来源；必须结合执行代码判断。

## 文本解析与管道组合

字符串输出解析器（StrOutputParser）解决“下游只接收文本”的问题。先用现有响应演示，不额外发送请求：

```python
from langchain_core.output_parsers import StrOutputParser

parser = StrOutputParser()             # 构造解析器，不调用模型
text = parser.invoke(response)         # 输入已有 AIMessage，输出 str
print(type(text).__name__)             # 当前安装版本实测 TextAccessor
print(isinstance(text, str))           # 实测 True，可以作为字符串使用
```

对于本课普通文本响应，`text` 实测与 `response.content` 相同。langchain-core 1.6.12 在此路径上返回 `TextAccessor`，它继承 `str`；不要用 `type(text) is str` 判断是否为字符串。该细节已用手工 `AIMessage(content="offline sample")` 离线验证，`isinstance(text, str)` 为 `True`，内容相等；无需为此另建观察脚本。

解析器不会核验事实、不会自动解析出业务字段，也不保留完整的消息 ID、工具请求和用量元数据。需要这些字段时保留原 `AIMessage`。若业务确实要求精确的内置 `str` 类型，可在下游显式 `str(text)`；本课练习接受 `str` 子类。

可运行对象（Runnable）提供一致的执行接口；`|` 在这些对象上组合成管道，不是立即发请求，也不是普通字符串的操作：

```python
chain = prompt | model | parser
text = chain.invoke({"concept": "Node"})
```

实测 `type(chain).__name__` 为 `RunnableSequence`，最终 `text` 为字符串子类 `TextAccessor`。输入字典先由模板消费，模型接收模板值，解析器接收模型消息；后一步拿到的是前一步返回值。手工分步调用更容易观察中间值，管道让重复组合更方便，不会因此提高模型回答质量。单独运行 `--mode chain` 会新发一次请求，不是在重复使用默认模式的回答。

## 流式输出：逐块观察一条回答

```python
for chunk in model.stream(messages):
    print(chunk.content, end="", flush=True)
```

`model.stream(messages)` 返回同步迭代器，遍历时生成消息块（AIMessageChunk），不是一次给出完整消息列表。一个块不一定等于一个 token；可能是空内容或元数据块。本课示例累计消息块后，再用解析器取出完整文本。

示例分别记录首块到达、首个非空文本块到达、全部完成三个时间。首块可能没有文字，所以三个指标含义不同。它们只表示这次客户端观察，不是服务稳定延迟，更不能与不同输入下的一次 `invoke` 直接比较性能。

第 03 课的 `graph.stream(..., stream_mode="updates")` 展示节点状态更新；这里的 `model.stream` 展示一次模型生成中的片段，属于不同层次。

## 批量与异步：改变调度，不改变回答标准

```python
inputs = [
    prompt.invoke({"concept": "State"}),
    prompt.invoke({"concept": "Node"}),
]
responses = model.batch(inputs, config={"max_concurrency": 2})
```

`batch` 接收多个独立输入，预期返回按输入顺序排列的 `list[AIMessage]`；本例长度为 `2`。这不是一段包含两个问题的共享对话，也不等于供应商的离线 Batch API。`max_concurrency=2` 限制并发执行数，不减少请求数或 token；默认失败会抛出异常，已有成功请求仍可能计费。先检查供应商的限流，再扩大规模。

```python
import asyncio

async def ask_once():
    response = await model.ainvoke(messages)
    return response

response = asyncio.run(ask_once())
```

`ainvoke` 是异步调用，必须在异步函数里 `await` 才得到 `AIMessage`；仅写 `model.ainvoke(messages)` 会得到尚未等待的协程。`asyncio.run` 在本课命令行脚本中创建并运行事件循环，返回 `ask_once` 的结果；已有事件循环的 Notebook 中应直接 `await ask_once()`。异步有助于同时等待其他任务，本课只请求一次，不能据此声称更快或回答更准。

完整脚本中，`BaseChatModel`（`langchain_core.language_models.chat_models`）和练习里的 `Runnable`（`langchain_core.runnables`）只用于类型标注：前者表示聊天模型接口，后者表示可组合执行的对象，不在本课手工实例化它们。`AIMessageChunk` 从 `langchain.messages` 导入，用于确认流式块类型；相加后仍是消息块，累计内容再交给解析器。

练习是完整独立的文件：`main()` 依次直接读取配置、调用 `init_chat_model`、调用你完成的 `build_chain`，最后执行 `chain.invoke`。所有步骤在当前文件内可见，不需要跳转到 `demo.py` 理解模型怎样构造；你的核心练习仍只有管道组合。

| 模式 | 生成请求数量（禁用重试） | 返回或观察结果 |
| --- | --- | --- |
| `check` | 0 | 模型对象类型、配置有效提示 |
| 默认 `invoke` | 1 | `AIMessage`，再本地解析出 `str` |
| `stream` | 1 | 消息块迭代，结束后得到累计文本 |
| `batch` | 2 | 两条独立的 `AIMessage` |
| `chain` | 1 | 管道最终输出 `str` |
| `async` | 1 | `await` 后得到 `AIMessage` |

## 预期输出与实测结果

2026-10-23 实际执行了上面的配置检查和各模式命令，初始 128 token 失败后调整为 512。以下是默认模式一次成功运行的实测摘录；生成文本是该次结果，不承诺逐字复现：

```text
模板返回对象： ChatPromptValue
输入角色： ['system', 'human']
模型返回对象： AIMessage
消息角色： ai
content 类型： str
模型回答： State是节点间传递、更新并持久化的共享数据结构。
工具调用数量： 0
结束原因： stop
解析后类型： TextAccessor
```

这句生成内容需要校正：**State 本身不会自动持久化。** 要跨调用或进程保存状态，需要后续课程的检查点保存配置。模型返回类型正确、请求成功，不代表事实描述完全正确。

| 模式 | 实测结构与行为 | 本次客户端总耗时 |
| --- | --- | --- |
| `check` | 退出 `0`，返回 `ChatOpenAI` 客户端，未发送生成请求 | 未测 |
| 默认 `invoke` | 退出 `0`，非空 `AIMessage`，结束原因 `stop`；输入/输出/总 token 为 `78/190/268`，输出中推理 token 为 `174` | 6.225 秒 |
| `stream` | 退出 `0`，累计 `118` 个 `AIMessageChunk`，非空文本，结束原因 `stop` | 9.145 秒 |
| `batch` | 退出 `0`，`list` 长度 `2`，顺序对应 State、Node，均为非空 `AIMessage`；各自总 token 为 `244`、`271` | 16.540 秒 |
| `chain` | 退出 `0`，`RunnableSequence` 调用后得到非空 `TextAccessor`，内容解释 Node | 13.827 秒 |
| `async` | 退出 `0`，`await` 后得到非空 `AIMessage`，结束原因 `stop`；输入/输出/总 token 为 `78/253/331` | 17.589 秒 |

流式首块为 `0.837` 秒，首个非空文本块为 `8.937` 秒，均从流式模式计时起点计算。若整条流没有文字，首个文本块时间应为 `None`，不能对它调用 `round`。该保护与空流回归测试已在后续配置启动修复时通过离线验证；上表记录的是此前有文本的真实运行。块数不能代替 token 数。本课禁用流式用量扩展，未统计流式 token；管道只保留文本，未在该模式记录原始用量。这些单次观测不能用于证明哪种模式更快、更便宜。

真实故障验证：初次默认请求未通过非空检查；随后一次内存诊断请求确认 `content=""`、结束原因 `length`，输入/输出/总 token 为 `78/128/206`，推理 token 为 `128`。据此把预算从 128 调到 512，保留自动重试 `0`。失败请求也可能消耗额度；不把空响应伪装为成功。这里只记录两次 128 预算请求中诊断那次的用量，不推算所有请求总费用。

离线检查命令：

```powershell
uv run python -m unittest discover -s tests -p "test_*.py" -v
```

最后一次实际运行的完整测试共 13 项通过，退出 `0`：前课 8 项，本课当时 5 项。后续配置启动修复时，运行 `uv run python -m unittest discover -s tests -p test_05_model_config.py -v`，本课当前 6 项检查均通过，包含新增的空流边界；本次未重跑完整的 14 项。检查覆盖缺失/空配置、非法供应商与 URL、有限正超时、参数映射及生成预算、空响应和空流诊断。测试使用假凭据或手工消息，不加载真实 `.env`，不发送模型请求。

当前简化后实测：示例直接使用 `dotenv_values` 读取根目录配置，`uv run python examples/05_model_calls/demo.py --mode check` 退出 `0`，显示 `ChatOpenAI` 和“未发送模型请求”。全套 14 项测试通过；练习用临时假 `.env` 和离线模型检查了配置读取、参数映射与完整主流程，退出 `0`。检查期间禁止动态加载其他脚本，练习仍能独立完成；未发真实模型请求。先前的跨文件加载与进程重启已移除。

练习初态运行退出 `1`，提示“练习尚未完成：请补全 build_chain，组合模板、模型和文本解析器。”，没有发送模型请求；不把预留任务当作运行故障或学习者作答。

安装时官方 PyPI 连接超时，后使用临时环境变量 `UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple` 执行 `uv add langchain-openai` 成功。未把镜像配置写入 `pyproject.toml`，但 `uv.lock` 记录了解析时的镜像来源与下载地址；之后用锁文件复现。安装出现跨盘硬链接回退为复制的提示，不影响安装成功。

## 效果与限制

- 功能：已分别确认同步调用、消息类型、非空输出、流式完成、批量结果顺序、管道与异步调用；各模式的验证证据见上表。工具调用和结构化输出尚未验证。
- 质量：本课是少量教学输入，没有固定评估集；不报告准确率，也不承诺模型遵守每条长度要求。
- 性能与成本：已记录上述单次耗时及部分标准 token 用量，价格、账单费用和总体性能未测。每次执行会发出上表数量的真实请求，重跑会再次消耗额度。
- 不会自动接入企业知识库、执行工具或跨调用保存历史。初始化成功也不证明认证、网络与服务可用。
- 非空内容不一定是完整答案。达到长度上限、拒绝或内容不符合要求时，保留对应现象供排查。

## 一道核心练习

在 `exercises/05_model_calls/exercise.py` 中，只补全 `build_chain(model)`：返回按“给定模板 → 传入模型 → 字符串输出解析器”顺序组合的可运行对象，不能在构造函数里先执行请求，不能返回写死的回答。运行部分已经提供输入 `{"concept": "条件边"}`。

先描述：这个输入字典经过哪三种类型的返回值，哪一步才发送请求？再动手补全。无需另做异步、流式或批量练习；这些模式用于观察。

验收标准：

- 构造链不发送请求；调用一次链得到非空 `str`，变量替换有效。
- 能分清模板、模型与链上的 `invoke`，说明为什么解析器不再请求模型。
- 能解释原始消息与文本的区别，指出工具调用能力仍未验证。
- 能指出 `.env` 在当前脚本的哪一行被读取，说明缺少文件或必需配置时的提示。

学习者参照所请求的答案，已将 `build_chain` 改为返回管道。离线模拟检查通过：构造不调用模型，两种 concept 正确替换，执行返回字符串，主流程退出 `0`。独立原理解释与真实练习运行仍待确认，不记录为独立实现；本次检查未修改练习代码。

## 常见问题与排查

配置边界已由离线测试复现；生成预算耗尽、空文本以及安装时的网络超时已实测。认证失败、限流、远程 400 等其余项只是排查方向，不标为已复现。

| 现象 | 原因与排查 |
| --- | --- |
| 缺少 `LLM_*` 的配置错误 | 核对根目录 `.env` 是否存在及变量名；当前脚本通过 `dotenv_values` 直接读取，不需要 `--env-file`，不要把私有值贴进聊天 |
| 超时格式错误 | 仅填写有限正数；`nan`、`inf` 也不是有效超时 |
| 找不到 `langchain_openai` | 从根目录运行 `uv sync --locked`，确认适配包已进入声明和锁文件 |
| 401/403 | 服务认证或权限问题；在本地核对凭据与服务权限，不把密钥写入源码 |
| 连接失败或超时 | 检查网络、代理和地址；初始化客户端成功不等于服务连通 |
| 400 或不支持生成参数 | 核对兼容服务实际协议，特别是生成上限参数；不要因此切换到模拟回答并称成功 |
| 内容为空或 `finish_reason=length` | 本次确实出现过 128 预算全部用于推理、正文为空；示例先展示结束原因和用量，再以非零状态退出。512 本次成功，但不保证对所有模型都足够 |
| 流中先出现空块 | 元数据块可能没有文本；分别观察首块与首个文本块 |
| 直接打印协程 | 在异步函数内用 `await` 等待 `ainvoke` |

## 下一步与官方资料

完成本课练习后再进入第 06 课：本地工具、模型提出工具调用请求、程序执行工具、工具结果回到模型；工具调用与结构化输出分别验证。前课消息状态补充仍需观察和解释。

- [LangChain 模型初始化与调用](https://docs.langchain.com/oss/python/langchain/models)
- [ChatOpenAI 适配与兼容服务](https://docs.langchain.com/oss/python/integrations/chat/openai)
- [LangChain 消息](https://docs.langchain.com/oss/python/langchain/messages)
- [python-dotenv：直接读取 .env](https://bbc2.github.io/python-dotenv/)

### 备课执行清单

按 Superpowers 的计划与完成前验证方法组织本课；沿用仓库已明确的备课流程，不增加例行批准、提交或推送步骤。

- [x] 读取日志、课程索引、模板与环境约定，先写讲义初稿。
- [x] 先添加配置边界检查，确认尚未实现时失败；编写示例与单一练习骨架。
- [x] 添加适配包并核对锁定版本；运行主体离线检查和受控真实请求，`uv sync --locked` 退出 `0`。
- [x] 后续配置启动修复时验证直接启动命令，并通过本课 6 项离线检查，包含空流边界；未重复运行所有模型模式。
- [x] 回填实测与未验证范围，更新课程入口和备课记录。
