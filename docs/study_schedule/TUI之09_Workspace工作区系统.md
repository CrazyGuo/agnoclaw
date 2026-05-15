# TUI 系列 09： Workspace 工作区系统

> 目标：小朋友也能看懂！用一个"多层保险柜"的比喻来讲清楚，工作区是如何管理各种配置文件的，以及文件是如何被加载到 AI 大脑中的。

---

## 一、"多层保险柜"比喻

想象你有一个**多层保险柜系统**：

```
┌──────────────────────────────────────┐
│  第三层：你的私人房间（workspace）   │  ← 最高优先级
│    你自己的文件和设置                │
├──────────────────────────────────────┤
│  第二层：项目办公室（project）       │  ← 中优先级
│    整个团队共享的设置                │
├──────────────────────────────────────┤
│  第一层：公司总部（global）          │  ← 最低优先级
│    公司默认的规则和配置              │
└──────────────────────────────────────┘
```

如果你在自己的房间（workspace）里找不到文件，就去项目办公室（project）找。如果还找不到，就去公司总部（global）找。

这就是 agnoclaw 的**工作区层级系统**！

---

## 二、工作区的目录结构

文件位置：`src/agnoclaw/workspace.py`

### 2.1 默认目录

```
~/.agnoclaw/
├── global/                    # 全局配置（公司总部）
│   ├── SOUL.md
│   ├── USER.md
│   └── ...
├── project/                   # 项目配置（项目办公室）
│   ├── .agnoclaw/
│   │   ├── SOUL.md
│   │   ├── USER.md
│   │   └── ...
│   └── project-files/
└── workspace/                 # 你的私人空间（私人房间）
    ├── AGENTS.md             # 行为指南
    ├── SOUL.md               # 人格设定
    ├── USER.md               # 用户信息
    ├── IDENTITY.md           # 身份设定
    ├── MEMORY.md             # 长期记忆
    ├── TOOLS.md              # 工具偏好
    ├── HEARTBEAT.md          # 心跳检查清单
    ├── BOOT.md               # 启动序列
    ├── skills/               # 技能目录
    ├── memory/               # 每日记忆
    │   └── 2026-05-14.md     # 今天的记忆
    └── sessions/             # 会话记录
```

### 2.2 初始化

```python
def initialize(self) -> None:
    """创建工作区目录和默认文件"""
    self.path.mkdir(parents=True, exist_ok=True)
    (self.path / "skills").mkdir(exist_ok=True)
    (self.path / "memory").mkdir(exist_ok=True)
    (self.path / "sessions").mkdir(exist_ok=True)

    # 创建默认文件（如果不存在）
    self._create_if_missing("AGENTS.md", DEFAULT_AGENTS_MD)
    self._create_if_missing("SOUL.md", DEFAULT_SOUL_MD)
    self._create_if_missing("HEARTBEAT.md", DEFAULT_HEARTBEAT_MD)
```

---

## 三、文件的作用

### 3.1 核心文件一览

| 文件 | 作用 | 优先级 |
|------|------|--------|
| `AGENTS.md` | 行为指南，告诉 AI 怎么做事 | 高 |
| `SOUL.md` | 人格设定，决定 AI 的说话风格 | 高 |
| `USER.md` | 用户信息，知道用户是谁 | 高 |
| `IDENTITY.md` | AI 的身份设定 | 中 |
| `MEMORY.md` | 长期记忆，跨会话记住重要信息 | 中 |
| `TOOLS.md` | 工具偏好，指定用什么工具 | 中 |
| `HEARTBEAT.md` | 心跳检查清单 | 低 |
| `BOOT.md` | 启动序列，开机时执行什么 | 低 |

### 3.2 加载顺序

系统提示词的加载顺序（从高到低）：

```
AGENTS.md → SOUL.md → IDENTITY.md → USER.md → MEMORY.md → TOOLS.md → BOOT.md
```

`BOOT.md` 最后加载，因为它包含的是**启动时就要执行的命令**。

---

## 四、层级查找机制

### 4.1 搜索链

当 `read_file("soul")` 被调用时：

```python
def read_file(self, name: str) -> Optional[str]:
    # 1. 先查 logical name
    filename = WORKSPACE_FILES.get(name, name)

    # 2. 按优先级搜索目录
    search_dirs = [self.path]  # 私人房间（最高）
    if self._project_dir:
        search_dirs.append(self._project_dir)  # 项目办公室（中）
    if self._global_dir:
        search_dirs.append(self._global_dir)  # 公司总部（最低）

    # 3. 第一个找到的就用
    for search_dir in search_dirs:
        path = search_dir / filename
        if path.exists():
            content = path.read_text(encoding="utf-8")
            # ... 处理 MEMORY.md 的行数限制
            return content if content else None

    return None  # 都没找到
```

### 4.2 子类覆盖父类

如果三个层级都有 `SOUL.md`：
- `~/.agnoclaw/global/SOUL.md` → 最低优先级
- `project/.agnoclaw/SOUL.md` → 中优先级
- `~/.agnoclaw/workspace/SOUL.md` → 最高优先级

**只用最高优先级的文件**，不会合并。

---

## 五、文件大小限制

### 5.1 为什么需要限制？

AI 的"脑子"（上下文窗口）大小有限，不能无限塞入内容。所以每个文件都有大小限制。

### 5.2 限制规则

| 文件 | 限制 | 原因 |
|------|------|------|
| 单个文件 | 最多 20,000 字符 | 防止一个文件占用太多空间 |
| 所有文件总和 | 最多 150,000 字符 | 保证总上下文不超限 |
| MEMORY.md | 只加载前 200 行 | 保持启动速度，不加载陈旧记忆 |

### 5.3 MEMORY.md 的特殊处理

