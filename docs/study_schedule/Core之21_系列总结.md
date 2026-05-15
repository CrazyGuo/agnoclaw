# Core 系列 21： 第二系列总结 —— 全栈知识图谱

> 目标：用一张大地图把所有 Core 系列（11-20）串起来，让你看到 agnclaw 作为"AI Agent 框架"的完整骨架。

---

## 一、agnoclaw 的四大层次

先记住这四层，从上到下看：

```
┌─────────────────────────────────────────────────────────────┐
│                    第一层：用户界面                           │
│         CLI（AsyncREPL）          TUI（Textual）              │
│              ↓                        ↓                     │
├─────────────────────────────────────────────────────────────┤
│                    第二层：Agent 核心                         │
│     AgentHarness ←→ SystemPromptBuilder ←→ 技能系统            │
│              ↓                        ↓                     │
├─────────────────────────────────────────────────────────────┤
│                    第三层：工具与后端                         │
│        Tools（Bash/Files/Web/Tasks）   Backends              │
│              ↓                        ↓                     │
├─────────────────────────────────────────────────────────────┤
│                    第四层：运行时基础设施                     │
│      Config  Memory  Teams  Plugins  Runtime  SkillsHub     │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、数据流：从输入到输出

```
用户输入："帮我写一个计算器"
    │
    ▼
┌─────────────────────────────────────┐
│ 1. CLI/TUI 接收输入                   │
│    AsyncREPL.prompt_async()          │
│    或 Textual InputBar               │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│ 2. AgentHarness 预处理                │
│    - 加载 Workspace 文件              │
│    - 注入 Skill（如果激活）           │
│    - 组装 System Prompt              │
│      SystemPromptBuilder.build()     │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│ 3. Agno Agent 处理                   │
│    - 决定用哪个 Tool                 │
│    - 调用 Tool（通过 Backend 执行）   │
│    - 返回 Stream 事件                │
└─────────────────┬───────────────────┘
                  ▼
┌─────────────────────────────────────┐
│ 4. 结果输出                         │
│    - 流式显示到 CLI/TUI              │
│    - 写入 Memory（如果启用）          │
│    - 触发 Hooks（前后置）             │
└─────────────────────────────────────┘
```

---

## 三、配置系统（Core 之 11）

### 3.1 配置从哪里来

```
优先级（从高到低）：
1. 环境变量（AGNOCLAW_xxx）
2. 项目级配置（.agnoclaw/config.toml）
3. 用户级配置（~/.agnoclaw/config.toml）
4. 默认值（HarnessConfig 里的默认值）
```

### 3.2 核心配置项

| 配置项 | 作用 | 默认值 |
|--------|------|--------|
| `model` | 使用哪个 AI 模型 | `claude-sonnet-4-6` |
| `provider` | 模型提供商 | `anthropic` |
| `enable_workspace` | 启用工作区 | `True` |
| `enable_learning` | 启用记忆学习 | `False` |
| `enable_heartbeat` | 启用心跳 | `True` |
| `enable_plugins` | 启用插件 | `True` |
| `permission_mode` | 权限模式 | `accept_edits` |

---

## 四、SystemPromptBuilder（Core 之 12）

### 4.1 提示词是怎么组装的

```
SystemPromptBuilder.build()
    │
    ├── IDENTITY          → "你是 agnclaw，一个 AI Agent"
    ├── TONE_AND_STYLE    → 语气风格指南
    ├── DOING_TASKS       → 任务执行原则
    ├── TOOL_GUIDELINES   → 工具使用指南
    ├── SECURITY          → 安全边界
    ├── GIT_PROTOCOL      → Git 协议规则
    ├── MEMORY_INSTRUCTIONS → Workspace 记忆注入
    ├── SKILL_INSTRUCTIONS → 激活的技能内容
    ├── PLAN_MODE         → 计划模式指令
    ├── HEARTBEAT_CONTEXT → 心跳上下文
    └── LEARNING_INSTRUCTIONS → 学习指令
```

### 4.2 Workspace 文件注入顺序

```
1. AGENTS.md      → Agent 的角色定义
2. SOUL.md        → Agent 的灵魂/个性
3. USER.md        → 用户信息
4. MEMORY.md      → 跨会话记忆
5. HEARTBEAT.md   → 心跳检查说明
```

---

## 五、Tools 全系统（Core 之 13）

### 5.1 工具箱一览

| 工具箱 | 提供的工具 | 用途 |
|--------|-----------|------|
| `BashToolkit` | bash, bash_start, bash_output, bash_kill | 执行命令行 |
| `FilesToolkit` | read, write, edit, glob, grep, list_dir | 文件操作 |
| `WebToolkit` | web_search, web_fetch | 网络搜索和抓取 |
| `TodoToolkit` | create_task, list_tasks, complete_task | 任务管理 |
| `SubagentTool` | subagent | 召唤子代理 |

### 5.2 工具是怎么注册的

```python
class BashToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="bash")
        self.register(self.bash)  # 注册单个工具

    @tool(name="bash", description="Execute a bash command")
    def bash(self, command: str) -> str:
        ...
