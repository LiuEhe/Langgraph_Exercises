# 第 08 课：状态保存、人工暂停与恢复

> 备课状态：可学习（2026-10-26，状态保存、批准/拒绝恢复及 35 项离线测试通过）。本课不读取 `.env`、不请求模型、不新增依赖。前课独立解释仍待确认，不把生成新讲义当作阶段验收。

## 场景与核心目标

上一课的图在一次 `invoke` 内传递状态，但函数返回后，下一次调用并不会自动使用之前的状态。

本课先让计数图在同一线程连续累加，再把“准备草稿 → 审核 → 模拟发布”暂停在审核点，收到外部决定后继续。

核心目标：分清**一次运行内的状态、保存下来的快照、恢复执行时的输入**。你需要知道状态保存在哪里、线程 ID 选择哪份状态，以及恢复时哪些代码会重跑。

“发布”只是把文本写入返回状态的 `published` 字段，不发送消息或修改任何外部系统。草稿是固定的手工示例文本，不是模型生成。

## 前置条件与文件

- 需要会读 `TypedDict` 字典状态、部分更新、条件边；第 07 课路由和完整图已通过离线代码查验，独立解释与真实练习运行未全部验收。
- 沿用 Python 3.12.13、LangGraph 1.2.16 与既有 uv 环境；本课不新增包，不初始化模型。LangChain 已安装但不是本课运行所必需的接口。
- 两份示例与练习各自完整，不加载其他课程脚本。

| 内容 | 位置 |
| --- | --- |
| 状态保存与历史 | [demo.py](../../examples/08_checkpoint_resume/demo.py) |
| 暂停、批准与拒绝 | [demo_interrupt.py](../../examples/08_checkpoint_resume/demo_interrupt.py) |
| 一道恢复练习 | [exercise.py](../../exercises/08_checkpoint_resume/exercise.py) |
| 关键行为检查 | [test_08_checkpoint_resume.py](../../tests/test_08_checkpoint_resume.py) |

从项目根目录运行：

```powershell
uv run python examples/08_checkpoint_resume/demo.py
uv run python examples/08_checkpoint_resume/demo_interrupt.py
uv run python examples/08_checkpoint_resume/demo_interrupt.py --reject
uv run python exercises/08_checkpoint_resume/exercise.py
```

审核决定由脚本预设 `True` 或 `False` 来模拟外部人员输入，不要求你在终端交互。这里验证的是暂停恢复机制，不声称已经接入真实审批界面。

## 1. 同一线程怎样保留状态

计数图只有一个节点：从状态读取 `increment`，把它加到已有 `total`，返回 `total` 更新。

```python
from typing import TypedDict
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver

class CounterState(TypedDict):
    increment: int
    total: int

def add_increment(state: CounterState) -> dict[str, int]:
    return {"total": state.get("total", 0) + state["increment"]}

builder = StateGraph(CounterState)
builder.add_node("add", add_increment)
builder.add_edge(START, "add")
builder.add_edge("add", END)
checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

`InMemorySaver` 从 `langgraph.checkpoint.memory` 导入。构造得到内存检查点保存器，不执行节点，也不立即保存一份业务状态。编译时的 `checkpointer=` 把保存器接到图上，返回可运行的 `CompiledStateGraph`。

检查点（checkpoint）保存某个线程的图状态及继续执行所需的信息；不只是最后一段答案。图执行时框架按超级步保存快照，供后续继续与查看历史。

```python
config_a = {"configurable": {"thread_id": "counter-a"}}
first = graph.invoke({"increment": 2, "total": 0}, config_a)
second = graph.invoke({"increment": 3}, config_a)
```

本次实测与预期一致：

| 调用 | 本次传入 | 节点读到的 `total` | 最终 `total` |
| --- | --- | --- | --- |
| 同一保存器、线程 A 第一次 | `increment=2, total=0` | 0 | 2 |
| 同一保存器、线程 A 第二次 | `increment=3` | 保留的 2 | 5 |
| 同一保存器、全新线程 B | `increment=3` | 未提供，节点取默认 0 | 3 |

`configurable` 内的 `thread_id` 是本应用的线程标识；不是 Python 线程编号、工具调用 ID，也不是当前聊天窗口 ID。配置字典不自动读取用户身份，需要调用方选对标识。

第二次调用只传新的输入字段。若再次传 `total=0`，该输入会覆盖之前保存的总数，结果变成 3；这不是保存器丢了数据。

普通 Python 变量适合单次顺序计算；当你需要跨调用按线程保存图状态、查询历史或暂停恢复时，checkpointer 才有明确用途。

## 2. get_state 读到什么

```python
snapshot = graph.get_state(config_a)
print(snapshot.values)
print(snapshot.next)
```

前提是图已配置 checkpointer，并提供线程配置。`get_state` 只读快照，不执行节点、不重新计算。返回 `StateSnapshot`，本例实测：

| 属性 | 对当前计数例子的实测值 | 用途 |
| --- | --- | --- |
| `.values` | `{'increment': 3, 'total': 5}` | 已保存的业务状态字典 |
| `.next` | `()` | 当前没有待执行节点，运行已结束 |
| `.config` | 含线程和检查点标识的配置字典 | 标识这份快照；本课不手工修改检查点 ID |

暂停例子中 `.next` 实测为 `('review',)`。它说明当前待执行审核节点，不表示恢复时从 Python 暂停行的下一行直接继续。

## 3. get_state_history 是读取历史，不是回退

```python
history = list(graph.get_state_history(config_a))
for item in history:
    print(item.values, item.next)
