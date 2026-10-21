# 课程索引

第一阶段先按下表备课，顺序可根据基础调整。以下课题均为规划，尚无对应讲义或代码；状态不代表学习者已掌握。已在聊天中讲过的概念仍需通过练习确认。

| 编号与主题标识 | 主要内容与常用 API | 备课状态 |
| --- | --- | --- |
| `01_state_node_edge` | `StateGraph`、`add_node`、`add_edge`、`compile`、`invoke`；节点部分更新 | 待编写 |
| `02_state_reducers` | `Annotated`、reducer、`MessagesState`、`add_messages`；覆盖与累积 | 待编写 |
| `03_routing_loops` | `add_conditional_edges`、`END`、流式状态更新；最多三次的检索循环 | 待编写 |
| `04_prompt_messages` | `ChatPromptTemplate`、`MessagesPlaceholder`、消息角色；无模型格式化练习 | 待编写 |
| `05_model_calls` | `.env` 参数映射、`init_chat_model`、`invoke`、`stream`、`batch` 与输出解析 | 待编写 |
| `06_tools_structured_output` | `@tool`、`bind_tools`、`ToolMessage`、`with_structured_output`；能力分别验证 | 待编写 |
| `07_agent_workflow` | `create_agent`、`ToolNode`、`tools_condition`；封装 Agent 与手写图对照 | 待编写 |
| `08_checkpoint_resume` | `InMemorySaver`、`thread_id`、`get_state`、`interrupt`、`Command`；初步理解恢复 | 待编写 |

第二至第四阶段沿用根目录 `AGENTS.md` 的八周路线，在第一阶段进展明确后再拆课；第三阶段会进一步学习持久化、恢复和人工介入的工程细节。

新课从 [讲义模板](../lesson-template.md) 开始，按 [教学流程](../teaching-workflow.md) 补齐讲义、示例、练习和验证，再更新这里的状态与实际文件链接。