```

### 5.3 工具执行流程

```
用户/AI 调用 tool
    │
    ▼
AgentHarness._run_tool()
    │
    ├── Runtime Hooks（前置）
    │
    ├── PermissionController.check()
    │     └── 根据 permission_mode 决定是否放行
    │
    ├── PolicyEngine.evaluate()
    │     └── 检查路径安全、网络安全
    │
    ├── Backend 执行
    │     ├── LocalCommandExecutor（本地）
    │     └── SandboxCommandExecutor（沙盒）
    │
    ├── Runtime Hooks（后置）
    │
    └── 返回结果给 Agent
```

---

## 六、后端抽象（Core 之 14）

### 6.1 两大协议

```
CommandExecutor（命令执行协议）
    │
    ├── run()      → 执行命令，等待结果
    ├── start()    → 启动进程，不等待
    ├── output()   → 获取进程输出
    └── kill()     → 终止进程

WorkspaceAdapter（工作区适配器协议）
    │
    ├── read_file()
    ├── write_file()
    ├── glob()
    ├── grep()
    └── list_dir()
```

### 6.2 两套实现

| 实现类 | 用途 | 安全性 |
|--------|------|--------|
| `LocalCommandExecutor` | 直接在主机执行 | 低（但用户可控） |
| `SandboxCommandExecutor` | 在临时会话执行 | 高（隔离环境） |

---

## 七、Runtime 运行时合约（Core 之 15）

### 7.1 五大组件

```
┌─────────────────────────────────────────────────────────────┐
│ Hooks（钩子）                                                  │
│ PreRunHook / PostRunHook — 在工具执行前后调用                   │
├─────────────────────────────────────────────────────────────┤
│ PolicyEngine（策略引擎）                                        │
│ PathGuardrails — 检查文件路径是否安全                           │
│ NetworkGuardrails — 检查网络请求是否允许                         │
├─────────────────────────────────────────────────────────────┤
│ PermissionController（权限控制器）                              │
│ 5 种模式：bypass / accept_edits / medium_review / / / tool_confirmation │
├─────────────────────────────────────────────────────────────┤
│ EventSink（事件槽）                                            │
│ 记录所有运行事件，用于可观测性                                   │
├─────────────────────────────────────────────────────────────┤
│ RuntimeGuardrails（运行时护栏）                                 │
│ 输入/输出过滤                                                  │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 权限模式详解

| 模式 | 含义 | 适用场景 |
|------|------|----------|
| `bypass` | 完全信任，无需确认 | 信任的环境 |
| `accept_edits` | 自动接受 AI 的编辑 | 推荐日常使用 |
| `medium_review` | AI 写的代码需要 review | 审慎场景 |
| `plan` | 只输出计划，不执行 | 安全第一 |
| `tool_confirmation` | 每个工具调用都确认 | 最高安全 |

---

## 八、Memory 记忆系统（Core 之 16）

### 8.1 三层记忆

```
第一层：Workspace 文件（人工维护）
    AGENTS.md, SOUL.md, USER.md, MEMORY.md
    ↓ AI 每次都读取
第二层：LearningMachine（AI 自动学习）
    Per-user: user_profile, user_memory
    Institutional: learned_knowledge, entity_memory, decision_log
    ↓ 存储在数据库
第三层：Session Memory（会话级）
    当前对话的上下文，关闭后消失
```

### 8.2 学习模式

| 模式 | AI 行为 | 说明 |
|------|---------|------|
| `always` | 每次运行后自动学习 | 最激进 |
| `agentic` | AI 决定何时学习 | 推荐 |
| `propose` | AI 提建议，用户审核 | 中等保守 |
| `hitl` | 用户手动批准 | 最保守 |

---

## 九、Teams 多智能体团队（Core 之 17）

### 9.1 三个预设团队

```
research_team
    Researcher → Analyst → Writer
    （搜索 → 分析 → 报告）

code_team
    Architect → Implementer → Reviewer
    （设计 → 编码 → 评审）

data_team
    DataFetcher → DataAnalyst
    （获取数据 → 分析）
```