```python
if name == "memory" or filename == "MEMORY.md":
    lines = content.splitlines()
    if len(lines) > MEMORY_STARTUP_LINES:  # 200行
        content = "\n".join(lines[:MEMORY_STARTUP_LINES])
```

这样即使 MEMORY.md 有 1000 行，也只加载前 200 行。之后的行不会被自动加载。

**建议：** 把 MEMORY.md 作为索引，真正的详细笔记放在单独的文件里（如 `debugging.md`、`patterns.md`）。

---

## 六、Workspace 类的主要方法

### 6.1 读取文件

```python
def read_file(self, name: str) -> Optional[str]:
    """读取工作区文件，支持层级查找"""
```

### 6.2 写入文件

```python
def write_file(self, name: str, content: str) -> None:
    """写入工作区文件（只写到私人房间）"""
    filename = WORKSPACE_FILES.get(name, name)
    path = self.path / filename
    path.write_text(content, encoding="utf-8")
```

### 6.3 追加到记忆

```python
def append_to_memory(self, content: str) -> None:
    """追加内容到 MEMORY.md"""
    memory_path = self.path / "MEMORY.md"
    existing = memory_path.read_text(encoding="utf-8") if memory_path.exists() else "# Memory\n"
    memory_path.write_text(existing.rstrip() + "\n\n" + content.strip() + "\n", encoding="utf-8")
```

### 6.4 每日日志

```python
def log_to_daily(self, content: str) -> None:
    """写入今天的每日记忆文件"""
    today = date.today().isoformat()  # "2026-05-14"
    log_path = self.path / "memory" / f"{today}.md"
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else f"# {today}\n"
    log_path.write_text(existing.rstrip() + "\n\n" + content.strip() + "\n", encoding="utf-8")
```

### 6.5 心跳相关

```python
def heartbeat_md(self) -> Optional[str]:
    """读取 HEARTBEAT.md"""
    content = self.read_file("heartbeat")
    if content is None:
        return None
    # 去掉只有标题的行
    meaningful = [
        line for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return content if meaningful else None

def is_empty_heartbeat(self) -> bool:
    """HEARTBEAT.md 是否为空（不需要检查）"""
    return self.heartbeat_md() is None
```

---

## 七、context_files() 方法

`context_files()` 返回所有需要加载到系统提示词的文件：

```python
def context_files(self) -> dict[str, str]:
    """
    加载所有工作区文件。返回 {logical_name: content}。

    加载顺序：AGENTS.md → SOUL.md → IDENTITY.md → USER.md →
             MEMORY.md → TOOLS.md → BOOT.md

    大小限制：
    - 单文件：20,000 字符
    - 总计：150,000 字符
    """
    result = {}
    total_chars = 0

    for name in ("agents", "soul", "identity", "user", "memory", "tools", "boot"):
        content = self.read_file(name)  # 读取文件
        if content:
            # 单文件大小限制
            if len(content) > BOOTSTRAP_MAX_CHARS:
                content = content[:BOOTSTRAP_MAX_CHARS]

            # 总大小限制
            if total_chars + len(content) > BOOTSTRAP_TOTAL_MAX_CHARS:
                break  # 超过总限制，停止加载

            result[name] = content
            total_chars += len(content)

    return result
```

---

## 八、init 命令（agnoclaw init）

当你运行 `agnoclaw init` 时，CLI 会问你几个问题：

```python
# Q1: Agent persona / soul
soul_input = click.prompt("Persona", default="", show_default=False)
# 回答：'Direct and concise. Prefers bullet points. No fluff.'

# Q2: User identity
user_input = click.prompt("User identity", default="", show_default=False)
# 回答：'Alice, UTC-8, prefers brief responses, uses Python 3.12'

# Q3: Agent capabilities
identity_input = click.prompt("Capabilities", default="", show_default=False)
# 回答：'Full-stack developer, expert in Python and React'

# Q4: Default model
model_input = click.prompt("Model ID", default="claude-sonnet-4-6", ...)
# 回答：claude-sonnet-4-6

# Q5: Enable bash tool
enable_bash = click.confirm("Allow bash tool?", default=True)
# 回答：Y
```

然后写入文件：

```python
if soul_input.strip():
    ws.write_file("soul", f"# Soul\n\n{soul_input.strip()}\n")

if user_input.strip():
    ws.write_file("user", f"# User\n\n{user_input.strip()}\n")

if identity_input.strip():
    ws.write_file("identity", f"# Identity\n\n{identity_input.strip()}\n")

# TOOLS.md 记录工具偏好
tools_lines = [
    "# Tool Preferences",
    f"- Preferred model: `{model_input.strip()}`",
    f"- Shell usage: `{'enabled' if enable_bash else 'avoid unless needed'}`",
]
ws.write_file("tools", "\n".join(tools_lines) + "\n")
```

---

## 九、完整流程图

```
agnoclaw tui 启动
    ↓
_build_agent() 创建 AgentHarness
    ↓
AgentHarness.__init__()
    ↓
创建 Workspace(path)
    ↓
读取工作区文件（context_files()）
    ↓
AGENTS.md → SOUL.md → IDENTITY.md → USER.md → MEMORY.md → TOOLS.md → BOOT.md
    ↓
组装系统提示词（SystemPromptBuilder）
    ↓
创建 Agno Agent(self._agent = Agent(...))
    ↓
AgnoClawApp(agent=agent).run()
    ↓
显示 TUI 界面
```

---

## 十、思考题

1. 如果三个层级都有 `SOUL.md`，AI 会用哪个？为什么？
2. MEMORY.md 为什么只加载前 200 行？如果想保留更多记忆怎么办？
3. 为什么 `BOOT.md` 要最后加载？先加载不行吗？

---

> 总结篇：《TUI 系列总结 —— 从命令行到界面的完整旅程》