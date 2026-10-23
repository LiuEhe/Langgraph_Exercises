# 学习记录

> 本文件为详细历史。新会话默认只读取 [当前进度](progress.md)；下方保留的旧命令和旧实现仅用于追溯，不代表当前代码结构。

<a id="model-call-handoff"></a>

## 模型调用速记与新会话衔接（2026-10-23）

**后续会话直接复用以下结论，不因换了聊天窗口重新安装依赖、检查整套环境或重跑全部模型模式。** 只有配置或依赖变化、实际报错、用户要求验证时，才检查对应部分；新课只补验新增能力。下方历史记录中的待办不要求每次会话启动时自动执行。

1. **已有环境**：项目 `.venv` 和 `uv.lock` 已就绪；langchain-openai 1.7.2 已安装，`uv sync --locked` 已成功，无需重复 `uv add`。
2. **加载配置**：第 05 课示例和练习均支持直接 `uv run python 脚本路径`；入口复用示例的 `restart_with_env`，缺少配置时自动通过 uv 加载根目录 `.env` 并重启一次，避免循环。显式 `uv run --env-file .env ...` 仍可用，直接调用 `build_model()` 时需由调用方先加载环境。现有 `.env` 已配好，不覆盖、不输出私有值；Python 用 `os.environ` 读取。
3. **构造模型**：复用 [第 05 课示例](../examples/05_model_calls/demo.py) 的 `build_model()`。`openai_compatible` 映射到 `model_provider="openai"`；其余 `LLM_*` 显式映射到 `model/api_key/base_url/timeout`。当前参数为 `max_tokens=512`、`max_retries=0`、`use_responses_api=False`、`stream_usage=False`，另加 `extra_body={"enable_thinking": False}` 默认关闭思考模式。构造对象不发请求。
4. **执行调用**：`prompt.invoke(变量字典).to_messages()` 得到消息列表，再用 `model.invoke(messages)` 发一次请求，得到 `AIMessage`；读取 `.content`、结束原因和用量。`StrOutputParser().invoke(response)` 只在本地取文本；当前返回 `str` 子类 `TextAccessor`，用 `isinstance(text, str)` 判断。
5. **复用验证结果**：同步、流式、批量、管道、异步均已真实验证；工具调用、结构化输出尚未验证。128 token 曾全部耗在推理上导致空正文，512 本次成功；遇到空正文先看 `finish_reason` 和用量，不重复排查已确认的环境。

需要实际调用时，默认命令仅发一次请求；不为日常读讲义或修改文档执行它：

```powershell
uv run python examples/05_model_calls/demo.py
# 仅在需要检查配置时使用；不发模型请求
uv run python examples/05_model_calls/demo.py --mode check
```

