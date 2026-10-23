# 第 02 课：默认覆盖与归并器

> 备课状态：可学习。2026-10-22 已实跑离线示例、确认练习初始行为并验证关键合并规则。学习者尚未作答本课练习。

## 本课目标与场景

上一课的节点只返回字段更新，图负责应用更新。本课继续追问：**两个节点先后更新同一个列表，怎样保留两个步骤的记录？**

业务示例仍是知识问答助手，但“检索”和“回答”均用普通 Python 函数写入固定标签，属于模拟步骤，没有查询知识库或调用模型。

只学一个核心能力：选择并解释字段的合并规则。默认规则用新值覆盖旧值；归并器（reducer）可以用旧值和本次更新计算新值。本课先使用列表拼接规则。

## 前置知识与运行条件

- 能读懂第 01 课的 `TypedDict`、节点部分更新、`START → 节点 → END`。
- Python 3.12.13、LangChain 1.4.6、LangGraph 1.2.16（2026-10-22 实查）。本课无新增依赖，不加载 `.env`，不调用模型。
- 项目依赖已声明；首次安装环境执行 `uv sync --locked`，无需重复 `uv add langgraph`。
- 需要认识列表拼接：`["开始"] + ["检索"]` 得到 `["开始", "检索"]`，不会去重。

## 文件位置与运行命令

| 内容 | 路径 |
| --- | --- |
| 讲义 | [02_state_reducers.md](02_state_reducers.md) |
| 导师示例 | [examples/02_state_reducers/demo.py](../../examples/02_state_reducers/demo.py) |
| 学习者练习 | [exercises/02_state_reducers/exercise.py](../../exercises/02_state_reducers/exercise.py) |

所有命令从项目根目录 `D:\project\langgraph` 的 PowerShell 执行：

```powershell
uv run python examples/02_state_reducers/demo.py
uv run python exercises/02_state_reducers/exercise.py
```

## 先用普通 Python 理解合并

不使用框架，也可以描述两种规则：

```python
from operator import add

old = ["开始"]
update = ["检索"]
replaced = update                 # 覆盖：只用新值
accumulated = add(old, update)     # 拼接：得到 ["开始", "检索"]
```

`add(left, right)` 等价于 `left + right`。单个普通列表处理用 Python 即可；多个图节点共同更新状态时，把合并规则放在状态结构中，可以让节点只返回本次增量。

## 状态如何变化

导师示例给同一张图声明三个字段：

```python
from operator import add
from typing import Annotated, TypedDict


class State(TypedDict):
    question: str
    steps: list[str]
    steps_log: Annotated[list[str], add]
```

`steps` 没有指定归并器，使用默认覆盖。`steps_log` 的值仍然是列表；`Annotated` 给类型附带了额外信息，这里由 LangGraph 读取 `add` 作为合并函数。

结合上一课的类型问题：**不是 Python 自动执行类型标注，也不是给字段增加运行时类型校验；是 LangGraph 主动解释这条元数据，调用合并函数。**

```text
START → retrieve（模拟检索）→ answer（模拟回答）→ END
```

两个节点都只返回新发生的步骤：

```python
# retrieve 的返回更新
{"steps": ["检索"], "steps_log": ["检索"]}

# answer 的返回更新
{"steps": ["回答"], "steps_log": ["回答"]}
```

| 时点 | `steps`：默认覆盖 | `steps_log`：使用 `add` |
| --- | --- | --- |
| 初始值 | `[]` | `[]` |
| `retrieve` 完成后 | `["检索"]` | `["检索"]` |
| `answer` 完成后 | `["回答"]` | `["检索", "回答"]` |

`question` 没有被任何节点返回，会一直保留。归并器按字段生效，不会自动把所有列表都改成累积。

## 本课 API 怎样用

