# 第 07 课：把工具往返组织成有界 Agent 工作流

> 备课状态：可学习（2026-10-26，26 项离线测试通过，手写图和 create_agent 分别完成真实工具往返）。前课调用 ID 配对的具体预测尚未作答，不据此补记为已掌握。

## 场景与目标

上一课把“模型请求工具 → Python 计算 → 模型回答”固定写成两次请求。如果模型读到工具结果后还需要工具，谁负责继续？如果一直要求调用，怎样停止？

本课围绕同一个加法工具做两种实现：先手写 LangGraph，明确状态、工具节点、路由和次数上限；再看 LangChain 的 `create_agent` 如何封装同类循环。

目标是独立解释一次执行：模型返回什么、工具结果怎样进入状态、谁决定走哪条边，以及“得到答案”与“达到上限停止”有什么区别。这里只注册一个工具，没有多智能体，也没有跨调用记忆。

## 前置知识与环境

- 能阅读消息列表、节点返回的部分更新、条件边；第 06 课加法工具练习已通过本地代码查验，独立解释与真实练习运行仍待确认。
- 沿用已安装的 Python 3.12.13、LangChain 1.4.6、langchain-core 1.6.12、LangGraph 1.2.16、langchain-openai 1.7.2 和 python-dotenv 1.2.4。本课不新增依赖。
- 模型、消息和工具协议继续用已有配置；每份模型脚本各自用 `dotenv_values` 直接读取根目录 `.env` 并初始化，不导入其他示例。
- 继续使用 `max_tokens=512`、`max_retries=0`、`extra_body={"enable_thinking": False}` 等已用参数，不重复安装或重测所有模式。

## 文件与命令

配套文件均已创建，各自独立，不加载其他示例：

| 内容 | 路径 |
| --- | --- |
| 手写图 | [demo.py](../../examples/07_agent_workflow/demo.py) |
| 封装对照 | [demo_create_agent.py](../../examples/07_agent_workflow/demo_create_agent.py) |
| 一道路由练习 | [exercise.py](../../exercises/07_agent_workflow/exercise.py) |
| 关键行为验证 | [test_07_agent_workflow.py](../../tests/test_07_agent_workflow.py) |

```powershell
# 手写图：真实模型最多请求三次，默认预期一次工具往返后结束
uv run python examples/07_agent_workflow/demo.py

# 独立的封装对照：真实模型最多请求三次
uv run python examples/07_agent_workflow/demo_create_agent.py

# 练习默认只判断三份手工状态，不读取 .env，不请求模型
uv run python exercises/07_agent_workflow/exercise.py

# 补全练习后，可选择真实运行自己的路由图
uv run python exercises/07_agent_workflow/exercise.py --live
```

## 从数据变化看循环

```text
START → model ──没有工具调用──→ END
          │
          ├─有调用且尚有额度─→ tools ─→ model
          │
          └─有调用但额度耗尽─→ stop ─→ END
```

图的骨架由程序确定；模型是否返回 `tool_calls` 影响实际路径。与第 06 课强制指定工具并固定请求两次不同，本课允许模型选择工具或直接回答。这是带边界的工具型 Agent 循环，不代表模型能修改图结构或随意执行 Python。

对“调用 add_numbers 计算 37 加 58”的预期状态变化：

| 时点 | 状态中的消息 | `model_calls` | `status` |
| --- | --- | --- | --- |
| 输入 | 系统规则、用户问题 | 0 | `running` |
| 第一次模型后 | 再加一条携带工具请求的 `AIMessage` | 1 | `running` |
| 工具后 | 再加一条 `ToolMessage(content="95")` | 1 | 不变 |
| 第二次模型后 | 再加一条最终 `AIMessage` | 2 | `completed` |

工具节点不增加模型请求计数。该表与本次真实运行一致；不同输入或模型可能直接回答，不能写死为一定两次。

## 1. 消息状态与部分更新

```python
from langgraph.graph import MessagesState

class AgentState(MessagesState):
    model_calls: int
    status: str
```

`MessagesState` 已为 `messages` 配置 `add_messages`，新消息按 ID 合并；另外两个字段默认覆盖。模型节点返回的更新形如：

