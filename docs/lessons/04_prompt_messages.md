# 第 04 课：消息角色与提示词模板

> 备课状态：可学习。2026-10-23 已运行离线示例并验证关键行为；本课两项消息状态测试与既有六项测试均通过。学习者尚未作答。

## 本课目标与场景

前面已用固定字符串模拟回答。接入模型之前，先明确要给模型什么数据：系统规则、过去的对话、当前的问题，应当组成怎样的消息列表？

核心目标：**独立组织一份角色与顺序正确的消息序列，并解释模板格式化为什么还没有调用模型。** 主线是提示词模板；消息状态作为同一课的补充，连接第 02 课的归并器。

本课不接入真实模型，不执行工具。历史中的 `AIMessage` 均由代码手工创建，是示例历史；补充图中的回复也是固定模拟文本，不能视为模型生成结果。

## 前置条件与环境

- 需要认识字典、列表、函数返回值，以及节点返回部分状态更新；第 02 课的列表归并规则会在补充部分复用。
- 2026-10-23 实查：Python 3.12.13、LangChain 1.4.6、`langchain-core` 1.6.12、LangGraph 1.2.16。
- 使用项目现有依赖，无需 `uv add` 新包；首次安装环境执行 `uv sync --locked`。`langchain_core` 是本次导入模块名，其安装分发名为 `langchain-core`。
- 不加载 `.env`，不需要模型凭据。真实模型适配包和服务验证仍留到第 05 课。

## 文件与运行命令

| 内容 | 路径 |
| --- | --- |
| 讲义 | [04_prompt_messages.md](04_prompt_messages.md) |
| 主示例：模板与历史 | [examples/04_prompt_messages/demo.py](../../examples/04_prompt_messages/demo.py) |
| 补充示例：消息状态 | [examples/04_prompt_messages/demo_message_state.py](../../examples/04_prompt_messages/demo_message_state.py) |
| 一道核心练习 | [exercises/04_prompt_messages/exercise.py](../../exercises/04_prompt_messages/exercise.py) |
| 消息状态的关键行为测试 | [tests/test_04_message_state.py](../../tests/test_04_message_state.py) |

从项目根目录 `D:\project\langgraph` 的 PowerShell 执行：

```powershell
uv run python examples/04_prompt_messages/demo.py
uv run python exercises/04_prompt_messages/exercise.py

# 理解主示例后再运行消息状态补充
uv run python examples/04_prompt_messages/demo_message_state.py

# 检查导师示例，不代替学习者练习验收
uv run python -m unittest discover -s tests -p "test_*.py" -v
```

## 先区分消息的角色与内容

普通字符串只有内容；消息对象还包含角色以及可选的消息 ID 等信息。先从普通 Python 手动组织消息开始：

```python
from langchain.messages import AIMessage, HumanMessage, SystemMessage

messages = [
    SystemMessage(content="你是一名 LangGraph 导师。"),
    HumanMessage(content="什么是 State？"),
    AIMessage(content="示例历史回答：State 保存工作流共享的数据。"),
    HumanMessage(content="那 Node 怎样更新它？"),
]
```

这只是创建四个对象，没有发送任何请求。`AIMessage` 表示“这条消息按助手角色参与对话”，不证明它一定来自真实模型调用。

| 消息对象 | 本课用途 | `.type` | `.content` |
| --- | --- | --- | --- |
| `SystemMessage` | 应用提供的角色要求和规则 | `system` | 指令文本 |
| `HumanMessage` | 历史用户提问或当前问题 | `human` | 用户文本 |
| `AIMessage` | 示例历史中的助手回答 | `ai` | 助手文本；本课由程序手工创建 |

这三个类从 `langchain.messages` 导入。LangChain 对象的 `human`、`ai` 类型通常由模型适配器转换为服务端的 `user`、`assistant`，不要把内部属性名与某个供应商的 JSON 字段直接混用。

消息的 `.id` 是可选标识，用于区分消息；补充部分会显式设置它。`.content` 也可承载复杂内容块，本课只使用文本字符串。

工具结果消息 `ToolMessage` 留在第 06 课：届时会结合匹配的 `tool_call_id` 与实际执行过程讲解，本课不把手工文本当作工具执行结果。

## AIMessage 具体怎样用，调用后得到什么

`AIMessage` 是一个类，`AIMessage(...)` 是构造对象的调用。它可以把已有文本组织成助手角色消息，用于历史记录、示例数据或图中的消息状态。文本已经明确时，不需要让模型重新生成。