```

`get_state_history` 返回可遍历的快照序列，`list(...)` 才一次性取出为列表；每项仍是 `StateSnapshot`。本例实测最新快照在前，第一项的 `.values` 与 `get_state(config_a).values` 一致，较早快照中可看到总数 2。

历史也包含输入与节点之间的中间快照，不等于“每次 `invoke` 只存一个”。遍历不会改写当前状态、重新执行或自动回退。数据量大时不应无条件把整段历史装入内存。

本课只读历史；修改状态、选择旧检查点重放与持久化数据库后端留到后续阶段。

## 4. 暂停审核的执行过程

```text
START → prepare（固定示例草稿）→ review（interrupt）
                                    │
                          外部传入 True 或 False
                                    │
                   ┌────────────────┴───────────────┐
                 publish                           reject
                   └────────────────┬───────────────┘
                                   END
```

本例状态字段为：`question`、`draft`、`approved`、`status`、`published`。初始 `approved=None` 表示尚无决定；批准或拒绝后才是布尔值。

```python
from langgraph.types import interrupt

def review(state):
    events.append("review:start")  # 仅用于观察执行次数，不是业务提交
    approved = interrupt({"draft": state["draft"], "question": "是否批准这份草稿？"})
    if not isinstance(approved, bool):
        raise ValueError("审核决定必须是 bool。")
    return {"approved": approved, "status": "approved" if approved else "rejected"}
```

`interrupt` 从 `langgraph.types` 导入，在节点里调用。输入 payload 是可 JSON 序列化的审核说明；它把暂停信息交给图的调用者，不是给模型发送提示词。

第一次走到此处时，审核节点尚未返回状态更新，图挂起该节点，并把控制权交回调用者。不要把 `interrupt` 当作普通的 `input()` 阻塞终端，也不要用宽泛异常捕获把它的控制流程吞掉。

```python
config = {"configurable": {"thread_id": "review-demo"}}
pending = graph.invoke(initial_state, config)
notice = pending["__interrupt__"][0]
print(notice.value)
```

当前版本默认 `invoke` 返回含 `__interrupt__` 的字典；此项是 `Interrupt` 对象的元组，本次 `notice` 的类型名实测为 `Interrupt`，`.value` 是刚才传入的审核字典。调用者可以将它显示给人；本课仅打印，不接入审批平台。

`graph.get_state(config).values` 是已保存的业务状态，`status` 仍为 `awaiting_review`；`.next` 为 `('review',)`，`published` 仍为空字符串。`__interrupt__` 是调用返回的控制信息，不是本例业务状态中自行声明的字段。

## 5. 用 Command 恢复，而不是重新提交初始数据

```python
from langgraph.types import Command