| API | 导入路径 | 关键参数、输入与返回 | 本课代码位置 |
| --- | --- | --- | --- |
| `Annotated` | 标准库 `typing` | `Annotated[list[str], add]`：第一个参数是值类型，第二个参数是额外元数据；其含义由读取它的框架决定 | 示例的 `State.steps_log` |
| `add` | 标准库 `operator` | `add(left, right)`；本课两参数均为列表，返回拼接后的新列表，不是原地 `append` | `State.steps_log` 的归并器 |
| `StateGraph` | `langgraph.graph` | `StateGraph(State)` 读取字段结构及其合并配置，返回图构建器 | 示例中的 `builder` |
| `add_node`、`add_edge` | 构建器方法 | 注册普通函数，串行连接 `START → retrieve → answer → END`；均返回构建器 | 示例建图部分 |
| `compile`、`invoke` | 构建器、编译后图的方法 | `compile()` 返回可执行图；`graph.invoke(initial_state)` 在本课默认设置下返回最终状态字典 | 示例中的 `graph`、`main` |

默认覆盖可以理解为“新字段值取本次更新”；自定义归并器可以理解为 `new_value = reducer(old_value, update_value)`。传入 `Annotated` 的是函数对象 `add`，不是提前调用 `add()` 的结果。

普通 Python 对照是手动 `old + update`。图节点使用归并器时应只返回增量：若既在节点内拼接完整历史，又让图拼接，会把历史重复加入。

## 最小示例讲解

完整可运行代码见 [导师示例](../../examples/02_state_reducers/demo.py)。核心节点如下，文件中还打印了输入与更新，便于观察：

```python
def retrieve(state: State) -> dict[str, list[str]]:
    return {"steps": ["检索"], "steps_log": ["检索"]}
```

节点没有改写输入列表，也没有返回整份历史。图在节点返回后，分别按两个字段各自的规则合并。示例会打印节点读到的状态和返回的更新，用来区分“节点做了什么”和“图做了什么”。

## 预期输出与实测结果

固定初始输入：

```python
{"question": "什么是 reducer？", "steps": [], "steps_log": []}
```

预期最终结果如下；2026-10-22 实测与此一致：

```python
{
    "question": "什么是 reducer？",
    "steps": ["回答"],
    "steps_log": ["检索", "回答"],
}
```

实际执行以下命令，两者退出码均为 `0`：

```powershell
uv run python examples/02_state_reducers/demo.py
uv run python exercises/02_state_reducers/exercise.py
```

示例实际输出：

```text
初始状态： {'question': '什么是 reducer？', 'steps': [], 'steps_log': []}
retrieve 读到： {'question': '什么是 reducer？', 'steps': [], 'steps_log': []}
retrieve 返回： {'steps': ['检索'], 'steps_log': ['检索']}
answer 读到： {'question': '什么是 reducer？', 'steps': ['检索'], 'steps_log': ['检索']}
answer 返回： {'steps': ['回答'], 'steps_log': ['回答']}
最终状态： {'question': '什么是 reducer？', 'steps': ['回答'], 'steps_log': ['检索', '回答']}
```

原始练习运行后输出 `{'question': 'State', 'steps': ['回答']}`，符合待修正的覆盖行为，尚未达到练习要求。

另通过 PowerShell 向 `uv run python -` 传入一次性校验代码，调用真实图验证以下情况，退出码 `0`，输出六项 `PASS`：

| 检查 | 实测 |
| --- | --- |
| 空初值、初始 `["开始"]`、初始 `["检索"]` | `steps` 最终均只剩 `["回答"]`；`steps_log` 保留初始值后追加两条记录，已有 `检索` 时重复记录仍在；问题字段保留 |
| 向 `["开始"]` 更新 `[]` | 结果仍为 `["开始"]`，未清空 |
| 节点返回旧历史加新记录 | 图再次拼接，得到 `["开始", "开始", "检索"]` |
| 把字符串 `"检索"` 直接作为列表更新 | 抛出 `TypeError`，未静默伪装为成功 |
| 把 `[123]` 作为列表更新 | 得到 `["开始", 123]`，未校验元素是否为字符串 |
| 未修改的练习骨架 | 原问题保留，步骤只剩最后一次更新，待学习者修正 |