在本项目的 LangChain 1.4.6、`langchain-core` 1.6.12 中，使用方式如下：

```python
from langchain.messages import AIMessage

# 把已有文本放进一条助手消息，不会自动生成新回答。
message = AIMessage(
    content="你好，我可以帮你学习 LangGraph。",
    id="reply-1",
)

print(type(message).__name__)  # 整个返回对象的类型
print(message.content)         # 取出文本
print(message.type)            # 取出角色标记
print(message.id)              # 取出本例指定的消息标识
```

2026-10-23 实测输出：

```text
AIMessage
你好，我可以帮你学习 LangGraph。
ai
reply-1
```

所以这里有两个不同的值：

- `message` 是包含文本、角色、标识等字段的 `AIMessage` 对象。
- `message.content` 才是本例传入的字符串，实际类型为 `str`。

本课常用的参数及字段：

| 参数或属性 | 用途、默认行为 | 上例实际值与类型 |
| --- | --- | --- |
| 构造参数 `content` / 属性 `.content` | 本课传入并保存文本；也支持内容块等复杂形式，本课暂不展开 | `"你好，我可以帮你学习 LangGraph。"`，`str` |
| 构造参数 `id` / 属性 `.id` | 可选消息标识；本例明确设置。不传时直接构造得到的 `.id` 实测为 `None`，后续组件可能再赋值 | `"reply-1"`，`str` |
| 属性 `.type` | 消息的角色标记，`AIMessage` 默认是 `"ai"`；不同于 Python 的 `type(message)` | `"ai"`，`str` |
| 属性 `.tool_calls` | 工具调用请求列表；本例未提供，默认为空列表 | `[]`，`list` |
| 属性 `.usage_metadata` | 可用时记录模型 token 用量等；手工构造不会产生真实用量信息 | `None` |
| 属性 `.response_metadata` | 可保存供应商返回的其他信息；本例未提供 | `{}`，`dict` |

本版本若既不提供 `content` 也不提供其他有效内容，直接调用 `AIMessage()` 实测会抛出 `ValidationError`；不要把可省略 `id` 理解成可以省略所有消息内容。

`print(message)` 不是只打印内容，实测显示为：

```text
content='你好，我可以帮你学习 LangGraph。' additional_kwargs={} response_metadata={} id='reply-1' tool_calls=[] invalid_tool_calls=[]
```

这是对象的打印形式，不是模型新生成的回答，也不是 JSON 字符串。只要文本时读取 `.content`；需要普通字典时可以使用：

```python
# model_dump 是把数据模型转成字典，不会调用语言模型。
message_dict = message.model_dump()
print(type(message_dict).__name__)  # dict
print(message_dict["content"])      # 你好，我可以帮你学习 LangGraph。
```

在本课历史列表中，`AIMessage(content="示例历史回答：State 保存工作流共享的数据。")` 的实际作用是：把这段已有文本表示为“历史中助手说过的话”。模板插入历史时会保留这个助手角色，因此消息顺序是“用户问 State → 助手解释 State → 用户继续问 Node”，而不只是三段没有身份的文本。

构造后的文本仍是你传入的原文，不会自动续写或回答下一问。以后将这样的历史传给聊天模型时，它会作为助手角色的上下文参与模型输入；真实生成效果需要在模型课另行验证。本课这里只组织消息，没有发送真实模型请求。接口效果和返回结构在讲义中阅读即可，练习仍按原任务完成。

## 区分类的构造与对象的使用

本课其他接口也按“这一次调用究竟拿到什么”来阅读：

| 具体调用 | 这一步得到什么 | 接下来怎样用 |
| --- | --- | --- |
| `HumanMessage(content="问题")` | `HumanMessage` 对象，`.content` 为 `"问题"`，`.type` 为 `"human"` | 放入消息列表或读取 `.content` |
| `SystemMessage(content="规则")` | `SystemMessage` 对象，`.content` 为 `"规则"`，`.type` 为 `"system"` | 放在本课输入消息序列的开头 |
| `MessagesPlaceholder("history")` | `MessagesPlaceholder` 对象，`.variable_name` 为 `"history"`，`.optional` 默认为 `False` | 放进模板，等格式化时再插入历史，不是现在就返回历史消息 |
| `ChatPromptTemplate.from_messages([...])` | `ChatPromptTemplate` 对象 | 看 `.input_variables` 需要哪些变量，再调用 `.invoke(...)` |
| `prompt.invoke({...})` | 本课为 `ChatPromptValue` 对象 | 调用 `.to_messages()` 得到消息列表 |
| `result.to_messages()` | 普通列表，其中每个元素是消息对象 | `messages[0].content` 取第一条消息的内容，循环查看每条角色 |

