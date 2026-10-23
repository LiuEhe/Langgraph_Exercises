# 第 06 课：工具调用往返与结构化输出

> 备课状态：可学习（2026-10-23，本地行为、18 项离线检查、真实工具往返及结构化输出分别验证通过）。主目标是看懂一次工具往返；结构化输出是同课补充。第 05 课独立原理解释仍待确认，不因本课备课自动记录为已掌握。

## 本课目标与场景

用户问：“每箱 7 本书，8 箱一共多少本？请调用工具计算。”我们提供 Python 乘法工具，让模型提出参数，程序实际计算，再让模型根据工具结果组织回答。

本课重点是分清三件事：**模型提出调用请求、Python 执行工具、模型读取工具结果**。绑定工具不会自动完成后两步。

补充场景是从“订单商品为键盘，数量为 2”中提取字段：返回有类型和字段约束的对象，便于后续程序使用。

这里仍是固定的 Python 执行顺序，最多两次模型请求，没有 Agent 自主循环。下一课再用 LangGraph 和 `create_agent` 组织流程。

## 前置条件与版本

- 已读第 04 课消息角色、第 05 课模型调用；能区分构造对象与调用 `invoke`。若仍不清楚，先回看第 05 课的数据流。
- 当前锁定版本：Python 3.12.13、LangChain 1.4.6、langchain-core 1.6.12、langchain-openai 1.7.2、LangGraph 1.2.16、python-dotenv 1.2.4、Pydantic 2.14.1。
- 现有适配包和 `.env` 继续使用，不重新验证第 05 课所有模式。关闭思考的参数继续保留，效果以本课实测为准。
- Pydantic 已由现有依赖安装；本课开始直接使用，已通过离线缓存执行 `uv add --offline pydantic` 声明为直接依赖，版本仍为 2.14.1，没有下载或升级现有包。首次从空环境引入时命令为 `uv add pydantic`。
- 所有模型代码在各自文件中用 `dotenv_values` 直接读取根目录 `.env`，不加载其他示例、不重启进程、不输出私有值。

## 文件与运行命令

| 内容 | 位置 |
| --- | --- |
| 工具往返示例 | [demo.py](../../examples/06_tools_structured_output/demo.py) |
| 结构化输出补充 | [demo_structured.py](../../examples/06_tools_structured_output/demo_structured.py) |
| 一道核心练习 | [exercise.py](../../exercises/06_tools_structured_output/exercise.py) |
| 关键行为测试 | [test_06_tools.py](../../tests/test_06_tools.py) |

从项目根目录运行：

```powershell
# 先观察本地工具对象、参数说明与 Python 返回值：不请求模型
uv run python examples/06_tools_structured_output/demo.py --local-only

# 一次完整工具往返：两次真实模型请求，自动重试为 0
uv run python examples/06_tools_structured_output/demo.py

# 补充：本地验证字段约束，不请求模型
uv run python examples/06_tools_structured_output/demo_structured.py --local-only

# 补充：结构化提取，一次真实请求
uv run python examples/06_tools_structured_output/demo_structured.py

# 练习默认使用手工消息，不请求模型；未作答时提示 NotImplementedError
uv run python exercises/06_tools_structured_output/exercise.py

# 完成练习后可选择接入模型，最多两次请求
uv run python exercises/06_tools_structured_output/exercise.py --live
```

## 先看完整的数据变化

```text
SystemMessage + HumanMessage
        │ 第一次模型请求：告诉模型可用工具
        ▼
AIMessage(tool_calls=[工具名、参数、调用 ID])
        │ Python 按请求执行工具，不请求模型
        ▼
ToolMessage(content="56", tool_call_id=同一个调用 ID)
        │ 将原消息、工具请求和工具结果一并发给模型
        ▼
第二次模型请求 → AIMessage(content=自然语言回答)
```

| 时点 | 消息角色顺序 | 发生的动作 |
| --- | --- | --- |
| 起点 | `system → human` | 程序准备规则和问题 |
| 第一次返回后 | `system → human → ai` | 助手消息携带工具调用请求，正文允许为空 |
| 执行工具后 | `system → human → ai → tool` | Python 计算并补入工具结果 |
| 第二次返回后 | `system → human → ai → tool → ai` | 模型读取结果并组织回答 |

不要漏掉带 `tool_calls` 的助手消息，也不要仅发送一条工具结果。模型需要完整的请求与回复配对。

## 第一步：把普通函数声明为工具

```python
from langchain.tools import tool

@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers and return their product."""
    return a * b
```