```python
response = bound_model.invoke(state["messages"])
return {
    "messages": [response],
    "model_calls": state["model_calls"] + 1,
    "status": "running" if response.tool_calls else "completed",
}
```

`response` 为 `AIMessage`；返回字典表示三个字段的状态更新，不是最终答案字符串。节点只返回本次新增消息，框架负责与旧消息合并。不重新返回整个历史，也不手动丢掉用户问题。

## 2. ToolNode 自动执行已有工具请求

```python
from langgraph.prebuilt import ToolNode

tool_node = ToolNode([add_numbers], handle_tool_errors=False)
```

`ToolNode` 从 `langgraph.prebuilt` 导入。构造时注册允许执行的工具，不请求模型、不立即计算。`handle_tool_errors=False` 让执行或参数校验异常继续抛出，便于本课明确观察失败，不把失败当正常结果。

它作为图节点收到当前状态，读取最后一条助手消息的 `tool_calls`，调用相应工具，并返回新增工具消息的更新：

```text
输入最后消息：AIMessage(tool_calls=[name、args、id])
ToolNode 执行工具
输出更新：{"messages": [ToolMessage(content="95", tool_call_id=原调用 ID)]}
```

因此它替代了上一课手工执行工具和构造 `ToolMessage` 的代码；没有替代模型节点，也不会自己调用模型。工具请求 ID 与回复 ID 仍须配对。

一个助手消息可携带多个调用，`ToolNode` 可执行多个工具；本课通常只有一个。模型请求数上限不等于工具执行总次数。工具错误和未知工具的处理有不同路径，不能笼统保证所有失败都变成同一种异常。

## 3. tools_condition 只判断有没有工具调用

```python
from langgraph.graph import END
from langgraph.prebuilt import tools_condition

destination = tools_condition(state)
```

默认读取 `state["messages"]` 的最后一条消息；若有 `tool_calls`，返回字符串 `"tools"`，否则返回 `END`，其实际字符串为 `"__end__"`。它不执行工具、不增加次数，也没有本课的业务上限。消息为空属于无效输入，不能用空历史代表模型已经给出答案。

本课再包装一层路由：

1. 没有工具调用：结束，即使本次模型次数恰好达到上限，也应接受最终回答。
2. 有工具调用，且模型次数已达上限：走 `stop`。
3. 有工具调用，仍有额度：走 `tools`。

核心是先判断是否已经有答案，再判断还要继续的请求能否获准。条件边映射写成：

```python
builder.add_conditional_edges("model", route_after_model, {
    "tools": "tools",
    "stop": "stop",
    END: END,
})
```

路由返回的是分支标签，不是状态更新。随后 `builder.add_edge("tools", "model")` 让工具结果返回模型。不要同时为模型节点再加一条无条件直达工具的边。

## 4. 三次上限具体限制什么

主示例 `build_graph(bound_model, max_model_calls=3)` 是我们自己写的函数，返回编译后的图，实测类型为 `CompiledStateGraph`。它与上一课 `build_chain` 类似，负责组合执行结构；内部定义节点时不运行节点，也不重新初始化模型。节点函数之后会使用传入的模型对象，这种引用外层变量的写法叫闭包（closure），所有代码仍在同一文件。

`graph.invoke(initial_state, config={"recursion_limit": 12})` 才实际执行，返回普通 `dict`，包含消息列表、次数和状态。

- `max_model_calls=3` 是本课自己实现的模型节点调用上限，不是 LangGraph 自带参数。
- 第三次模型返回最终答案：`completed`，正常结束。
- 第三次模型仍要求工具：不再执行这一轮工具，`stop` 节点只更新 `status="limit_reached"`，以非零退出码报告未完成。
- 最后一个未执行请求仍留在最终状态中，供诊断；不能把它当完整答案，不能直接接着发送新模型请求而漏掉工具配对。
- `recursion_limit=12` 是执行图的超级步（superstep）安全界限，不等于 12 次模型请求。它只是额外防护，不能代替业务次数限制。超出时抛出 `GraphRecursionError`。

主示例的 `stop` 不生成伪造的模型回答、不补虚假的工具结果，也没有重试循环。

## 5. 同类循环用 create_agent 怎么写

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware

agent = create_agent(
    model=model,
    tools=[add_numbers],
    system_prompt="使用加法工具计算，按工具结果用简体中文回答。",
    middleware=[ModelCallLimitMiddleware(run_limit=3, exit_behavior="error")],
)
result = agent.invoke({"messages": [HumanMessage(content="请计算 37 加 58。") ]},
                      config={"recursion_limit": 24})
```

这里 `HumanMessage` 仍从 `langchain.messages` 导入。模型对象在当前文件直接初始化；不要把手写图里的 `bound_model` 传给这个例子强制重复选工具。`create_agent` 按工具列表组织绑定与执行。

| 调用 | 得到什么 | 发模型请求？ |
| --- | --- | --- |
| `ModelCallLimitMiddleware(...)` | 调用次数限制中间件对象 | 否 |
| `create_agent(...)` | 可运行的编译图，本次为 `CompiledStateGraph` | 否 |
| `agent.invoke({"messages": [...]})` | 最终状态字典，不是字符串 | 是，根据实际循环次数 |
| `result["messages"][-1]` | 正常结束时预期为最终 `AIMessage` | 否，只读已有结果 |

中间件（middleware）是在既有流程上插入限制等行为的组件。本课只学习次数限制：`run_limit=3` 限制单次运行的模型调用，`exit_behavior="error"` 达到限制后若还要请求，抛出 `ModelCallLimitExceededError`，不返回伪装完成的回答。默认 `exit_behavior` 是 `"end"`，本课显式覆盖；没有设置跨运行的 `thread_limit`。

`create_agent` 的停止检查时点与手写图不同：达到上限的模型若提出工具调用，工具仍可能先执行，下一次模型请求前才被中间件拒绝。后续模型调用次数受限，不代表外部工具副作用都被提前阻止。该例只执行本地加法，不做有副作用的操作。

| 比较 | 手写 LangGraph | create_agent |
| --- | --- | --- |
| 模型与工具节点 | 当前文件显式连接 | 框架建立循环 |
| 请求次数限制 | 状态字段与路由自己实现 | 本例显式添加限制中间件 |
| 输出 | 消息和自定义状态字段 | 包含消息等字段的状态字典 |
| 适用点 | 需要控制特定分支和停止时点 | 使用常见工具循环，减少重复连线 |

封装不会提高模型本身的算术或事实能力，也不会自动提供进程重启后的记忆。

## 预期输出与实测

2026-10-26 先执行离线测试，再分别运行本课两份真实示例，没有重新安装依赖或重跑前课能力检查。

```powershell
uv run python -m unittest discover -s tests -p "test_*.py" -v
uv run python examples/07_agent_workflow/demo.py
uv run python examples/07_agent_workflow/demo_create_agent.py
```

| 实测项目 | 结果 |
| --- | --- |
| 完整离线测试 | 26 项通过，退出 `0`；本课新增 8 项 |
| 手写图对象与返回值 | `CompiledStateGraph`，最终为 `dict`，退出 `0` |
| 手写图消息与状态 | `system → human → ai → tool → ai`，工具结果 `95`，调用 ID 配对；`model_calls=2`、`status=completed` |
| create_agent 对象与返回值 | `CompiledStateGraph`，最终为 `dict`，退出 `0` |
| create_agent 消息与结果 | `human → ai → tool → ai`，工具结果 `95`，两条模型消息，最终回答包含 `95` |

系统规则由 `system_prompt` 注入；封装示例的结果状态中本次没有系统消息。这不是规则未发送的证据，不应要求两种实现的返回字典与角色列表完全相同。

这次生成的手写图最终文本为“37 加 58 的结果是 **95**。”，封装版本为“37 加 58 等于 **95**。”；只是模型输出样例，不承诺逐字复现。

| 真实实现 | 第一次请求输入/输出/总 token | 第二次请求输入/输出/总 token | 总耗时 |
| --- | --- | --- | --- |
| 手写图 | `313/37/350` | `370/14/384` | 3.382 秒 |
| create_agent | `313/37/350` | `370/13/383` | 16.112 秒 |

这两次单样本观测不构成性能对比，不能认定封装更慢或更贵；账单费用、并发性能和总体成功率未测。请求都携带关闭思考参数，未额外验证服务内部推理用量。

本课 8 项离线检查覆盖：直接回答不执行工具；工具结果与 ID 正确进入第二次模型上下文；第三次恰好给出答案仍成功；持续请求工具时在第三次模型后停止且仅执行前两轮工具；非法参数异常传播；未知工具产生的错误状态不会继续送模型；封装正常往返；封装限制阻止第四次模型调用。先确认缺少示例实现时测试失败，再实现并运行通过。

`ToolNode` 的未知工具会形成 `status="error"` 的工具消息，因此主示例模型节点还会在请求前检查上一批工具消息；遇到错误就停止，不把它当作成功结果。参数错误则由 `handle_tool_errors=False` 继续抛出。真实服务本次只跑正常路径，上限与错误路径使用离线模型替身验证，没有为重现错误额外消耗模型请求。

练习默认命令 `uv run python exercises/07_agent_workflow/exercise.py` 退出 `1`，提示“请补全 route_after_model，区分正常结束、工具执行和次数上限。”，属于预留任务，未请求模型。`--live` 练习尚未运行，学习者尚未作答；未覆盖前课作答，未创建参考解答。

## 一道核心练习

补全 `exercises/07_agent_workflow/exercise.py` 的 `route_after_model(state)`，返回 `END`、`"tools"` 或 `"stop"`。工具、模型节点和完整建图代码已提供，且全部在当前文件。

先预测三个本地输入，再实现路由：

| 最后助手消息 | `model_calls` | 预期分支 |
| --- | --- | --- |
| 无工具调用的最终回答 | 3 | `END` |
| 有工具调用 | 1 | `"tools"` |
| 有工具调用 | 3 | `"stop"` |

先解释第一行为什么不能判作失败，再填写函数。默认只检查手工状态，未作答会提示 `NotImplementedError`，不产生模型费用；完成后才选择 `--live`。不额外增加一份封装 Agent 作业，不提前创建参考解答。

验收：路由边界与判断顺序正确；能指出 `ToolNode` 的更新合并在哪里发生；能说明调用次数、工具数量与图步数的区别，并区分正常完成和限制退出。

## 效果、限制与排查

- 功能：正常工具往返已真实验证，限制退出和失败路径已离线验证；工具调用和最终文本是不同消息，验证边界见上。
- 质量：固定算术输入便于查验，不据少量演示报告整体成功率；模型也可能不调用工具。
- 性能与成本：两种真实示例各最多三次模型请求，本次各执行两次。每次 512 token、自动重试 0；单次耗时和标准 token 用量见上，费用未测。这不限制输入 token 总数。
- 工具错误：手写 `ToolNode(handle_tool_errors=False)` 的执行异常会传播；主程序显示类别并退出。不能把报错路径描述为已得答案。
- 状态保存：本课没有 checkpointer，两次调用不自动共享对话，跨进程也不持久化。下一课再学习保存与恢复。

| 现象 | 检查方向 |
| --- | --- |
| `ToolNode` 找不到工具请求 | 最后一条是否为带 `tool_calls` 的助手消息，而非纯文本或工具结果 |
| 工具结果丢失 | 消息字段是否使用 `MessagesState`，节点是否返回本次增量 |
| 明明已有最终答案仍判次数耗尽 | 路由应先判断无工具调用的正常结束，再判断继续所需额度 |
| `GraphRecursionError` | 检查循环边与业务停止条件，不能只不断调高执行步数 |
| `ModelCallLimitExceededError` | 限制确实阻止了下一次请求；这属于未完成，不是模型回答 |
| 直接看最后 `.content` 却为空 | 最后可能是待执行工具请求；结合 `tool_calls` 和 `status` 判断 |

## 下一步与官方资料

下一课学习检查点、线程 ID 与暂停恢复。先确认“状态保存在一次执行中”和“跨调用保存状态”是两件事。

- [LangGraph 工作流与 Agent](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- [LangGraph 图与消息状态](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangChain create_agent](https://docs.langchain.com/oss/python/langchain/agents)
- [模型调用次数中间件](https://docs.langchain.com/oss/python/langchain/middleware/built-in#model-call-limit)

### 备课检查

- [x] 读取当前进度与课程约定，先写讲义初稿。
- [x] 编写独立示例、对照、练习及关键行为检查。
- [x] 验证路由、状态增量、次数上限与错误传播；分别验证两种真实实现。
- [x] 回填实测，更新当前进度与课程入口，不虚构前课验收。
