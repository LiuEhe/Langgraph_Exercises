# 课程索引

第一阶段先按下表逐课备课，顺序可根据基础调整。目前第 01～05 课材料与必要验证齐全；第 05 课真实模型各模式此前已验证，当前独立读取配置与离线练习已验证，全套 14 项测试通过，后补关闭思考参数尚未请求验证；第 06～08 课仍为规划。备课状态不代表学习者已掌握。

| 编号与主题标识 | 主要内容与常用 API | 备课状态 |
| --- | --- | --- |
| [01_state_node_edge](01_state_node_edge.md) | `StateGraph`、`add_node`、`add_edge`、`compile`、`invoke`；节点部分更新；[示例](../../examples/01_state_node_edge/demo.py) · [练习](../../exercises/01_state_node_edge/exercise.py) | 可学习（2026-10-21 离线验证） |
| [02_state_reducers](02_state_reducers.md) | `Annotated`、`operator.add`、reducer；覆盖与累积；[示例](../../examples/02_state_reducers/demo.py) · [练习](../../exercises/02_state_reducers/exercise.py) | 可学习（2026-10-22 离线验证） |
| [03_routing_loops](03_routing_loops.md) | `add_conditional_edges`、`END`、`stream`；最多三次的检索循环；[示例](../../examples/03_routing_loops/demo.py) · [练习](../../exercises/03_routing_loops/exercise.py) | 可学习（2026-10-22 离线验证，6 项测试通过） |
| [04_prompt_messages](04_prompt_messages.md) | `ChatPromptTemplate`、`MessagesPlaceholder`、消息角色；消息状态补充 `MessagesState`、`add_messages`；[主示例](../../examples/04_prompt_messages/demo.py) · [状态补充](../../examples/04_prompt_messages/demo_message_state.py) · [练习](../../exercises/04_prompt_messages/exercise.py) | 可学习（2026-10-23 离线验证） |
| [05_model_calls](05_model_calls.md) | `.env` 参数映射、`init_chat_model`、`invoke`、`ainvoke`、`stream`、`batch`、`StrOutputParser` 与管道；[示例](../../examples/05_model_calls/demo.py) · [练习](../../exercises/05_model_calls/exercise.py) | 可学习（2026-10-23，真实模型各模式此前已验证，本课 6 项离线检查通过；关闭思考参数尚未实测） |
| `06_tools_structured_output` | `@tool`、`bind_tools`、`ToolMessage`、`with_structured_output`；能力分别验证 | 待编写 |
| `07_agent_workflow` | `create_agent`、`ToolNode`、`tools_condition`；封装 Agent 与手写图对照 | 待编写 |
| `08_checkpoint_resume` | `InMemorySaver`、`thread_id`、`get_state`、`interrupt`、`Command`；初步理解恢复 | 待编写 |

第二至第四阶段沿用根目录 `AGENTS.md` 的八周路线，在第一阶段进展明确后再拆课；第三阶段会进一步学习持久化、恢复和人工介入的工程细节。

当前学习第 05 课，最新验收结论、待巩固点与下一步只看 [当前进度](../progress.md)。详细日志不作为新会话的默认入口。第 05 课示例和练习均在当前文件直接读取 `.env` 并初始化模型，练习不再加载导师示例。

第 02 课先学通用列表合并；消息专用的 `MessagesState`、`add_messages` 已在第 04 课补充部分结合消息角色和消息 ID 讲解。

新课从 [讲义模板](../lesson-template.md) 开始，按 [教学流程](../teaching-workflow.md) 补齐讲义、示例、练习和验证，再更新这里的状态与实际文件链接。