装饰器（decorator）`@tool` 根据函数名、类型标注和文档字符串，构造可描述和校验参数的工具。本课实测 `type(multiply).__name__` 为 `StructuredTool`，使用 `.invoke(...)` 执行，不直接用 `multiply(7, 8)` 调用。

| 观察表达式 | 实测结果与用途 |
| --- | --- |
| `multiply.name` | `"multiply"`，用于匹配模型提出的工具名 |
| `multiply.description` | 函数的文档字符串，告诉模型工具做什么 |
| `multiply.args` | 字典，包含 `a`、`b` 两个整数参数的说明 |
| `multiply.invoke({"a": 7, "b": 8})` | 整数 `56`，在本地执行 Python 函数，不请求模型 |

这里的 `invoke` 属于工具；上一课的 `model.invoke` 才请求模型。若程序已经知道要计算哪个函数，普通 `7 * 8` 或函数调用就足够；工具对象额外提供的是给模型看的名称、描述和参数结构。

类型标注用于生成参数结构与校验。工具不是沙箱，Python 函数能做什么取决于函数自身。本课只计算整数，不读文件、发邮件或修改外部数据。

## 第二步：绑定工具，观察模型提出请求

模型初始化仍是当前文件内的 `init_chat_model`，直接映射 `.env` 的五项配置；沿用 `max_tokens=512`、`max_retries=0` 和 `extra_body={"enable_thinking": False}`。

```python
bound_model = model.bind_tools([multiply], tool_choice="multiply")
request = bound_model.invoke(messages)
print(request.tool_calls)
```

- `bind_tools` 是模型对象的方法。输入工具列表，返回一个携带工具定义的可运行对象；当前版本实测类型名为 `_ChatModelBinding`，属于内部实现，按可运行对象的 `.invoke(...)` 使用即可，不手工导入该内部类。**绑定本身不请求模型，也不执行工具。** 原模型对象仍可单独使用。
- `tool_choice="multiply"` 显式要求选择这个工具，便于本课控制执行路径，不表示模型自主决定一定需要工具。`tool_choice="auto"` 才允许服务选择调用或直接回答；默认行为及支持情况依供应商而异。
- `bound_model.invoke(messages)` 才发起第一次请求，返回 `AIMessage`。参数由模型生成，程序仍要检查。

返回结构示意，调用 ID 每次可能不同，不要求逐字复现：

```python
request.tool_calls == [{
    "name": "multiply",
    "args": {"a": 7, "b": 8},
    "id": "call_demo",       # 示意 ID
    "type": "tool_call",
}]
```

这里的 `args` 已由适配层解析成 Python 字典，不需要自行 `eval`。`content` 可以是空字符串：当前返回的是调用请求，不能只检查正文就判断失败。

主示例要求恰好一个调用、正确工具名和有效调用 ID。若服务没返回调用或返回多个调用，本课明确报错并停止，不静默模拟成功；多工具调度留到下一课。

## 第三步：执行工具，构造匹配的 ToolMessage

```python
from langchain.messages import ToolMessage

call = request.tool_calls[0]
result = multiply.invoke(call["args"])
reply = ToolMessage(
    content=str(result),
    tool_call_id=call["id"],
    name=call["name"],
)
```

逐个看返回值：

| 表达式或属性 | 对当前输入的预期值 |
| --- | --- |
| `result` | 整数 `56`，由本地工具计算 |
| `reply` | `ToolMessage` 对象，构造消息不请求模型 |
| `reply.type` | `"tool"` |
| `reply.content` | 字符串 `"56"` |
| `reply.tool_call_id` | 对应请求的 `call["id"]`，示意为 `"call_demo"` |
| `reply.name` | `"multiply"`，辅助识别工具 |

`tool_call_id` 用于匹配“这个结果回答了哪个工具请求”；它不是第 04 课消息自身的 `.id`，不能混用。多个调用时，仅工具名相同也不足以匹配具体请求。

主示例会在执行前确认工具名和调用 ID，随后由工具校验参数。未知工具、缺少参数、错误参数类型都会停止；不把错误文本伪装成正常计算结果，也不会执行任意模型提出的函数名。

## 第四步：把工具结果交回模型

```python
messages.append(request)
messages.append(reply)
answer = model.invoke(messages)
```

`append` 修改当前消息列表；顺序是原输入、助手请求、工具结果。最后使用**原模型**请求自然语言回答，不再强制选择工具，因此不会因为 `tool_choice="multiply"` 再次请求工具。

`answer` 预期为非空 `AIMessage`，表达计算结果 `56`；具体措辞由模型生成。本例总共两次请求，中间的工具执行和消息构造都是本地操作。代码没有 `while` 循环，没有自动重试，也没有验证 Agent 自主退出能力。