若工具捕获中文输出出现乱码，可先在当前 PowerShell 执行 `$env:PYTHONIOENCODING = "utf-8"` 再运行；本次验证采用此设置。

## 效果与边界

- 功能：已验证配置归并器的字段保留两个步骤，默认字段覆盖旧值，未更新的问题字段保留。
- 质量：固定标签只用于观察状态，不代表检索或回答质量。
- 性能：本地耗时与内存未测；没有模型请求，模型 token、费用不适用。无上限地累积列表会增加内存占用。
- `add` 不会去重，重复更新会重复记录；返回 `[]` 相当于拼接空列表，不能清空已有历史。
- `Annotated[list[str], add]` 不自动校验元素类型。更新的外层若为字符串，列表与字符串拼接会失败；更新为 `[123]` 却可能成功，因此合并成功不等于数据符合声明。
- 本课只有串行固定流程，没有循环、并行或持久化。进程重启与跨调用记忆尚未涉及。
- `MessagesState`、`add_messages` 会在第 04 课结合消息角色与消息 ID 学习，不将普通列表拼接直接等同于消息状态管理。

## 一道核心练习

任务：让 [本课练习](../../exercises/02_state_reducers/exercise.py) 保留完整步骤历史。

骨架已提供两个返回增量的节点，以及初始状态 `{"question": "State", "steps": ["开始"]}`，但 `steps` 仍使用默认覆盖。未修改时实测最后只剩 `["回答"]`；脚本能运行不等于练习完成。

1. 先用一句话说明应修改状态声明还是节点返回，以及原因。
2. 修改 `steps` 的合并配置，使最终值为 `["开始", "检索", "回答"]`。
3. 保持节点只返回本次新增的一条记录，不原地改列表，不在节点内带回旧历史。

如果卡住：检查 `steps` 是否仅声明了类型，还是还告诉了 LangGraph 怎样合并。参考解答在需要或讲评时单独提供。

## 验收方式

- 解释默认覆盖和 `add` 的输入、输出；能指出哪个字段使用哪种规则。
- 独立修改练习中的合并配置，初始 `[]`、`["开始"]` 两种情况下均保留对应完整历史。
- 预测向 `["检索", "回答"]` 再更新 `["回答"]`、再更新 `[]` 分别得到什么；理解不会去重或自动清空。
- 解释为何节点只返回增量，以及为什么归并器不等于类型校验器。

导师验证示例与学习者独立验收分别记录，本次不会预先记录为已掌握。

## 常见问题与排查

以下现象已在本次一次性校验中复现：

| 现象 | 原因 | 排查与修正方向 |
| --- | --- | --- |
| 最后只剩 `["回答"]` | 列表字段只有类型，没有累积配置 | 检查对应字段的 `Annotated` 元数据 |
| 旧记录重复 | 节点返回完整历史，图又应用拼接 | 节点只返回本次新记录 |
| 返回 `[]` 后旧记录仍在 | 旧列表加空列表仍等于旧列表 | 先区分“没有新记录”与“清空历史”的需求，后者不由本课的 `add` 完成 |
| `TypeError`：列表不能与字符串拼接 | 把字符串当作列表字段的更新 | 检查返回值外层是否为列表，不能只看字段名正确 |

## 下一步与官方资料

本次先预测、运行并修改一个合并配置。完成后准备条件路由与有限循环：将步骤记录与“最多检索三次”的退出条件结合；该思考题仍待作答。

- [LangGraph 字段归并器](https://docs.langchain.com/oss/python/langgraph/graph-api#reducers)
- [Python 3.12 Annotated](https://docs.python.org/3.12/library/typing.html#typing.Annotated)
- [Python 3.12 operator.add](https://docs.python.org/3.12/library/operator.html#operator.add)

### 备课检查

- [x] 先写目标、API、数据变化与练习。
- [x] 创建示例与练习。
- [x] 验证关键合并行为并回填实测。
- [x] 更新课程索引与学习记录。