后补设置：按用户要求关闭思考模式，采用当前 Qwen 接口的 `extra_body={"enable_thinking": False}`（[官方说明](https://www.alibabacloud.com/help/zh/model-studio/deep-thinking)）。本次仅修改参数与文档，未重新调用模型；此前耗时、推理 token 数据属于修改前，不能当作关闭思考后的实测。后续正常调用时观察是否生效，不因此重跑所有模式。

最新验证：直接运行 `uv run python examples/05_model_calls/demo.py --mode check` 已退出 `0`，自动加载配置成功，未请求模型；`uv run python -m unittest discover -s tests -p test_05_model_config.py -v` 的本课 6 项检查均通过，包含此前待补的空流边界。此前完整测试曾有 13 项通过，本次只复查相关课程，未重跑当前全套 14 项。关闭思考参数仍待下次正常请求时观察，不专门重跑服务模式。学习者参照答案修正后的管道已通过离线检查，独立原理解释与真实练习运行尚未验收。

## 2026-10-21：第 01 课修改后检查

- 本次目标：复查字段拼写修正和问题长度计算。
- 学习者证据：已将字段名统一为 `question`，并在长度节点加入 `len(state["question"])`；节点仍只返回 `question_length` 的更新。
- 实测：运行 `uv run python exercises/01_state_node_edge/exercise.py`，退出码 `0`，原先的 `KeyError` 不再出现，但长度字段为字符串 `长度：5`。
- 边界检查：通过 PowerShell 向 `uv run python -` 输入临时校验，分别调用现有图。输入 `State` 得到字符串 `长度：5`，输入空字符串得到字符串 `长度：0`；两例均保留原问题和前一节点的答案，均不满足整数长度要求。
- 待巩固：`len(...)` 的整数结果放进格式化字符串后会变成字符串；状态中的 `int` 类型声明不自动校验或转换该值。函数返回类型目前仍标为 `dict[str, str]`，需随返回整数更新调整。
- 下一步：直接返回整数长度并调整返回类型，再复查两种输入；让学习者解释部分更新为何保留其他字段。本课仍为练习中，尚未验收；“最多检索三次”思考题仍待作答。
- 文件：[练习](../exercises/01_state_node_edge/exercise.py)、[讲义](lessons/01_state_node_edge.md)。导师本次未修改练习代码。

### 概念反馈：覆盖规则与类型提示

- 学习者正确预测：长度节点额外返回 `{"answer": ""}` 时，答案会被覆盖为空字符串；这是一次字段覆盖规则的作答证据，不代表整课已验收。
- 新疑问：为什么长度字段实际返回字符串仍能运行。讲解重点为 `TypedDict` 的类型提示与运行时校验的区别，以及本课图按字段管理状态但不自动校验或转换字段值。
- 下一步：修正整数返回后复查代码，确认能区分字段名称、声明类型和实际值类型；本轮仅答疑，未重新运行或修改练习。

## 2026-10-22：第 01 课整数返回复查

- 学习者证据：长度节点已直接返回 `len(state["question"])`，不再用格式化字符串包装结果。
- 实测命令：`uv run python exercises/01_state_node_edge/exercise.py`，退出码 `0`；最终状态为 `{'question': 'State', 'answer': '收到问题：State', 'question_length': 5}`。
- 关键行为：通过 `uv run python -` 临时检查现有节点和图，`State`、空字符串两种输入的长度分别为整数 `5`、`0`；节点只返回长度字段，最终状态保留问题和答案，两例断言通过。
- 剩余问题：`measure_question` 仍声明 `-> dict[str, str]`，与实际整数值不一致，需要改为 `-> dict[str, int]`。本次只检查并反馈，未修改学习者代码。
- 当前结论：本次练习的功能检查通过；类型标注待修正，完整概念说明与整课验收尚未完成。
- 下一步：学习者修正返回类型，并能独立解释节点部分更新和类型提示的作用，再衔接默认覆盖与 reducer 的对比。“最多检索三次”思考题仍待作答。

## 2026-10-22：衔接第 02 课默认覆盖与归并器

- 学习者证据：第 01 课长度节点已改为 `dict[str, int]`。导师通过 `uv run python -` 复查 `State`、空字符串的实际值、整数类型、字段保留及返回类型标注，均符合要求。记录为经提示完成的练习代码核对通过，不扩大为独立构图或整课原理全部已验收。
- 本次目标：比较默认覆盖和 `Annotated[list[str], add]` 的列表累积规则，强调节点只返回增量。消息专用归并器调整到第 04 课。
- 备课文件：[讲义](lessons/02_state_reducers.md)、[示例](../examples/02_state_reducers/demo.py)、[练习](../exercises/02_state_reducers/exercise.py)。先写讲义，再创建代码、运行与回填。
- 导师验证：`uv run python examples/02_state_reducers/demo.py`、`uv run python exercises/02_state_reducers/exercise.py` 均退出 `0`；通过 `uv run python -` 临时检查覆盖、初始历史保留、重复记录、空列表不清空、完整历史重复累积、错误类型与练习初始行为，六组检查通过。均为普通函数和模拟步骤，未调用模型。
- 学习者状态：第 02 课已开始讲解，练习尚未作答或验收。导师未改动第 01 课练习与其他学习者文件。
- 下一步：学习者先描述应调整状态声明还是节点返回，再把第 02 课练习改为保留 `["开始", "检索", "回答"]`，并检查空初值。继续巩固类型提示与合并函数的区别；“最多检索三次”思考题仍待作答。

### 第 02 课练习查验

- 学习者证据：已将练习的 `steps` 改为 `Annotated[list[str], add]`，两个节点仍只返回新增记录，未自行拼接完整历史。
- 实测：`uv run python exercises/02_state_reducers/exercise.py` 退出码 `0`，最终状态为 `{'question': 'State', 'steps': ['开始', '检索', '回答']}`。
- 通过 `uv run python -` 临时检查：空初值、`["开始"]`、`["检索"]` 三种初值均正确累积；第三种保留重复的 `检索`，符合拼接语义；原问题保留。另核对了归并器元数据、节点返回增量与不原地修改输入列表，均通过。
- 结论：第 02 课本次代码练习查验通过；学习者尚未独立回答累积结果预测与归并器边界问题，不记录为全部原理已掌握。
- 下一步：条件路由与循环退出条件，结合仍待作答的“最多检索三次”思考题推进。本次未改动学习者练习。

## 2026-10-22：开始第 03 课条件路由与有限循环

- 本次目标：用模拟检索区分节点状态更新与路由标签，按命中与最多三次限制退出；通过 `updates`、`values` 观察执行。
- 备课文件：[讲义](lessons/03_routing_loops.md)、[示例](../examples/03_routing_loops/demo.py)、[练习](../exercises/03_routing_loops/exercise.py)、[测试](../tests/test_03_routing_loops.py)。先写讲义，再写关键行为测试、示例与练习，运行后回填。
- 导师验证：`uv run python examples/03_routing_loops/demo.py` 退出 `0`；`uv run python -m unittest discover -s tests -p "test_*.py" -v` 的 6 项测试全部通过，覆盖第 1/2/3 次命中、始终未命中和第 4 次才命中的上限、路由边界、日志增量以及两种状态流。均为普通函数模拟，未调用模型或真实检索。
- 练习初态：`uv run python exercises/03_routing_loops/exercise.py` 在路由占位处抛出预留 `NotImplementedError`，退出 `1`；保留给学习者实现。当前自动化测试检查导师示例，不代表练习已通过。
- 学习者状态：本课开始讲解，尚未提交路由函数或判断顺序的作答；“最多检索三次”问题仍未验收。前两课已有练习文件均保留。
- 下一步：先解释第 3 次恰好命中时怎样路由，以及成功判断与次数上限的顺序，再独立补全路由函数，运行四种模拟条件。

## 2026-10-23：第 03 课练习查验

- 学习者证据：已实现路由，先判断 `found`，未命中时按 `attempts >= MAX_ATTEMPTS` 停止，否则重试；练习也加入了 `make_initial_state` 和两种状态流观察。
- 实测命令：`uv run python exercises/03_routing_loops/exercise.py` 退出 `0`，第 1/2/3 次命中均及时回答，始终未命中时恰好检索三次并停止。第二次命中案例的 `updates` 输出 3 条节点更新，`values` 输出含初始状态在内的 4 条快照。
- 关键验证：通过 `uv run python -` 在内存中将现有测试模块的示例路径改指学习者练习，运行同一组 6 项检查，全部通过，包含计划第 4 次命中仍在第 3 次停止、路由边界、日志增量与流式输出。此次测试对象是练习，未改写测试文件的默认路径。
- 待清理：路由末尾 `return "retry"` 后还留有不可达的 `raise NotImplementedError`，占位 TODO 也尚未删除；不影响本次运行，已反馈学习者。
- 结论：本次练习功能检查通过，已有“最多检索三次”的代码证据；尚未独立回答路由判断顺序及流式输出预测问题，不记录为全部原理已掌握。本次未修改学习者练习。
- 下一步：清理占位内容，确认能解释第 3 次命中及 `updates`/`values` 的差异，再衔接消息角色与提示词模板。

## 2026-10-23：第 04 课消息角色与提示词模板备课

- 本次目标：组织系统规则、历史消息和当前问题，区分模板格式化与真实模型调用；补充消息 ID 的追加与更正规则。
- 课程文件：[讲义](lessons/04_prompt_messages.md)、[主示例](../examples/04_prompt_messages/demo.py)、[消息状态补充](../examples/04_prompt_messages/demo_message_state.py)、[练习](../exercises/04_prompt_messages/exercise.py)、[状态测试](../tests/test_04_message_state.py)。先写讲义，再编写代码并验证、回填。
- 运行验证：`uv run python examples/04_prompt_messages/demo.py`、`uv run python examples/04_prompt_messages/demo_message_state.py` 均退出 `0`。模板实际返回 `ChatPromptValue`，两条历史形成四条消息；消息图快照条数为 `1 → 2 → 2`，同 ID 更正保留原问题。
- 关键检查：`uv run python -m unittest discover -s tests -p "test_*.py" -v` 共 8 项通过（既有 6 项，本课 2 项）；另通过 `uv run python -` 临时检查角色顺序、空历史、缺少必需变量、字符串历史报错、可选历史、ID 合并与错误插入历史方式，七组检查通过。
- 练习初态：`uv run python exercises/04_prompt_messages/exercise.py` 在 `build_prompt` 占位处抛出 `NotImplementedError`，退出 `1`，保留供学习者作答。自动化测试检查导师示例，不代表练习已通过。
- 学习者状态：仅备课与导师验证完成，本课尚未作答或验收。示例历史与消息图回复均为手工文本，未调用模型、未新增依赖，未改动前课学习者代码。
- 下一步：先描述历史占位符与当前用户模板的区别，再补全 `build_prompt()`，检查有历史和空历史时的角色顺序；理解后阅读消息状态补充。真实模型接入仍在第 05 课。

### 第 04 课首次练习查验

- 学习者证据：已实现 `build_prompt()`，返回 `ChatPromptTemplate`，按系统规则、必需历史占位符、当前用户问题组织消息。
- 实测：`uv run python exercises/04_prompt_messages/exercise.py` 退出 `0`，返回 `ChatPromptValue`；两条历史生成四条消息，角色顺序与历史内容正确。
- 临时检查：通过 `uv run python -` 直接检查练习，空历史生成两条消息，省略必需历史抛出 `KeyError`；这些行为符合要求。
- 待修正：系统模板缺少“请用简体中文回答。”，当前用户模板仅使用 `{question}`，未使用 `{style}`。`.input_variables` 实测为 `['history', 'question', 'subject']`，更换输入字典中的 `style` 不改变当前用户消息，尚不满足题目要求。
- 下一步：在原模板补齐系统规则和 `请用{style}解释：{question}`，再验证不同 style 的实际格式化结果。本次未修改练习，未新增观察脚本；本课仍为练习中，未验收。

### 第 04 课模板练习修改后查验

- 学习者已补齐简体中文系统规则，并在当前用户模板中使用 `{style}` 和 `{question}`。
- `uv run python exercises/04_prompt_messages/exercise.py` 实测退出 `0`，得到 `ChatPromptValue`，四条消息的角色、顺序、历史内容和当前问题均符合要求。
- 通过 `uv run python -` 临时检查：必需变量为 `subject/history/style/question`；更换 style 后当前问题随之变化；空历史生成两条消息；省略 history 或 style 均抛出 `KeyError`。四组检查通过。
- 结论：本次模板代码练习查验通过，记录为经反馈修正后的实现证据；消息状态补充与独立原理解释尚未验收。本次未修改练习或新增代码文件。
- 下一步：观察消息状态补充中的同 ID 更正，理解普通拼接和 `add_messages` 的区别，再衔接真实模型输入输出。

## 2026-10-23：第 05 课真实模型输入输出备课

- 衔接依据：第 04 课模板练习经反馈修正后查验通过，消息状态补充与独立原理说明仍待验收。下一课继续第一阶段，不直接跳到 RAG。
- 本次目标：解释模板值、消息列表、真实 `AIMessage` 与文本的变化；显式映射本地配置，分别观察同步、流式、批量、管道和异步调用。仍只安排一道 `build_chain(model)` 管道组合练习。
- 文件：[讲义](lessons/05_model_calls.md)、[示例](../examples/05_model_calls/demo.py)、[练习骨架](../exercises/05_model_calls/exercise.py)、[离线测试](../tests/test_05_model_config.py)。先写讲义初稿，再写边界测试、示例与练习，运行后回填。
- 环境：新增 langchain-openai 1.7.2、openai 3.37.0；Python 3.12.13、LangChain 1.4.6、langchain-core 1.6.12、LangGraph 1.2.16 保持不变。`uv add langchain-openai` 访问官方 PyPI 超时后，临时使用清华 PyPI 镜像安装成功；依赖声明与锁文件已更新，锁文件记录镜像来源。未覆盖 `.env`，未输出其私有值。
- 真实故障：128 token 预算下默认请求正文为空；一次内存诊断请求确认 `finish_reason=length`、推理 token 为 128，全部耗尽预算。调整为 512，仍关闭自动重试；示例在拒绝空文本前保留结束原因和用量。针对诊断缺失先复现失败，再修复。
- 实测命令：`uv run --env-file .env python examples/05_model_calls/demo.py --mode check` 及默认模式、`--mode stream`、`--mode batch`、`--mode chain`、`--mode async` 均退出 `0`。默认返回非空 `AIMessage`；流式累计 118 块；批量返回两个独立消息且顺序正确；管道返回字符串子类；异步等待后返回消息。默认、流式、批量、管道、异步本次耗时分别为 6.225、9.145、16.540、13.827、17.589 秒，不能作为性能优劣结论。
- 版本细节：本版本 `StrOutputParser.invoke` 实测返回 `TextAccessor`，它是 `str` 子类；通过内存中的手工消息验证 `isinstance(text, str)` 为真、内容与原文相同，已写入讲义。默认生成回答提及“持久化”，讲义明确纠正 State 本身不会自动持久化，不能以调用成功代替内容评估。
- 离线验证：`uv run python -m unittest discover -s tests -p "test_*.py" -v` 共 13 项通过（前课 8 项、本课 5 项）。本课覆盖配置边界、有限正超时、参数映射与预算、空响应诊断；测试不加载真实配置、不请求模型。
- 最后检查发现空流时首个文本时间为 `None`，直接 `round` 会掩盖原本的空响应诊断；已补时间打印保护和第 14 项离线回归测试，但执行未获授权，未运行该新增测试，也未在最终修改后复跑全套。课程状态保持“待验证”，不将当前 14 项记为全部通过。另 `uv sync --locked` 已退出 `0`，锁文件与环境一致。
- 练习初态：`uv run --env-file .env python exercises/05_model_calls/exercise.py` 退出 `1`，提示预留的 `build_chain` 尚未完成，未发送请求。学习者尚未作答或验收；未修改任何已有练习，未创建参考解答，未提交或推送。
- 下一步：有运行授权后先复跑空流边界及全套离线测试，再更新第 05 课备课状态。学习时先补看第 04 课消息状态更新，再描述第 05 课每步返回类型并独立补全管道。工具调用与结构化输出留到第 06 课分别验证。

### 第 05 课启动命令修复

- 用户直接运行 `uv run python examples/05_model_calls/demo.py` 时缺少环境变量；用同一命令加 `--mode check` 复现配置错误，退出 `1`。
- 修复：命令行入口在缺配置时定位根目录 `.env`，通过 uv 加载后重启一次，继承原环境及参数；保护标记防止配置不完整时循环。Windows 路径使用正斜杠，避免 uv 对 env-file 转义解析时丢失反斜杠。未添加依赖、未更改 `.env` 或学习者练习。
- 实测：不带 `--env-file` 的 `--mode check` 退出 `0`；第 05 课 6 项离线测试全部通过，空流边界待办已关闭。未发送模型请求、未重新验证各远程调用模式；关闭思考参数仍待正常调用观察。

### 第 05 课练习加载路径修复与作答反馈

- 根因：练习的 `demo_path` 被改成练习自身，`runpy.run_path` 返回的命名空间不包含示例的 `build_model` 与 `ConfigurationError`，因此先后出现两个 `KeyError`。
- 框架修复：路径改回 `examples/05_model_calls/demo.py`，预先取出配置异常类型；示例与练习共享 `restart_with_env`，练习直接运行也能通过 uv 加载根目录 `.env`。保留学习者 `build_chain` 中全部现有作答。
- 学习者证据：已实现模板格式化、模型调用与文本解析的分步过程；但在构造函数中使用固定 concept 并直接请求模型，且没有返回值，因此返回 `None`，尚不满足“返回可复用管道”的任务。运行框架增加了明确的返回类型提示，避免继续触发含糊的 `AttributeError`；练习仍未验收。
- 验证使用内存中的离线模型替换真实模型构造，确认加载的是示例、所需接口存在，并定位到上述练习返回值问题；没有发送真实请求。另示例配置检查和本课 6 项离线测试均通过。最后补充明确的管道返回值提示后，复查命令未获执行授权，该提示分支未复跑，不记为已验证。
- 下一步：学习者让 `build_chain(model)` 只构造并返回模板、模型、解析器的管道，输入字典交给 main 中的 `chain.invoke`，不在构造时先执行。

### 第 05 课管道练习修改后查验

- 学习者已按请求获得的参考答案，将 `build_chain(model)` 改为返回 `prompt | model | StrOutputParser()`；本次导师未修改练习代码。
- 通过 `uv run python -c` 执行一次性离线检查，使用 `FakeListChatModel` 和回调记录输入：构造管道不调用模型；`条件边`、`State` 两种输入正确替换为系统/用户消息；每次执行返回预期模拟文本，满足 `isinstance(text, str)`。
- 在内存中替换模型初始化并跳过环境重启，执行现有 `main()` 退出 `0`，确认正确加载示例且管道运行一次；再临时模拟返回 `None`，确认退出 `1` 并显示明确提示，不增加模型调用。检查命令退出 `0`，未读真实凭据、未发真实请求。
- 结论：参考答案后的代码实现通过离线功能检查，不扩大为独立实现、真实服务验证或整课原理全部掌握。下一步能解释字典、模板值、模型消息和文本的传递顺序，以及构造管道与执行管道的区别。

## 2026-10-23：进度入口与教学代码简化

- 按用户反馈，新建 `docs/progress.md` 只保留当前状态、验收边界和下一步；AGENTS 及文档入口改为新会话默认只读进度，详细日志按需追溯。
- 示例与练习各自使用 `dotenv_values` 直接读取根目录 `.env`，练习在当前文件显式初始化模型；移除跨文件加载及 uv 重启逻辑，保留学习者已完成的 `build_chain`。新增 python-dotenv 1.2.4。
- `uv run python -m unittest discover -s tests -p "test_*.py" -v` 的 14 项检查通过；示例 `--mode check` 及独立练习的假配置/离线模型检查通过。未发送真实请求；不新增学习者掌握程度结论。