## 补充：让输出变成字段对象

字符串输出解析器只能提取文本；当后续程序需要商品名和数量时，使用结构化输出（structured output）。

```python
from pydantic import BaseModel, Field

class OrderInfo(BaseModel):
    product: str = Field(description="订单商品名称")
    quantity: int = Field(ge=1, description="购买数量，必须至少为 1")
```

`BaseModel` 提供字段校验与属性访问；`Field` 声明字段说明和约束。这里没有给默认值，所以两项都必须提供。`ge=1` 表示数值大于或等于 1；不是让模型额外发请求。

本地构造：

```python
order = OrderInfo(product="键盘", quantity=2)
print(order.product)       # 键盘，str
print(order.quantity)      # 2，int
print(order.model_dump())  # {'product': '键盘', 'quantity': 2}
```

`OrderInfo(...)` 返回经过校验的 `OrderInfo` 实例；`.model_dump()` 返回普通字段字典。`quantity=0` 或缺少必需字段会抛出 `pydantic.ValidationError`。默认校验也可能做合法的类型转换，不等于所有输入都按严格类型原样接受。

模型生成时使用：

```python
structured_model = model.with_structured_output(
    OrderInfo,
    method="function_calling",
)
order = structured_model.invoke([
    ("system", "只提取用户提供的订单字段，不编造。"),
    ("human", "订单商品为键盘，数量为 2。"),
])
```

`with_structured_output` 返回按 schema 约束并解析结果的可运行对象，本身不请求模型；其 `invoke` 发出一次请求，本课预期直接返回 `OrderInfo`，不是 `AIMessage`。默认 `include_raw=False`，本课不取原始消息；不要因此认为没有模型 token 消耗。

当前 ChatOpenAI 适配器的 `method` 默认是 `"json_schema"`；本课**显式指定 `"function_calling"`**，仅验证这个方法在现有兼容服务上的表现，不推断原生 JSON Schema 或 JSON 模式也可用。

这条路径利用工具调用协议返回字段，但没有执行我们的乘法函数，不需要发送第二次工具结果请求。字段格式正确仍可能事实错误；例如原文数量为 2 却返回 3，类型校验会通过，本课还会按给定输入检查字段值。

## 预期结果与实测记录

2026-10-23 先运行本地模式与离线测试，再分别运行两个真实示例，均完成验证。只验证本课新增能力，没有重跑第 05 课各模式。

| 项目 | 实测结果 |
| --- | --- |
| 本地工具 | `--local-only` 退出 `0`；对象为 `StructuredTool`，参数说明包含两个整数，结果为整数 `56` |
| 真实工具往返 | 主示例退出 `0`；模型请求一个 `multiply`，参数 `{"a": 7, "b": 8}`；工具回复 ID 匹配、内容 `"56"`，最终消息包含 `56` |
| 本地字段校验 | 补充 `--local-only` 退出 `0`；合法实例能访问字段，数量 0 抛出 `ValidationError` |
| 真实结构化输出 | 补充示例退出 `0`；包装对象为 `RunnableSequence`，返回 `OrderInfo`，商品 `键盘`、整数数量 `2` |
| 练习初态 | 默认运行退出 `1`，提示“请补全 make_tool_reply，执行工具并返回匹配的 ToolMessage。”，未请求模型 |

上面的真实调用命令分别为：

```powershell
uv run python examples/06_tools_structured_output/demo.py
uv run python examples/06_tools_structured_output/demo_structured.py
```

工具往返实测摘录，最终回答是这一次模型生成的内容，不要求每次相同：

```text
绑定返回对象： _ChatModelBinding
第一次返回： AIMessage
工具回复： ToolMessage 56
调用 ID 匹配： True
第二次请求角色： ['system', 'human', 'ai', 'tool']
第二次返回： AIMessage
模型回答： 每箱 7 本书，8 箱一共 **56** 本。
最终角色顺序： ['system', 'human', 'ai', 'tool', 'ai']
```

本次主示例两次请求的用量分别为输入/输出/总计 `325/29/354`、`108/18/126` token，合计 480 token；总耗时 14.704 秒。结构化补充耗时 13.667 秒，`.model_dump()` 为 `{'product': '键盘', 'quantity': 2}`；因默认未保留原始消息，没有记录该模式 token。账单费用未测，不把单次耗时当作稳定性能。

两类真实请求都携带 `extra_body={"enable_thinking": False}` 并成功；返回用量未提供推理 token 明细，不据此额外推断服务内部推理消耗为零。未验证 `method="json_schema"`、`"json_mode"`、自动选择工具、多工具并行或任意 Agent 循环。练习 `--live` 尚未运行，不将导师示例验证等同于学习者验收。

