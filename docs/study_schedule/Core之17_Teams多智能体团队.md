# Core 系列 17： Teams 多智能体团队 —— 协作完成任务

> 目标：小朋友也能看懂！用一个"建筑队"的比喻来讲清楚，agnoclaw 的多智能体团队是如何工作的，如何让多个 AI 协作完成复杂任务。

---

## 一、"建筑队"比喻

想象你要**建一栋房子**：
- **Architect（建筑师）** — 画设计图，规划整体结构
- **Implementer（施工队）** — 按照设计图施工
- **Reviewer（监理）** — 检查施工质量

一个人很难同时做这三件事，但一个团队可以！

`teams.py` 就是这样的"AI 建筑队"，把一个复杂任务分解给多个 AI 去做。

---

## 二、三种预设团队

文件：`src/agnoclaw/teams.py`

### 2.1 research_team —— 研究团队

```
research_team
    ├── Researcher（研究员）— 搜索网页，收集信息
    ├── Analyst（分析师） — 评估信息，找出关键点
    └── Writer（作家） — 写出最终报告
```

```python
def research_team(
    model_id: str | None = None,
    provider: str | None = None,
    config: HarnessConfig | None = None,
    session_id: str | None = None,
    enable_learning: bool = False,
    backend: RuntimeBackend | None = None,
    skill_install_approver: SkillInstallApprover | None = None,
) -> Team:
```

**使用示例：**
```python
from agnoclaw.teams import research_team

team = research_team(model_id="claude-sonnet-4-6")
team.print_response("Research the state of fusion energy in 2026", stream=True)
```

### 2.2 code_team —— 编码团队

```
code_team
    ├── Architect（架构师） — 设计系统，写规格说明
    ├── Implementer（实现者） — 写代码
    └── Reviewer（评审员） — 检查代码，运行测试
```

**使用示例：**
```python
from agnoclaw.teams import code_team

team = code_team(model_id="claude-sonnet-4-6")
team.print_response("Build a REST API for a todo list", stream=True)
```

### 2.3 data_team —— 数据团队

```
data_team
    ├── DataFetcher（数据获取员） — 获取和清洗数据
    └── DataAnalyst（数据分析师） — 分析数据，找出模式
```

**使用示例：**
```python
from agnoclaw.teams import data_team

team = data_team(model_id="claude-sonnet-4-6")
team.print_response("Analyze the sales data from last quarter", stream=True)
```

---

## 三、TeamMode.coordinate 模式

所有预设团队都使用 `TeamMode.coordinate`：

```python
return Team(
    name="Research Team",
    model=model,
    mode=TeamMode.coordinate,  # ← 协调模式
    members=[researcher, analyst, writer],
    ...
)
```

### 协调模式的工作原理

```
任务：研究融合能源现状
    │
    ▼
Team Leader（协调者）
    │
    ├── 第1步：把任务分解
    │   "需要：信息收集 → 分析评估 → 报告撰写"
    │
    ├── 第2步：分配给 Researcher
    │   → "搜索融合能源最新进展"
    │   ← 返回：大量搜索结果和URL
    │
    ├── 第3步：分配给 Analyst
    │   → "评估这些发现，找出共识和争议"
    │   ← 返回：分析报告
    │
    ├── 第4步：分配给 Writer
    │   → "根据分析写最终报告"
    │   ← 返回：完整报告
    │
    └── 第5步：综合输出
        → 最终报告给用户
```

---

## 四、_build_member_agent() 辅助函数

每个团队成员都是一个 `AgentHarness`，由这个函数创建：

```python
def _build_member_agent(
    *,
    name: str,           # 成员名字
    role: str,           # 角色描述（instructions）
    model: str,          # 模型
    cfg: HarnessConfig,  # 配置
    db,                  # 数据库
    tools: list,         # 工具列表
    backend: RuntimeBackend | None = None,
    skill_install_approver: SkillInstallApprover | None = None,
    learning=None,       # LearningMachine
    enable_learning: bool = False,
):
    harness = AgentHarness(
        model=model,
        config=cfg,
        db=db,
        workspace_dir=_tool_workspace_dir(cfg),
        include_default_tools=False,  # ← 不使用默认工具
        tools=tools,                  # ← 只使用指定的工具
        name=name,
        instructions=role,             # ← 角色作为 instructions
        enable_learning=enable_learning,
        debug=cfg.debug,
        backend=backend,
        skill_install_approver=skill_install_approver,
    )
    harness._agent.role = role
    if learning is not None:
        harness._agent.learning = learning
        harness._agent.add_learnings_to_context = enable_learning
    return harness._agent
```

**关键点：**
- 每个成员只获得**需要的工具**，不会获得所有默认工具
- 角色描述作为 `instructions`，告诉 AI 它的职责

---

## 五、每个团队的工具配置