### 9.2 协调模式原理

```
用户："研究量子计算现状"
    │
    ▼
Team Leader（协调者）
    │
    ├── 分解任务
    │
    ├── 第1步：分配给 Researcher
    │     → "搜索量子计算最新进展"
    │     ← 返回搜索结果
    │
    ├── 第2步：分配给 Analyst
    │     → "分析这些结果，找出关键趋势"
    │     ← 返回分析报告
    │
    ├── 第3步：分配给 Writer
    │     → "撰写最终报告"
    │     ← 返回完整报告
    │
    └── 第4步：返回给用户
```

---

## 十、Plugins 插件系统（Core 之 18）

### 10.1 插件发现方式

```
方式1：Python Entry Points（推荐）
    pyproject.toml:
    [project.entry-points."agnoclaw.plugins"]
    my-plugin = "my_package.plugin"

方式2：显式模块路径
    loader.load_from_path("my_package.plugin")
```

### 10.2 插件可以扩展什么

```python
PluginManifest(
    name="my-plugin",
    tools=[MyToolkit()],           # 添加工具
    skills_dirs=["path/to/skills"], # 添加技能目录
    pre_run_hooks=[my_hook],        # 添加前置钩子
    post_run_hooks=[my_hook],       # 添加后置钩子
    config_overrides={...},         # 修改配置
)
```

---

## 十一、Skills Hub 技能市场（Core 之 19）

### 11.1 ClawHubClient 四大操作

```
search()   → 搜索技能（返回列表）
inspect()  → 查看技能详情
download() → 下载技能到本地
categories() → 列出所有分类
```

### 11.2 技能运行时后端

| 后端 | 用途 |
|------|------|
| `LocalSkillRuntimeBackend` | 本地直接执行 |
| `CommandExecutorSkillRuntimeBackend` | 通过命令执行器 |
| `AutoApproveSkillInstallApprover` | 自动批准安装 |
| `InteractiveSkillInstallApprover` | 交互式批准安装 |

---

## 十二、AsyncREPL 异步交互（Core 之 20）

### 12.1 同步 vs 异步

```
同步 REPL：
    等待输入 → 等待 AI 回复 → 等待输入 → ...
    问题：AI 处理期间无法显示通知

异步 REPL：
    等待输入（可切换）
    ↓
    AI 处理（流式输出）
    ↓
    同时：Heartbeat 检查在后台运行
    ↓
    收到通知就打印在界面上
```

### 12.2 核心机制

```
patch_stdout() → 让标准输出在等待输入时也能打印
prompt_async() → 非阻塞等待输入
notification_queue → 通知队列，异步打印
HeartbeatDaemon → 和 REPL 在同一 asyncio 循环
```

---

## 十三、全局数据流图

```
┌──────────────────────────────────────────────────────────────────┐
│                           用户                                    │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      CLI / TUI 界面                               │
│              AsyncREPL          AgnoClawApp                       │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     AgentHarness                                  │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │ Workspace 文件   │  │ SystemPromptBuilder │  │ Skill Registry │  │
│  │ (AGENTS/SOUL/)  │  │ (15+ Sections)    │  │ (激活的技能)     │  │
│  └─────────────────┘  └──────────────────┘  └─────────────────┘  │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Agno Agent                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Model (LLM)  │  │ Tools (Kits) │  │ Memory (LearningMachine) │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Runtime 层                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ PolicyEngine  │  │ PermissionCtrl │  │ EventSink (日志)        │ │
│  │ (路径/网络安全) │  │ (5 种权限模式)  │  │                         │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Backend 层                                   │
│  ┌──────────────────┐      ┌──────────────────┐                  │
│  │ CommandExecutor  │      │ WorkspaceAdapter │                  │
│  │ (Local / Sandbox)│     │ (Local / Sandbox) │                  │
│  └──────────────────┘      └──────────────────┘                  │
└───────────────────────────────────────────────────────────────────┘
```

---

## 十四、扩展性点睛

### 14.1 想加新工具？
```python
# src/agnoclaw/tools/my_toolkit.py
class MyToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="my_tools")
        self.register(self.my_tool)

    @tool(name="my_tool", description="Do something")
    def my_tool(self, input: str) -> str:
        return f"Done: {input}"

# 在 get_default_tools() 中加入
```

### 14.2 想加新插件？
```python
# 在 pyproject.toml 中注册
[project.entry-points."agnoclaw.plugins"]
my-plugin = "my_package.plugin"

# 提供 agnoclaw_plugin() 函数
def agnoclaw_plugin() -> PluginManifest:
    return PluginManifest(name="my-plugin", tools=[MyToolkit()])
```