离线测试命令：

```powershell
uv run python -m unittest discover -s tests -p "test_*.py" -v
```

18 项通过，退出 `0`，其中本课新增 4 项。覆盖不同数字和调用 ID、未知工具、缺少 ID、参数缺失或非法、工具请求与回复进入第二次上下文、字段约束和必需字段。先观察到缺少实现时失败，再补齐导师代码。测试中的模型是本地替身，不是对远程服务的验证；不会读取真实配置或发请求。未修改前课练习，未创建本课参考解答。

## 效果与边界

- 功能：工具请求、工具结果、最终消息必须分别检查；结构化输出单独验证。
- 质量：计算结果可确定；模型选参是否符合原问题、最终描述是否正确仍需检查。这几个例子不构成整体准确率评估。
- 性能与成本：主示例最多两次请求，补充最多一次，单次输出预算 512、自动重试 0；本次耗时与已获取用量见上，账单费用未测。运行 `--live` 练习会额外发请求。
- 兼容性：`bind_tools`、具名 `tool_choice`、结构化输出方法都需服务支持；初始化成功不证明它们可用。
- 失败：网络错误、模型不返回调用、工具校验失败、字段解析失败分别保留诊断类别，不静默重试或改成模拟成功。

## 一道核心练习

编辑 `exercises/06_tools_structured_output/exercise.py` 的 `make_tool_reply(call)`，其余框架已提供，所有代码在同一文件。

已给本地工具 `add_numbers`，函数输入是来自 `AIMessage.tool_calls` 的一个调用字典。例如：

```python
{"name": "add_numbers", "args": {"a": 37, "b": 58}, "id": "practice-1", "type": "tool_call"}
```

你需要检查工具名与调用 ID，执行指定工具，并返回 `ToolMessage`。预期 `.content == "95"`、`.tool_call_id == "practice-1"`、`.name == "add_numbers"`。未知工具要报错，不执行任意函数。不要把结果写死为 95，替换输入仍应有效。

先用一句话说清：`call["id"]` 在请求和回复之间起什么作用？再补全函数。默认运行只用手工构造的助手调用消息；它不是模型生成证据。完成后可选择 `--live` 感受真实往返；没有另加一道结构化输出作业。

## 验收与常见问题

- 能说明工具对象的构造、绑定、请求与执行分别在哪一步发生。
- 能从 `AIMessage.tool_calls` 找到名称、字典参数和调用 ID；保留请求消息并返回匹配的 `ToolMessage`。
- 练习能正确处理不同数字，未知工具和不合法调用被拒绝；当前状态为尚未作答。
- 了解结构化输出实例与字符串、消息对象的区别，以及类型正确不保证事实正确。

| 现象 | 排查方向（未实测的故障仅为排查建议） |
| --- | --- |
| 第一次回答正文为空 | 先看 `.tool_calls`；工具请求消息可没有正文 |
| 模型不返回工具调用 | 检查服务能力和 `tool_choice`，不是直接构造假的请求充当成功 |
| 工具参数校验失败 | 查看工具 `.args`，核对字段和类型，不 `eval` 参数 |
| 工具回复被服务拒绝 | 核对助手请求是否在前、调用 ID 是否完全一致、每个调用是否都有结果 |
| 第二次仍要求工具 | 检查是否误用仍强制具名调用的绑定模型；本例用原模型结束 |
| 结构化输出解析失败 | 区分服务不支持、字段缺失、约束不符与模型截断，不只看 HTTP 是否成功 |

## 下一步与资料

下一课把本课明确的请求、执行、返回顺序组织进图，再对比 `ToolNode`、`tools_condition` 与 `create_agent`，并添加可检查的退出条件。

- [LangChain 工具定义](https://docs.langchain.com/oss/python/langchain/tools)
- [模型工具调用与工具循环](https://docs.langchain.com/oss/python/langchain/models#tool-calling)
- [ChatOpenAI 工具调用与结构化输出](https://docs.langchain.com/oss/python/integrations/chat/openai)
- [Pydantic 模型](https://docs.pydantic.dev/latest/concepts/models/)

### 备课清单

- [x] 读取当前进度与相关约定，先写讲义初稿。
- [x] 创建独立示例、补充与练习；验证关键消息配对和失败行为。
- [x] 分别验证真实工具往返与结构化提取，不重复第 05 课环境检查。
- [x] 回填实测，更新课程索引与当前进度，不把备课当作学习验收。