### 5.1 research_team

```python
researcher = _build_member_agent(
    name="Researcher",
    role="Find factual information from multiple sources...",
    tools=[web, TodoToolkit()],  # ← 只有网页搜索和待办
    ...
)

analyst = _build_member_agent(
    name="Analyst",
    role="Critically evaluate research findings...",
    tools=[TodoToolkit()],  # ← 只有待办
    ...
)

writer = _build_member_agent(
    name="Writer",
    role="Produce clear, structured reports...",
    tools=[],  # ← 不需要工具
    ...
)
```

### 5.2 code_team

```python
architect = _build_member_agent(
    name="Architect",
    tools=[files, TodoToolkit()],  # ← 文件读写 + 待办
    ...
)

implementer = _build_member_agent(
    name="Implementer",
    tools=[files, bash, TodoToolkit()],  # ← + bash
    ...
)

reviewer = _build_member_agent(
    name="Reviewer",
    tools=[files, bash],  # ← 没有待办（不需要规划）
    ...
)
```

### 5.3 data_team

```python
fetcher = _build_member_agent(
    name="DataFetcher",
    tools=[
        WebToolkit(),
        FilesToolkit(workspace_dir=workspace_dir, adapter=resolved_workspace_adapter),
        make_bash_tool(...),  # ← 用于数据处理
    ],
    ...
)

analyst = _build_member_agent(
    name="DataAnalyst",
    tools=[
        FilesToolkit(...),
        make_bash_tool(...),
    ],
    ...
)
```

---

## 六、共享存储和 Learning

### 6.1 共享数据库

```python
db = _make_db(cfg)  # 创建数据库

researcher = _build_member_agent(..., db=db, ...)
analyst = _build_member_agent(..., db=db, ...)
writer = _build_member_agent(..., db=db, ...)

return Team(
    ...,
    db=db,  # ← 共享数据库
)
```

所有成员共享同一个数据库，这样：
- 对话历史可以跨成员访问
- 学习内容可以跨成员共享

### 6.2 共享 LearningMachine

```python
if enable_learning:
    from .memory import build_learning_machine
    _learning = build_learning_machine(db=db, namespace="research-team")

    researcher = _build_member_agent(
        ...,
        learning=_learning,
        enable_learning=enable_learning,
    )
```

团队成员共享同一个 `LearningMachine`，学习会在团队内共享。

---

## 七、团队指令（Instructions）

```python
return Team(
    name="Research Team",
    ...
    instructions=(
        "1. Have the Researcher gather comprehensive information from multiple sources.\n"
        "2. Have the Analyst evaluate and synthesize the findings critically.\n"
        "3. Have the Writer produce a well-structured final report with citations.\n"
        "Do not skip steps. The final output must include sources."
    ),
    show_members_responses=True,  # ← 显示每个成员的响应
    markdown=True,
)
```

`show_members_responses=True` 意味着你会看到：
```
Researcher: 找到了20篇相关论文...
Analyst: 这些论文中有3个关键主题...
Writer: 最终报告已完成...
```

---

## 八、完整使用示例

```python
from agnoclaw.teams import research_team

# 创建团队
team = research_team(
    model_id="claude-sonnet-4-6",
    enable_learning=True,  # 启用学习
)

# 运行任务
team.print_response(
    "Research the state of fusion energy in 2026",
    stream=True,
)

# 查看团队成员响应
# （show_members_responses=True 已设置）
```

---

## 九、自定义团队

你也可以创建自己的团队：

```python
from agnoclaw.agent import AgentHarness
from agnoclaw.teams import _build_member_agent
from agno.team import Team, TeamMode

# 定义成员
designer = _build_member_agent(
    name="Designer",
    role="Create beautiful UI designs...",
    model="claude-sonnet-4-6",
    tools=[FilesToolkit(), TodoToolkit()],
    ...
)

developer = _build_member_agent(
    name="Developer",
    role="Implement designs in code...",
    model="claude-sonnet-4-6",
    tools=[FilesToolkit(), BashToolkit(), TodoToolkit()],
    ...
)

# 创建团队
my_team = Team(
    name="My Custom Team",
    model="claude-sonnet-4-6",
    mode=TeamMode.coordinate,
    members=[designer, developer],
    instructions="1. Have the Designer create the spec...\n2. Have the Developer implement...",
)

# 运行
my_team.print_response("Build a landing page for my product", stream=True)
```

---

## 十、思考题

1. 为什么 `code_team` 中 `Architect` 不需要 `bash` 工具，而 `Implementer` 需要？
2. 如果 `show_members_responses=False`，会发生什么？
3. 为什么每个团队成员需要独立的 `learning_namespace`？如果不隔离会怎样？

---

> 下一篇：《Core 系列 18： Plugins 插件系统 —— 可扩展架构》——深入解析插件的发现和加载机制