下面继续讲这些对象怎样组合。练习仍按原任务完成，不新增或替换练习要求。

## 提示词模板解决什么问题

当导师主题、当前问题不断变化时，可以把固定部分与变量分开。少量固定消息直接用 Python 列表即可；需要反复替换变量、插入多条历史消息时，使用对话提示词模板（ChatPromptTemplate）。

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一名{subject}导师。请用简体中文回答。"),
    MessagesPlaceholder("history"),
    ("human", "{question}"),
])
```

这里有三种位置：

- `("system", "…{subject}…")`：固定角色的模板，替换 `subject` 后得到系统消息。
- `MessagesPlaceholder("history")`：消息占位符，插入一整个历史消息列表，保留其中的角色和顺序。
- `("human", "{question}")`：把本次问题放成最后一条用户消息。

不要把历史写成 `("human", "{history}")`：那会把列表当成一个变量格式化进一段文本，失去多条消息各自的角色结构。

## 输入、输出与执行顺序

准备两条示例历史，然后调用：

```python
history = [
    HumanMessage(content="什么是 State？"),
    AIMessage(content="示例历史回答：State 保存工作流共享的数据。"),
]

result = prompt.invoke({
    "subject": "LangGraph",
    "history": history,
    "question": "那 Node 怎样更新它？",
})
messages = result.to_messages()
```

`result` 实测为 `ChatPromptValue`；`result.to_messages()` 得到消息对象列表。`ChatPromptValue` 定义在 `langchain_core.prompt_values`，本课使用模板返回的对象，不需要手工导入或构造它。过程如下：

```text
变量字典 → 模板替换与历史插入 → ChatPromptValue → to_messages() → 消息列表
```

| 位置 | 对象（实测与预期一致） | 内容 |
| --- | --- | --- |
| 1 | `SystemMessage` | 你是一名LangGraph导师。请用简体中文回答。 |
| 2 | `HumanMessage` | 什么是 State？ |
| 3 | `AIMessage` | 示例历史回答：State 保存工作流共享的数据。 |
| 4 | `HumanMessage` | 那 Node 怎样更新它？ |

**这里的 `invoke` 属于模板，只做格式化。** 第 01 课的 `graph.invoke` 运行图，第 05 课的 `model.invoke` 才会发起模型调用；方法名字相同，需要先看调用它的对象。

## 本课 API 说明

| API 与导入来源 | 调用、参数和默认行为 | 输入与返回、检查点 |
| --- | --- | --- |
| `SystemMessage`、`HumanMessage`、`AIMessage`，`langchain.messages` | 用 `content="文本"` 创建；可传 `id="标识"` | 返回对应消息对象；观察 `.type`、`.content`、`.id` |
| `ChatPromptTemplate.from_messages`，`langchain_core.prompts` | 参数是有序消息模板列表；本课采用默认的 `f-string` 模板格式 | 返回 `ChatPromptTemplate`；`.input_variables` 列出需要填入的变量名 |
| `MessagesPlaceholder`，`langchain_core.prompts` | `variable_name="history"`；默认 `optional=False`，必须提供该变量；默认 `n_messages=None` 不主动截断历史 | 从输入中取消息列表并插入模板；传 `history=[]` 合法，缺少变量与空列表不同 |
| `prompt.invoke` | 输入变量字典，键对应 `subject`、`history`、`question` | 本课得到 `ChatPromptValue`，不调用模型；缺少必需变量会报错 |
| `result.to_messages()` | 不需要参数 | 返回消息对象列表，可逐条访问角色与文本 |
| `MessagesState`，`langgraph.graph` | 作为 `StateGraph(MessagesState)` 的状态结构 | 内含 `messages` 字段，并配置消息归并器 `add_messages` |
| `add_messages`，`langgraph.graph.message` | `add_messages(old_messages, updates)`；本课直接传消息对象列表 | 新 ID 的消息追加，已有 ID 的消息在原位置更新；与单纯 `operator.add` 拼接不同 |

`MessagesPlaceholder(optional=True)` 可允许省略历史变量；这不是本课主示例或练习的默认设置。`n_messages` 可以限制保留的历史消息条数，但不保证对话轮次或工具调用配对完整，本课先不截断。

## 补充：将消息放进 LangGraph 状态

第 02 课用 `add` 拼接列表，同一条记录再次返回也会重复。消息状态有时需要“更正同一条消息”：这时使用 `add_messages`，按消息 ID 决定追加还是更新。

[补充示例](../../examples/04_prompt_messages/demo_message_state.py) 是一张串行图：

```text
START → draft_reply（手工模拟草稿）→ revise_reply（手工模拟更正）→ END
```

初始状态有 `HumanMessage(id="question-1", ...)`。两个节点分别只返回一条 `AIMessage`，两次的 ID 都为 `reply-1`。

| 时点 | 消息 ID 顺序 | 实测行为 |
| --- | --- | --- |
| 初始 | `question-1` | 用户问题 |
| 草稿后 | `question-1, reply-1` | 新 ID，追加助手消息 |
| 更正后 | `question-1, reply-1` | 已有 ID，更新第二条消息的内容，不新增第三条 |

补充脚本还会直接对比两个函数：`add([草稿], [更正])` 保留两条；`add_messages([草稿], [更正])` 只保留一条更正后的消息。**相同内容不代表相同消息；决定是否更新的关键是 ID。**

这里的 ID 与第 06 课要学的 `tool_call_id` 用途不同。本课不配置检查点保存器，因此消息状态不会自动跨两次独立运行或跨进程保留。提示词模板也不会自动替你记住历史，调用时仍需显式传入。

## 预期与实测结果

2026-10-23 实际执行：

```powershell
uv run python examples/04_prompt_messages/demo.py
uv run python examples/04_prompt_messages/demo_message_state.py
uv run python -m unittest discover -s tests -p "test_*.py" -v
uv run python exercises/04_prompt_messages/exercise.py
```

两个示例均退出 `0`。主示例的完整输出为：

```text
必需变量： ['history', 'question', 'subject']
模板返回对象： ChatPromptValue
以下是格式化消息，不是本次生成的模型回答：
SystemMessage system 你是一名LangGraph导师。请用简体中文回答。
HumanMessage human 什么是 State？
AIMessage ai 示例历史回答：State 保存工作流共享的数据。
HumanMessage human 那 Node 怎样更新它？
```

消息状态示例观察到三份状态中的消息条数分别为 `1 → 2 → 2`，末尾助手消息从模拟草稿变为模拟更正，原用户问题始终保留。直接调用 `add` 的比较结果为两条同 ID 消息；调用 `add_messages` 后只有一条更正后的消息。

自动化测试输出 `Ran 8 tests`、`OK`，退出码 `0`：第 03 课原有六项，本课新增两项，针对导师消息图验证原问题保留、同 ID 更正、执行过程消息数与内容变化。测试不加载本课练习，不能代替学习者练习验收。

练习初始版本退出码 `1`，抛出预留的 `NotImplementedError: 请补全 build_prompt，返回 ChatPromptTemplate。`，用于提示尚未作答。

另通过 PowerShell 向 `uv run python -` 传入一次性检查代码，七组检查均通过，退出码 `0`：

| 检查 | 实测结果 |
| --- | --- |
| 模板替换、角色顺序与返回对象 | 两条历史得到四条消息，角色为 `system → human → ai → human`，对象为 `ChatPromptValue` |
| 空历史与再次调用 | 显式传 `[]` 得到两条消息，前一次调用的历史不会自动保留 |
| 缺少必需变量 | 分别省略 `subject`、`history`、`question`，均抛出 `KeyError` |
| 历史传入字符串 | 抛出 `ValueError`，不能当作消息列表使用 |
| 显式 `optional=True` | 省略历史变量也能格式化，得到两条消息 |
| 消息 ID 与内容 | 同 ID 更正只保留新内容；相同内容但不同 ID 仍追加为两条 |
| 将历史误放进普通用户模板 | 得到三条消息，历史被格式化成一条用户消息，未保留各历史角色 |

这些代码只实例化消息、格式化模板或执行普通函数节点，没有初始化或调用模型。未发送真实服务请求，也未验证真实模型的消息兼容性。

## 效果与限制

- 功能：已验证消息角色、顺序、模板变量替换、空历史与缺失变量的区别，以及消息 ID 更新。
- 质量：没有请求模型，没有生成答案；不能据此评价回答正确率或模型是否遵守系统规则。
- 性能：本地耗时、内存未测。当前不调用模型，不产生模型请求 token 或费用；未来把更长历史发送给模型时会增加上下文规模，具体 token、延迟和费用须另测。
- 系统消息是应用给出的指导，不保证模型必然遵守，也不能把构建消息当成完成安全校验。
- `add_messages` 按 ID 处理消息更新，不按文本内容自动去重，不等于压缩历史或持久化。
- 本课学习纯文本消息。多模态、实际工具往返、模型流式输出和跨调用记忆尚未验证。

## 一道核心练习

[练习文件](../../exercises/04_prompt_messages/exercise.py) 已提供 `build_prompt()` 骨架和运行代码。你只补全模板构造，不调用模型，不用固定字符串直接写死最终输出。

模板要求依次组织：

1. 系统规则：`你是一名{subject}导师。请用简体中文回答。`
2. 必需的历史消息占位符，变量名为 `history`。
3. 当前用户问题：`请用{style}解释：{question}`。

运行代码提供 `subject="LangGraph"`、两条示例历史、`style="一个生活类比"`、`question="什么是条件边？"`。预期得到系统、历史用户、历史助手、当前用户四条消息；最后一条为 `请用一个生活类比解释：什么是条件边？`。

先用一句话说明：为什么历史用消息占位符，而当前问题用一条用户模板？再补全 `build_prompt()`，返回 `ChatPromptTemplate`。参考解答在需要或讲评时再创建。

## 验收标准

- 独立构造符合要求的模板，输入内容正确替换；两条历史得到四条消息，空历史得到两条。
- 解释 `ChatPromptValue` 与消息列表、模型生成回答的区别；说明三种 `invoke` 分别做什么。
- 能指出 `AIMessage` 由代码手工创建时只是示例历史，不是调用过模型的证据。
- 理解必需变量缺失与空列表不同；可在打印结果中识别角色和顺序。
- 补充部分能预测同 ID、更换 ID 时消息条数与内容怎样变化，理解消息状态不等于持久化。

本课尚无学习者作答证据，不标记为已掌握。

## 常见问题与排查

前三项已在本次一次性检查中观察到；消息 ID 行为已由示例和测试确认。最后一项是阅读代码时的判断方法：

| 现象 | 检查方向 |
| --- | --- |
| 缺少变量的 `KeyError` | 查看 `.input_variables`，核对调用字典；需要空历史时显式传 `history=[]` |
| 历史参数类型错误 | 传消息对象列表，不能直接传一大段历史字符串 |
| 历史变成一条很长的用户消息 | 是否误用 `("human", "{history}")`，而不是 `MessagesPlaceholder` |
| 更正助手消息却又追加了一条 | 核对两条消息的 ID 是否一致，不只检查内容相似 |
| 打印到 `AIMessage` 就以为已请求模型 | 查找是否真的初始化模型并调用它；本课没有相关调用 |

## 下一步与官方资料

先完成模板练习，再按需要看消息状态补充。下一课才引入真实模型，显式映射 `.env` 的配置项、安装供应商适配包并做受控的最小请求验证。

- [LangChain 消息与角色](https://docs.langchain.com/oss/python/langchain/messages)
- [AIMessage 的创建与属性](https://docs.langchain.com/oss/python/langchain/messages#ai-message)
- [ChatPromptTemplate](https://reference.langchain.com/python/langchain-core/prompts/chat/ChatPromptTemplate)
- [MessagesPlaceholder](https://reference.langchain.com/python/langchain-core/prompts/chat/MessagesPlaceholder)
- [LangGraph 消息归并规则](https://docs.langchain.com/oss/python/langgraph/graph-api#working-with-messages-in-graph-state)
- [LangGraph MessagesState](https://docs.langchain.com/oss/python/langgraph/graph-api#messagesstate)

本次工具捕获中文时使用 `$env:PYTHONIOENCODING = "utf-8"`；若输出乱码，可先在当前 PowerShell 设置后再运行。

### 备课检查

- [x] 先写目标、API、预期效果与练习。
- [x] 创建主示例、消息状态补充、练习与必要检查。
- [x] 运行并核对正常、空历史、错误输入与消息更新。
- [x] 回填实测，更新课程入口与学习记录。
