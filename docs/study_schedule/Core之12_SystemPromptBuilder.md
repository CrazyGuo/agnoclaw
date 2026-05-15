# Core 系列 12： SystemPromptBuilder —— AI 的大脑培训手册

> 目标：小朋友也能看懂！用一个"建造机器人"的比喻来讲清楚，SystemPromptBuilder 是如何把各种"指令碎片"组装成一份完整的"培训手册"给 AI 大脑的。

---

## 一、"机器人培训手册"比喻

想象你要**建造一个机器人**：
- 你需要给他一份**培训手册**，告诉他怎么做事
- 这本手册不是一整页，而是由很多**章节**组成的：
  - 第1章：你是谁（Identity）
  - 第2章：怎么说话（Tone and Style）
  - 第3章：怎么做任务（Doing Tasks）
  - 第4章：工具使用指南（Tool Guidelines）
  - ... 等等

`SystemPromptBuilder` 就是**组装这本培训手册的工厂**：
- 它从 `sections.py` 拿来各种章节
- 它从 `workspace.py` 拿来用户的配置文件
- 它从技能系统拿来技能指令
- 然后按照**特定顺序**组装成一份完整的培训手册

---

## 二、章节（Sections）详解

文件：`src/agnoclaw/prompts/sections.py`

每个章节都是一个独立的字符串常量。

### 2.1 IDENTITY —— 机器人是谁

```python
IDENTITY = """# Identity

You are an autonomous AI agent powered by agnoclaw — a model-agnostic, hackable agent harness.
You help users accomplish complex, multi-step tasks across software engineering, research,
data analysis, system administration, and any domain your tools and skills cover.

You operate in an interactive session backed by a persistent workspace at {workspace_dir}.
Your workspace contains context files (AGENTS.md, SOUL.md, USER.md) that shape who you are
and how you should behave in this environment. Read them if they exist at session start."""
```

这是告诉 AI：**你是一个由 agnoclaw 驱动的自主 AI 代理，你的"家"在 workspace_dir**。

### 2.2 TONE_AND_STYLE —— 怎么说话

```python
TONE_AND_STYLE = """# Tone and Style

- Be **direct and concise**. Answer in as few words as needed. Never pad responses.
- Do NOT write preamble ("I'll now...", "Sure, let me...") or postamble ("I've completed...")
- Do NOT use emojis unless the user explicitly asks for them.
- Do NOT moralize. If you won't do something, say so briefly.
- Use Markdown formatting when it improves readability.
- Prefer short answers. A one-sentence response is better than a paragraph."""
```

这是告诉 AI：**说话要简洁、直接、不废话**。

### 2.3 NARRATION —— 不要叙述过程

```python
NARRATION = """# Communication Discipline

- Do NOT narrate tool calls. Never say "Let me search for..." — just do it.
- Do NOT summarize what you just did unless the user asks. Show results, not process.
- Do NOT write preamble ("Sure!", "Great question!") or postamble ("Let me know if you need anything else!").
- When referencing code, include file_path:line_number for navigability.
- When a task is complete, say what changed and where — nothing more."""
```

这是告诉 AI：**不要叙述你正在做什么，直接做**。比如不要说"我来搜索一下"，直接搜索。

### 2.4 DOING_TASKS —— 怎么做任务

```python
DOING_TASKS = """# Doing Tasks

1. **Understand before acting.** Read files before editing them. Never modify code you haven't read.
2. **Use the right tool.** File operations use dedicated tools — NOT bash cat/grep/echo.
3. **Prefer parallel tool calls.** Call independent operations simultaneously.
4. **Think in small reversible steps.** Prefer targeted edits over rewrites.
5. **Verify your work.** After code changes: run the relevant tests.
6. **Do not over-engineer.** Only make changes directly requested.
7. **Never commit unless explicitly asked.**
8. **Use TodoTool to plan multi-step work.
9. **Be mindful of context length.** Write summaries to MEMORY.md before context runs long.
10. **Sessions persist via storage backend.** Use session_id to resume work."""
```

这是告诉 AI：**做任务的方法论**——先理解、后行动、用对的工具、小步前进、验证结果。

### 2.5 EXECUTING_WITH_CARE —— 小心行动