### 14.3 想加新团队？
```python
# 在 teams.py 中添加工厂函数
def research_team(...) -> Team:
    return Team(
        name="Research Team",
        mode=TeamMode.coordinate,
        members=[researcher, analyst, writer],
        ...
    )
```

### 14.4 想加新 Runtime 检查？
```python
# 在 runtime/ 下新建模块
class MyGuardrail:
    def evaluate(self, context) -> PolicyDecision:
        ...

# 在 hooks.py 中集成
```

---

## 十五、第二系列完结

从 Core 之 11 到 Core 之 21，我们覆盖了 agnclaw 作为"AI Agent 框架"的完整技术栈：

| 篇目 | 主题 | 核心文件 |
|------|------|----------|
| 11 | 配置系统 | `config.py` |
| 12 | SystemPromptBuilder | `prompts/system.py` |
| 13 | Tools 全系统 | `tools/*.py` |
| 14 | 后端抽象 | `backends.py`, `tools/backends.py` |
| 15 | Runtime 运行时合约 | `runtime/` |
| 16 | Memory 记忆系统 | `memory.py` |
| 17 | Teams 多智能体 | `teams.py` |
| 18 | Plugins 插件系统 | `plugins.py` |
| 19 | Skills Hub | `skills/hub.py`, `skills/backends.py` |
| 20 | AsyncREPL | `cli/async_repl.py` |
| 21 | 系列总结 | 本篇 |

---

## 十六、思考题答案

### 篇 11（配置系统）
1. **为什么需要层级合并？** — 支持多环境（开发/测试/生产），让用户可以在不同层级覆盖配置
2. **环境变量优先级最高** — 确保敏感信息（如 API Key）不泄露到配置文件

### 篇 12（SystemPromptBuilder）
1. **为什么要分这么多 Section？** — 模块化，方便单独修改/调试某个部分
2. **Workspace 文件为什么在最后？** — 用户自定义的内容优先级最高，覆盖框架默认值

### 篇 13（Tools）
1. **Toolkit vs 单个 Tool** — Toolkit 是一组相关工具的容器
2. **为什么要通过 Backend 执行命令？** — 隔离性，Sandbox 可以防止危险操作

### 篇 14（Backends）
1. **Local vs Sandbox** — Local 直接执行，Sandbox 在隔离会话中执行
2. **WorkspaceAdapter 的作用** — 统一文件操作接口，方便切换实现

### 篇 15（Runtime）
1. **PolicyEngine vs PermissionController** — PolicyEngine 检查操作本身是否安全，PermissionController 检查用户是否授权
2. **5 种权限模式** — 从完全信任到最高安全，覆盖不同场景

### 篇 16（Memory）
1. **Workspace 文件 vs LearningMachine** — 前者是人工维护，后者是 AI 自动学习
2. **namespace 的作用** — 隔离不同团队/项目的学习，避免互相干扰

### 篇 17（Teams）
1. **为什么需要协调模式？** — 复杂任务需要分解为多个步骤，不同 Agent 做不同的事
2. **共享数据库的好处** — 对话历史可以跨成员访问

### 篇 18（Plugins）
1. **为什么用 Entry Points？** — 安装即发现，不需要额外配置
2. **插件冲突怎么办？** — 目前没有处理机制，用户需要自己避免

### 篇 19（Skills Hub）
1. **缓存的好处** — 减少网络请求，加快响应速度
2. **安装审批的作用** — 防止恶意技能在后台安装危险包

### 篇 20（AsyncREPL）
1. **为什么需要同一 asyncio 循环？** — 确保 Heartbeat 通知可以随时打断 REPL 等待
2. **patch_stdout 的问题** — 猴子补丁，可能与其他库冲突

---

## 十七、下一步学习

恭喜完成 Core 系列！现在你有两条路：

**路一：深入某个模块**
- 想深入 TUI？→ 回到 TUI 系列，尝试修改 widget
- 想深入工具？→ 查看 `tools/` 目录，添加自己的 toolkit
- 想深入 Runtime？→ 阅读 `runtime/` 下的每个模块

**路二：实际使用**
```bash
# 尝试 AsyncREPL
uv run agnoclaw chat

# 尝试 TUI
uv run agnoclaw tui

# 搜索一个技能
uv run agnoclaw hub search "code review"

# 创建一个团队任务
python -c "from agnoclaw.teams import research_team; ..."
```

---

> 全系列完结！从 TUI 之 01 到 Core 之 21，我们一起探索了 agnclaw 的每一寸土地。祝你在 AI Agent 的世界里玩得开心！
