# TUI 系列 08： Skill 系统 —— 技能是如何工作的

> 目标：小朋友也能看懂！用一个"工具箱"的比喻来讲清楚，SKILL.md 是如何定义一个技能的，以及技能是如何被注入到 AI 大脑中的。

---

## 一、"工具箱"比喻

想象你有一个**工具箱**：
- 工具箱里有各种工具（锤子、螺丝刀、锯子...）
- 每种工具都有特定的用途（锤子用来敲钉子，螺丝刀用来拧螺丝）
- 你可以根据需要选择合适的工具

在 agnoclaw 中，**Skill（技能）**就像一个工具箱：
- 每个技能都有特定的功能（代码审查、搜索网页、调试...）
- 你可以选择一个技能来帮助你完成任务
- AI 会根据技能的内容来执行任务

---

## 二、SKILL.md 的结构

每个技能是一个**目录**，目录里有一个 `SKILL.md` 文件。

### 2.1 目录结构

```
skill-name/
└── SKILL.md    ← 技能的定义文件
```

### 2.2 SKILL.md 的组成

`SKILL.md` 文件分为两部分：
1. **前面部分（Frontmatter）**——元数据，用 `---` 包裹
2. **后面部分（Content）**——技能的指令内容

```markdown
---
name: code-review        # 技能名称
description: 代码审查技能  # 简短描述
user-invocable: true     # 用户是否可以激活
allowed-tools: bash, read, write  # 允许使用的工具
---

## Code Review Skill

当你审查代码时：
1. 首先阅读代码文件
2. 检查潜在的bug
3. 提出改进建议
```

---

## 三、Frontmatter（前面部分）详解

### 3.1 基础字段

```yaml
name: code-review              # 技能名称（必须）
description: 执行代码审查      # 简短描述
user-invocable: true           # 用户是否可以激活（true/false）
disable-model-invocation: false  # 是否禁用模型调用
allowed-tools: bash, read, write  # 允许使用的工具（空=所有工具）
argument-hint: "[files...]"    # 参数提示
```

| 字段 | 含义 |
|------|------|
| `name` | 技能的名字 |
| `description` | 技能是做什么的 |
| `user-invocable` | 用户是否可以用 `/skill` 命令激活它 |
| `allowed-tools` | 技能可以使用哪些工具 |
| `argument-hint` | 用户传入参数时的格式提示 |

### 3.2 OpenClaw 扩展字段

```yaml
metadata:
  openclaw:
    emoji: 🔍                # 显示表情
    os: [darwin, linux]     # 支持的操作系统
    requires:
      bins: [git]          # 必须存在的命令（全部）
      anyBins: [brew, apt] # 至少有一个存在的命令
      env: [GITHUB_TOKEN]  # 必须的环境变量
    install:               # 安装说明
      - type: uv
        package: httpx
      - type: brew
        package: gh
        os: [darwin]       # 只在 macOS 上安装
```

### 3.3 命令派发字段

```yaml
command-dispatch: tool      # 绕过 AI，直接执行工具
command-tool: bash          # 指定要执行的工具
```

---

## 四、Content（内容部分）详解

内容部分包含了 AI 执行这个技能时的具体指令。

```markdown
## Code Review Skill

When performing a code review:
1. Read the file: $ARGUMENTS
2. Check for bugs
3. Suggest improvements
```

### 4.1 占位符：$ARGUMENTS

`$ARGUMENTS` 代表用户传入的参数：

```
用户输入：/skill code-review src/app.py
$ARGUMENTS = "src/app.py"
```

### 4.2 索引占位符：$ARGUMENTS[N]

`$ARGUMENTS[0]` 代表第一个参数，`$ARGUMENTS[1]` 代表第二个：

```
用户输入：/skill search "python" "web"
$ARGUMENTS[0] = "python"
$ARGUMENTS[1] = "web"
```

### 4.3 内联命令：!`cmd`

`!`cmd`` 会执行一个 shell 命令，并把输出插入到内容中：

```markdown
当前 Git 分支：!`git branch --show-current`
当前提交：!`git log -1 --oneline`
```

**注意：** 出于安全考虑，默认情况下内联命令不会执行。

---

## 五、技能的加载过程

### 5.1 发现技能

`SkillRegistry` 会扫描以下目录来找到技能：

```
优先级从高到低：
1. 工作区技能目录    (~/.agnoclaw/workspace/skills/)
2. 用户技能目录      (~/.agnoclaw/skills/)
3. 额外配置的目录    (config.skills_dirs)
4. 内置技能目录      (包内置的技能)
```

### 5.2 解析 SKILL.md