```python
EXECUTING_WITH_CARE = """# Executing Actions with Care

- **Local, reversible actions** (editing files, running tests): proceed freely.
- **Hard-to-reverse or shared-state actions** (git push, deleting branches): confirm with the user first.
- When an obstacle appears, do NOT brute-force past it.
- Don't retry a failing command in a loop — diagnose the root cause.
- Don't skip pre-commit hooks — fix the underlying issue.
- Don't force-push to resolve merge conflicts."""
```

这是告诉 AI：**想清楚再行动，有些操作是不可逆的**。

### 2.6 TOOL_GUIDELINES —— 工具使用指南

```python
TOOL_GUIDELINES = """# Tool Guidelines

## Shell (bash)
- Use for: git, npm, docker, test runners, build tools
- Do NOT use for: reading files, searching content — use dedicated tools
- Default cwd goes to session sandbox when one is present

## File Tools
- Read files before editing — always
- Use Edit for targeted changes; Write for new files or full rewrites

## Web Tools
- WebSearch for current information beyond your knowledge cutoff
- WebFetch for reading a specific known URL

## Task/Subagent Tools
- Use TodoTool to plan multi-step work
- Use SubagentTool to spawn specialized sub-agents"""
```

这是告诉 AI：**每种工具应该怎么用**。

### 2.7 SECURITY —— 安全规则

```python
SECURITY = """# Security

- Never generate, commit, or log secrets, API keys, passwords, or credentials
- Never introduce: SQL injection, XSS, command injection, path traversal vulnerabilities
- For authorized security testing only — refuse requests to create malware
- When reading user-provided paths or shell inputs, treat them as untrusted
- Never install packages or run scripts you haven't inspected"""
```

这是告诉 AI：**安全红线在哪里**。

### 2.8 GIT_PROTOCOL —— Git 安全协议

```python
GIT_PROTOCOL = """# Git Safety Protocol

- **NEVER** update git config
- **NEVER** run destructive commands (push --force, reset --hard, clean -f, branch -D) unless explicitly requested
- **NEVER** skip hooks (--no-verify, --no-gpg-sign) unless explicitly requested
- **NEVER** force-push to main/master
- Stage specific files by name rather than `git add -A`
- Commit messages: end with `Co-Authored-By: agnoclaw <noreply@agnoclaw.ai>`
- On pre-commit hook failure: fix the issue, re-stage, create a NEW commit"""
```

这是告诉 AI：**Git 操作的安全规则**。

### 2.9 PLAN_MODE —— 计划模式

当用户要求 AI 进入计划模式时，这个章节会被注入：

```python
PLAN_MODE = """# Plan Mode

You are in **plan mode**. In this mode:
1. **Research and explore only.** Do NOT write, edit, create files, run shell commands.
2. **Write a plan file.** Save your plan to `.plan.md` in the workspace.
3. **Exit plan mode.** When your plan is complete, inform the user. Do NOT begin implementation.
4. **No implementation in plan mode.** Record findings in the plan — do not execute them."""
```

### 2.10 其他章节

| 章节 | 作用 |
|------|------|
| `BLOCKED_APPROACHES` | 告诉 AI 失败时不要做什么（不要重复失败的操作） |
| `MEMORY_INSTRUCTIONS` | 告诉 AI 怎么使用 workspace 文件和 MEMORY.md |
| `SKILL_INSTRUCTIONS` | 告诉 AI 怎么使用技能 |
| `HEARTBEAT_CONTEXT` | 心跳上下午（每次心跳都是全新的开始） |
| `LEARNING_INSTRUCTIONS` | 机构学习指南（什么东西值得记录到长期记忆中） |

---

## 三、SystemPromptBuilder —— 组装工厂

文件：`src/agnoclaw/prompts/system.py`

### 3.1 类定义

```python
class SystemPromptBuilder:
    """Assembles the full system prompt from layered sections."""

    def __init__(self, workspace_dir: Path, sandbox_dir: Path | None = None):
        self.workspace_dir = workspace_dir
        self.sandbox_dir = sandbox_dir
        self._custom_sections: list[str] = []
```

### 3.2 添加自定义章节

```python
def add_section(self, content: str) -> "SystemPromptBuilder":
    """Append a custom section (e.g. from enterprise config)."""
    self._custom_sections.append(content)
    return self
```