resume_input = Command(resume=True)
result = graph.invoke(resume_input, config)
```

`Command(...)` 构造命令对象，`.resume` 为 `True`，构造时不运行图。恢复依然使用 `graph.invoke`，但输入是命令；使用相同保存器和原 `thread_id` 找到暂停状态。

恢复时发生：

1. `review` 节点从头重新执行，所以前面的 `events.append(...)` 再执行一次。
2. 再走到对应的 `interrupt(...)`，它得到恢复值 `True` 并作为返回值交给 `approved`。
3. 节点返回审核状态更新，条件边走向 `publish`。
4. `publish` 把示例文本放进 `published`，`status=completed`，最终 `.next == ()`。

**不是从暂停点下一行直接继续。** 这也是本例要保留事件列表的原因。`events` 是普通的进程内观察列表，不由 checkpointer 保存，不能把它当作可靠的审计记录。

传入 `False` 时走拒绝分支，`published` 仍为空、`status=rejected`。布尔值 `False` 与字符串 `"false"` 不同；本课应用明确拒绝非布尔决定，不能直接用字符串的真假性做审批。

普通字典 `{"resume": True}` 不等于 `Command(resume=True)`，也不应把最初的 question/draft 再当作恢复命令提交。

## 6. 恢复前检查线程与待执行节点

示例的 `resume_review(graph, config, approved)` 是本课自己写的小函数，核心 API 仍在当前文件：先检查布尔值与 `get_state(config).next`，确认是待审核线程，再调用 `graph.invoke(Command(resume=approved), config)`。

- 新的线程 ID 读不到原线程的暂停任务；函数应拒绝恢复，不能猜测或更换 ID。
- 已完成线程的 `.next` 为空，函数拒绝再次提交审核命令。
- 查快照、决定是否恢复、实际恢复是不同动作；读取快照本身不执行审核或发布。

该检查用于教学中的串行调用，不是并发下的原子锁，也不代表已解决所有重复请求问题。

## 7. 内存保存与外部副作用的边界

`InMemorySaver` 只保存在当前 Python 进程内：

- 同一保存器和线程 ID 可跨多次 `invoke` 保留状态；重新编译图但复用该保存器时仍可读到它。
- 换一个全新的 `InMemorySaver()`，同名线程也没有之前的状态。主示例比较这两种情况，不声称真的重启了进程。
- 进程退出或重启后，内存数据不会自动恢复。数据库保存器留到后续持久化工程课程，不在本课新增服务。

不要在 `interrupt` 前发送邮件、扣款或发布内容：节点恢复会重跑该部分。把动作移到审核后能避免这一次暂停带来的提前执行，但真实动作仍需考虑重试、故障与重复请求的幂等性（idempotency），不能承诺放到后面就永远只执行一次。

## 预期与实测记录

2026-10-26 实际运行：

```powershell
uv run python examples/08_checkpoint_resume/demo.py
uv run python examples/08_checkpoint_resume/demo_interrupt.py
uv run python examples/08_checkpoint_resume/demo_interrupt.py --reject
uv run python -m unittest discover -s tests -p "test_*.py" -v
uv run python exercises/08_checkpoint_resume/exercise.py
```

三条示例命令均退出 `0`。主示例的关键实测输出：

```text
线程 A 第一次： {'increment': 2, 'total': 2}
线程 A 第二次： {'increment': 3, 'total': 5}
新线程 B： {'increment': 3, 'total': 3}
快照类型： StateSnapshot
快照 values： {'increment': 3, 'total': 5}
快照 next： ()
历史快照数量： 6
历史 total（新到旧）： [5, 2, 2, 2, 0, None]
历史读取后的 total： 5
重编译但共享保存器： {'increment': 3, 'total': 5}
换全新保存器： {}
显式覆盖 total 后： {'increment': 3, 'total': 3}
```

历史中的重复数值来自不同执行时点，不能按 `total` 数值去重后就认为是全部历史。最后的 `None` 是那份快照尚无 `total`，由 `.get("total")` 返回默认值，不是节点把总数更新成 `None`。显式覆盖演示放在最后，执行后线程 A 的最新总数为 3；上面总数 5 的快照来自覆盖之前。

| 审核观测 | 批准运行 | 拒绝运行 |
| --- | --- | --- |
| 暂停时 status/next | `awaiting_review` / `('review',)` | 相同 |
| 暂停时 published | `''` | `''` |
| 恢复后 approved/status | `True` / `completed` | `False` / `rejected` |
| 恢复后 published | 原模拟草稿 | `''` |
| 恢复后 next | `()` | `()` |
| 完整事件顺序 | `prepare, review:start, review:start, publish` | `prepare, review:start, review:start, reject` |

中断 payload 的 `draft` 与保存的草稿一致；`review:start` 两次、`prepare` 一次，直接显示恢复会从审核节点开头重跑。这里的“发布”仍只是字段更新，无真实服务副作用。

完整测试实测 `Ran 35 tests`、`OK`，退出 `0`。本课新增 9 项，覆盖线程隔离与累加、输入覆盖、历史顺序与只读、保存器实例的寿命、暂停后批准重跑、拒绝、非法决定、错误/已完成线程以及缺少线程配置。先观察缺少实现时失败，再创建导师代码并运行通过。

练习初态退出 `1`，先显示已暂停及 `True` 输入，再提示“请补全 resume_review，检查线程并用 Command 恢复审核。”。这是预留任务；学习者尚未作答，不用导师测试替代练习验收。未改动前课作答，未创建本课参考解答。

没有模型请求，不记录为真实模型验证；本地耗时、内存占用与生产恢复性能未测。没有使用数据库、重启进程、真实用户界面或并发审核，因此不据此声称这些场景也已验证。

## 一道核心练习

补全 `exercises/08_checkpoint_resume/exercise.py` 的 `resume_review(graph, config, approved)`。其余图、草稿和两个审核输入已给出，代码都在本文件内。

任务：只接受布尔决定；确认当前线程待执行节点包含 `review`；用恢复命令传入决定，返回恢复后的状态。错误线程、已完成线程或非法决定要清楚报错，不静默新建一次审核。

默认运行会分别验证批准与拒绝；还需检查你函数对错误线程、重复恢复和非布尔值的处理。未完成时会在暂停后的恢复函数处提示 `NotImplementedError`，不请求模型，不创建参考解答。

先预测：`review` 中位于 `interrupt` 前的一条打印，暂停一次、恢复一次，总共会执行几次？再补全函数。

验收看点：正确传递同一配置与恢复值；批准才写入模拟发布字段；两条分支均结束；能区分检查状态、恢复执行、重新开始输入及内存保存的寿命。

## 排查与后续衔接

| 现象 | 检查方向，未实测的项只作建议 |
| --- | --- |
| 配了保存器却提示缺配置 | 调用 config 是否有 `configurable.thread_id` |
| 同一线程总数又从零开始 | 是否换了保存器，或输入又覆盖了 `total=0` |
| 等待审核时没有发布结果 | 这是暂停状态，查看 `__interrupt__` 与 `.next` |
| 换了线程无法恢复原审核 | 新 ID 对应新状态；使用原 ID 与原保存器 |
| 恢复时审核前日志出现两次 | 中断节点从头执行，不是从下一行继续 |
| 传 `"false"` 仍被当同意 | 字符串非空；本例应拒绝，使用真正的 `False` |
| 重开程序找不到状态 | 内存保存器不提供进程重启后的持久性 |

第 08 课是第一阶段最后一节计划课程，但备课完成不等于第一阶段通过。先结合前课完成一个包含状态、条件边、工具循环、上限和人工介入的小型整合验收；通过后再决定第二阶段的 RAG 主题，不在这里提前生成完整项目。

- [LangGraph 状态保存](https://docs.langchain.com/oss/python/langgraph/persistence)
- [暂停、恢复与节点重跑](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph 图接口](https://docs.langchain.com/oss/python/langgraph/graph-api)

### 备课检查

- [x] 读取当前进度与约定，先写目标、API、预期行为与一道练习。
- [x] 创建独立示例、审核补充、练习和关键行为检查。
- [x] 验证线程隔离、历史读取、状态覆盖、暂停与批准/拒绝、恢复节点重跑和错误恢复。
- [x] 回填实测与边界，更新当前进度，保留阶段待验收状态。