```python
def load_skill_from_path(skill_md_path: Path) -> Optional[Skill]:
    # 1. 读取文件
    post = frontmatter.load(str(skill_md_path))

    # 2. 解析前面部分（metadata）
    metadata = post.metadata
    content = post.content.strip()

    # 3. 提取名称
    name = metadata.get("name") or skill_md_path.parent.name

    # 4. 解析 allowed-tools
    allowed_tools_raw = metadata.get("allowed-tools", [])
    if isinstance(allowed_tools_raw, str):
        allowed_tools = [t.strip() for t in allowed_tools_raw.split(",")]
    else:
        allowed_tools = list(allowed_tools_raw)

    # 5. 构建 Skill 对象
    return Skill(meta=meta, content=content, path=skill_md_path)
```

### 5.3 内容渲染

当技能被激活时，内容中的占位符会被替换：

```python
def render(self, arguments: str = "", *, allow_exec: bool = False, ...):
    content = self.content

    # 替换 $ARGUMENTS[N]
    args_list = arguments.split() if arguments else []
    content = re.sub(r"\$ARGUMENTS\[(\d+)\]", replace_arg_n, content)
    content = content.replace("$ARGUMENTS", arguments)

    # 替换 !`cmd`（如果 allow_exec=True）
    if allow_exec and inline_backend:
        content = re.sub(r"!`([^`]+)`", run_inline, content)

    return content
```

---

## 六、技能的激活过程

### 6.1 用户手动激活

用户在 InputBar 中输入：

```
/skill code-review
```

或者在运行命令时指定：

```
agnoclaw run "审查代码" --skill code-review
```

### 6.2 自动选择（Auto-skill Selection）

当用户没有指定技能时，`AgentHarness` 会把**所有可用技能的描述**注入到系统提示词中，让 AI 自己判断需要哪个技能。

```
系统提示词中包含：
┌─────────────────────────────────────────┐
│ Available skills:                       │
│  • code-review: 执行代码审查             │
│  • web-search: 搜索网页内容             │
│  • debug: 调试助手                      │
└─────────────────────────────────────────┘

AI 会根据用户的问题自动选择合适的技能。
```

### 6.3 技能注入的规则

```
选择性注入原则：
• 如果只有一个技能明显适用 → 加载它
• 如果多个技能可能适用 → 选择最具体的一个
• 如果没有技能适用 → 不加载任何技能
• 每次对话最多加载一个技能（保持上下文精简）
```

---

## 七、技能的安全模型

### 7.1 信任等级

技能根据来源分为不同信任等级：

| 来源 | 信任等级 | 内联命令 | 安装 |
|------|----------|----------|------|
| 内置（builtin） | 高 | 自动执行 | 自动批准 |
| 本地（local） | 中 | 允许执行 | 需要确认 |
| 社区（community） | 低 | 阻止执行 | 需要确认 |

### 7.2 危险字符检测

包名中不允许出现危险字符：

```python
_DANGEROUS_CHARS = re.compile(r'[;&|$`()\[\]{}!#\\\n\r]')
```

### 7.3 URL 检测

不允许从 URL 安装包：

```python
_URL_PATTERNS = re.compile(r'^(https?://|git\+|git://|ssh://|ftp://)')
```

---

## 八、TUI 中的技能选择器

### 8.1 SkillPickerScreen

按 `Ctrl+S` 打开技能选择器：

```
┌─────────────────────────────────────────────────┐
│              选择一个技能                        │
├─────────────────────────────────────────────────┤
│  [ ] code-review   代码审查技能                  │
│  [ ] debug        调试助手                       │
│  [ ] web-search   网页搜索                       │
├─────────────────────────────────────────────────┤
│  Enter 确认    ESC 取消                         │
└─────────────────────────────────────────────────┘
```

### 8.2 斜杠命令补全

在 InputBar 中输入 `/sk` + Tab，会自动补全为 `/skill`。

如果可用技能有 `code-review`，输入 `/sk co` + Tab 会补全为 `/skill code-review`。

---

## 九、完整流程图

```
用户输入：/skill code-review src/app.py
    ↓
InputBar 发送 UserSubmitted
    ↓
AgnoClawApp.on_user_submitted()
    ↓
AgentDriver.send_message(text, skill="code-review")
    ↓
AgentHarness.arun(text, skill="code-review")
    ↓
SkillRegistry.load_skill("code-review")
    ↓
load_skill_from_path() → 解析 SKILL.md
    ↓
skill.render(arguments="src/app.py") → 渲染内容
    ↓
把渲染后的内容注入到系统提示词
    ↓
Agno Agent 处理请求
    ↓
返回结果给用户
```

---

## 十、思考题

1. 为什么每个技能只需要加载一个 SKILL.md 文件，而不是多个？
2. 如果技能内容中使用了 `!`git log``，但 `allow_exec=False`，会发生什么？
3. 为什么要有"选择性注入"原则？加载多个技能不行吗？

---

> 附加篇3：《TUI 之 09： Workspace 工作区系统》——深入解析工作区的层级结构和文件加载机制