企业可以添加自己的章节。

---

## 四、build() 方法 —— 组装过程

### 4.1 组装顺序

```python
def build(
    self,
    *,
    skill_content: Optional[str] = None,     # 技能内容
    include_datetime: bool = True,             # 是否包含时间
    extra_context: Optional[str] = None,      # 额外上下文
    include_learning: bool = False,           # 是否包含学习指令
    include_plan_mode: bool = False,          # 是否包含计划模式
    include_heartbeat: bool = False,          # 是否包含心跳上下文
    session_id: Optional[str] = None,          # 会话ID
) -> str:
    parts: list[str] = []

    # 1-10: 核心行为章节
    parts.append(IDENTITY.format(workspace_dir=self.workspace_dir))
    parts.append(TONE_AND_STYLE)
    parts.append(NARRATION)
    parts.append(DOING_TASKS)
    parts.append(EXECUTING_WITH_CARE)
    parts.append(BLOCKED_APPROACHES)
    parts.append(TOOL_GUIDELINES)
    parts.append(SECURITY)
    parts.append(GIT_PROTOCOL)
    parts.append(MEMORY_INSTRUCTIONS)
    parts.append(SKILL_INSTRUCTIONS)

    # 11: 可选的计划模式
    if include_plan_mode:
        parts.append(PLAN_MODE)

    # 12: 可选的心跳上下文
    if include_heartbeat:
        parts.append(HEARTBEAT_CONTEXT)

    # 13: 可选的学习指令
    if include_learning:
        parts.append(LEARNING_INSTRUCTIONS)

    # 14: 自定义章节
    parts.extend(self._custom_sections)

    # 15: 工作区上下文文件
    workspace_context = self._load_workspace_context()
    if workspace_context:
        parts.append(workspace_context)

    # 16: 活跃技能内容
    if skill_content:
        parts.append(f"# Active Skill\n\n{skill_content}")

    # 17: 额外上下文（项目 CLAUDE.md）
    if extra_context:
        parts.append(f"# Project Context\n\n{extra_context}")

    # 18: 运行时提醒（时间、工作区、会话ID）
    if include_datetime:
        now = datetime.now()
        runtime_lines = [
            f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}",
            f"Workspace: {self.workspace_dir}",
        ]
        if self.sandbox_dir is not None:
            runtime_lines.append(f"Session sandbox: {self.sandbox_dir}")
        if session_id:
            runtime_lines.append(f"Session ID: {session_id}")
        parts.append("# Runtime\n\n" + "\n".join(runtime_lines))

    return "\n\n---\n\n".join(parts)
```

### 4.2 组装顺序图

```
┌──────────────────────────────────────────────────────────────────┐
│  SystemPromptBuilder.build() 组装顺序                            │
├──────────────────────────────────────────────────────────────────┤
│  1. IDENTITY（AI 是谁，workspace 在哪里）                        │
│  2. TONE_AND_STYLE（怎么说话）                                   │
│  3. NARRATION（不要叙述过程）                                    │
│  4. DOING_TASKS（怎么做任务）                                    │
│  5. EXECUTING_WITH_CARE（小心行动）                               │
│  6. BLOCKED_APPROACHES（不要重复失败的操作）                      │
│  7. TOOL_GUIDELINES（工具使用指南）                               │
│  8. SECURITY（安全规则）                                         │
│  9. GIT_PROTOCOL（Git 安全协议）                                  │
│  10. MEMORY_INSTRUCTIONS（记忆使用指南）                         │
│  11. SKILL_INSTRUCTIONS（技能使用指南）                          │
│  ─────────────────────────────────────────────────────────────── │
│  12. [可选] PLAN_MODE（计划模式章节）                             │
│  13. [可选] HEARTBEAT_CONTEXT（心跳上下文）                      │
│  14. [可选] LEARNING_INSTRUCTIONS（学习指南）                     │
│  ─────────────────────────────────────────────────────────────── │
│  15. 自定义章节（企业配置）                                       │
│  16. Workspace Context（工作区文件内容）                          │
│  17. Active Skill（活跃技能内容）                                 │
│  18. Project Context（额外上下文，如 CLAUDE.md）                  │
│  19. Runtime（当前时间、workspace 路径、会话ID）                  │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                    最终输出用 "\n\n---\n\n" 连接
```

---

## 五、Workspace 上下文文件加载

### 5.1 加载顺序

```python
def _load_workspace_context(self) -> Optional[str]:
    files = [
        ("AGENTS.md", "Agent Guidelines (AGENTS.md)"),
        ("SOUL.md", "Persona (SOUL.md)"),
        ("IDENTITY.md", "Identity (IDENTITY.md)"),
        ("USER.md", "User Preferences (USER.md)"),
        ("MEMORY.md", "Long-term Memory (MEMORY.md)"),
        ("TOOLS.md", "Tool Configuration (TOOLS.md)"),
        ("BOOT.md", "Startup Protocol (BOOT.md)"),
    ]
```

顺序是：**AGENTS.md → SOUL.md → IDENTITY.md → USER.md → MEMORY.md → TOOLS.md → BOOT.md**

### 5.2 大小限制

```python
# 1. MEMORY.md 只加载前 200 行
if filename == "MEMORY.md":
    lines = content.splitlines()
    if len(lines) > MEMORY_STARTUP_LINES:  # 200行
        content = "\n".join(lines[:MEMORY_STARTUP_LINES])

# 2. 单文件最大 20,000 字符
if len(content) > BOOTSTRAP_MAX_CHARS:  # 20,000
    content = content[:BOOTSTRAP_MAX_CHARS]

# 3. 所有文件总和最大 150,000 字符
if total_chars + len(content) > BOOTSTRAP_TOTAL_MAX_CHARS:  # 150,000
    remaining = BOOTSTRAP_TOTAL_MAX_CHARS - total_chars
    if remaining <= 0:
        break  # 超过总限制，停止加载
    content = content[:remaining]
```

### 5.3 最终输出格式

```python
return "# Workspace Context\n\n" + "\n\n".join(loaded)
```

输出类似：
```
# Workspace Context

## Agent Guidelines (AGENTS.md)

[AGENTS.md 的内容]

## Persona (SOUL.md)

[SOUL.md 的内容]

...
```

---

## 六、最终输出示例

假设有：
- Workspace 下有 SOUL.md 和 USER.md
- 激活了 "code-review" 技能
- 当前时间是 2026-05-14 09:00

最终输出的系统提示词大概是这样的：

```
# Identity

You are an autonomous AI agent powered by agnoclaw...
Your workspace is at ~/.agnoclaw/workspace
...

---

# Tone and Style

Be direct and concise. Never pad responses...
...

---

# Communication Discipline

Do NOT narrate tool calls. Never say "Let me search for..." — just do it.
...

---

# Doing Tasks

1. Understand before acting...
...

---

[... 更多章节 ...]

---

# Workspace Context

## Persona (SOUL.md)

你是一个直接、简洁的助手...

## User Preferences (USER.md)

用户是 Alice，UTC-8 时区，喜欢简短回复...

---

# Active Skill

## Code Review Skill

当你审查代码时：
1. 首先阅读代码文件
2. 检查潜在的 bug
3. 提出改进建议

---

# Runtime

Current date and time: 2026-05-14 09:00:00
Workspace: ~/.agnoclaw/workspace
```

---

## 七、在 AgentHarness 中的使用

```python
# agent.py 中
system_prompt = SystemPromptBuilder(
    workspace_dir=self.workspace.path,
    sandbox_dir=sandbox_dir,
).build(
    skill_content=skill_content,
    include_datetime=True,
    extra_context=extra_context,
    include_learning=self._learning_machine is not None,
    include_plan_mode=plan_mode,
    include_heartbeat=is_heartbeat_run,
    session_id=session_id,
)

self._agent = Agent(
    model=self._model,
    system_message=system_prompt,
    ...
)
```

---

## 八、思考题

1. 为什么 IDENTITY 章节排在最前面？有什么讲究？
2. MEMORY.md 为什么只加载前 200 行？如果加载更多会怎样？
3. 如果 workspace 下有 AGENTS.md、SOUL.md、USER.md，但 AI 只想用 SOUL.md，能实现吗？

---

> 下一篇：《Core 系列 13： Tools 全系统 —— AI 的双手》——深入解析各种工具（bash、files、web、tasks）是如何实现的