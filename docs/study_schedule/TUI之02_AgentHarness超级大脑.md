# TUI 系列 02： AgentHarness 超级大脑的秘密

> 目标：小朋友也能看懂！用一个"厨房餐厅"的比喻来讲清楚，AgentHarness 是如何把"用户指令"变成"AI回复"的。

---

## 一、"餐厅"比喻介绍

我们可以把整个 AI 对话系统想象成一家**餐厅**：

| 真实场景 | AI 系统 | 比喻 |
|----------|---------|------|
| 顾客 | 你（用户） | 你走进餐厅点菜 |
| 服务员 | AgentHarness | 接待你，记录你的需求 |
| 厨师 | Agno Agent（大模型） | 真正炒菜的人 |
| 厨房工具 | Tools（工具） | 刀、锅、烤箱——能切菜、炒菜、烤肉 |
| 菜单 | System Prompt | 厨师的培训手册，告诉他怎么做菜 |
| 点菜单 | 用户输入 | "我要一份宫保鸡丁" |
| 完成的菜 | AI 回复 | 一盘热腾腾的宫保鸡丁 |

`AgentHarness` 就是这家餐厅的**服务员**，他接待顾客（你），把需求传给厨师（AI模型），再把做好的菜端回来。

---

## 二、AgentHarness 在代码中的位置

文件：`src/agnoclaw/agent.py`，从第 263 行开始是 `AgentHarness` 类。

```python
class AgentHarness:
    """一个"服务员"，把用户输入发给AI模型，再把AI回复展示给用户。"""
    
    def __init__(self, model=None, provider=None, session_id=None, 
                 workspace_dir=None, debug=False, permission_mode=None, ...):
        # 1. 读取工作区配置
        # 2. 决定用哪个AI模型（claude-sonnet-4-6? gpt-4o?）
        # 3. 创建厨师（Agno Agent）
        # 4. 准备各种工具
```

---

## 三、AgentHarness 的初始化过程

### 3.1 读取工作区文件（Workspace）

当 `AgentHarness` 启动时，它会读取工作区目录下的各种 `.md` 文件：

```
~/.agnoclaw/workspace/
├── SOUL.md      → 机器人的"性格"（怎么说话？）
├── USER.md      → 用户的信息（你是谁？）
├── IDENTITY.md  → 机器人的"身份"（我是谁的助手？）
├── AGENTS.md    → 代理的配置
├── HEARTBEAT.md → 工作计划清单
└── MEMORY.md    → 记忆文件
```

这就像服务员在顾客进门前，先了解一下：
- 顾客喜欢什么口味（USER.md）
- 今天的special是什么（SOUL.md）

### 3.2 决定用哪个"厨师"（模型）

`AgentHarness` 会根据你传入的参数决定用哪个 AI 模型：

```python
# 如果你指定了 model="claude-sonnet-4-6"，provider="anthropic"
# 它会创建一个"会做特定口味菜的厨师"

model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
provider = os.environ.get("ANTHROPIC_PROVIDER", "anthropic")
```

支持的"厨师"（模型提供商）：

- **Anthropic** → Claude 系列（claude-sonnet-4-6, claude-opus-4-7...）
- **OpenAI** → GPT 系列（gpt-4o, gpt-4o-mini...）
- **Google** → Gemini 系列
- **Ollama** → 本地开源模型（qwen3, llama3...）

### 3.3 创建"厨师"（Agno Agent）

真正和 AI 模型对话的是 `agno` 库提供的 `Agent` 类，`AgentHarness` 只是在外面包了一层：

```python
# 这是 AgentHarness 内部创建的"厨师"
self._agent = Agent(
    model=self._model,              # 用什么模型
    system_message=system_prompt,   # 培训手册（怎么说话）
    tools=_all_tools,               # 厨房工具（能做什么）
    session_id=session_id,          # 哪个餐桌（会话）
    markdown=True,                  # 用 Markdown 格式回复
    debug_mode=debug,               # 是否调试
)
```

### 3.4 准备"厨房工具"（Tools）

`AgentHarness` 默认会给厨师准备以下工具：

| 工具 | 能力 |
|------|------|
| BashToolkit | 执行 bash 命令（就像给厨师一把刀） |
| FilesToolkit | 读写文件（切菜板） |
| WebToolkit | 搜索网页（查菜谱） |
| TodoToolkit | 管理待办事项 |
| SubagentTool | 召唤"副厨师"帮忙 |

---

## 四、"点菜"流程——用户输入如何变成AI回复

当你输入一句话，流程是这样的：

```
你：帮我写一个"Hello World"程序
    ↓
InputBar 收集你的输入
    ↓
发送 UserSubmitted 消息
    ↓
AgnoClawApp.on_user_submitted() 被调用
    ↓
创建 Worker 运行 AgentDriver.send_message()
    ↓
AgentDriver.send_message() 调用 agent.arun()
    ↓
AgentHarness.arun() 把输入发给"厨师"（Agno Agent）
    ↓
厨师（大模型）思考并回复
    ↓
AgentHarness 把回复切成小块（StreamChunk）发回
    ↓
ChatLog 逐字显示给用户
```

### 4.1 核心方法：arun()

```python
async def arun(self, message: str, *, stream: bool = True, skill: str | None = None):
    """
    这是服务员把点菜单交给厨师的核心方法
    """
    # 1. 找到要用的技能（skill）
    # 2. 把技能内容加到系统提示词里
    # 3. 调用 agent.arun() 开始做菜
    # 4. 如果 stream=True，边做菜边端盘子（流式输出）
```

### 4.2 流式输出（Streaming）

当 `stream=True` 时，厨师不是等全部菜做好了才上菜，而是**边做边端**：

```
厨师正在做：宫保鸡丁
    ↓
切好鸡肉 → 端上来（第一个chunk）
    ↓
炒好了 → 端上来（第二个chunk）
    ↓
装盘完成 → 端上来（第三个chunk）
```

这就是为什么你在 TUI 里看到的 AI 回复是**逐字出现**的，而不是等好久才一下子全显示出来。

---

## 五、"厨房工具"详解——Tools

### 5.1 BashToolkit（能执行命令）

当你让 AI "运行 `ls` 命令"，它就会用这个工具：

```python
class BashToolkit:
    def bash(self, command: str) -> str:
        """执行一个bash命令，返回输出"""
        return subprocess.run(command, shell=True, capture_output=True).stdout
    
    def bash_start(self, command: str) -> str:
        """启动一个长时间运行的命令"""
        
    def bash_output(self, pid: str) -> str:
        """获取正在运行的命令的输出"""
        
    def bash_kill(self, pid: str) -> str:
        """停止一个正在运行的命令"""
```

### 5.2 FilesToolkit（能读写文件）

```python
class FilesToolkit:
    def read(self, path: str) -> str:
        """读取文件内容"""
        
    def write(self, path: str, content: str) -> str:
        """写入文件内容"""
        
    def edit(self, path: str, old: str, new: str) -> str:
        """编辑文件（替换特定文本）"""
        
    def glob(self, pattern: str) -> list[str]:
        """查找匹配的文件"""
        
    def grep(self, pattern: str, path: str) -> list[str]:
        """在文件中搜索内容"""
```

### 5.3 WebToolkit（能搜索网页）

```python
class WebToolkit:
    def web_search(self, query: str) -> str:
        """搜索网页"""
        
    def web_fetch(self, url: str) -> str:
        """获取网页内容"""
```

---

## 六、"培训手册"——System Prompt

每个厨师都需要培训手册，告诉它：
- 怎么和人说话（语气）
- 能做什么事（工具）
- 有什么限制（不能做什么）

`AgentHarness` 的系统提示词是由很多"章节"组成的：

```
┌─────────────────────────────────────────┐
│ System Prompt（培训手册）                │
├─────────────────────────────────────────┤
│ 第一章：身份设定（Identity）             │
│   "你是一个AI助手"                       │
├─────────────────────────────────────────┤
│ 第二章：说话风格（Tone/Soul）            │
│   "简洁、直接、不废话"                   │
├─────────────────────────────────────────┤
│ 第三章：工具说明（Tools）                │
│   "你可以读写文件、执行命令、搜索网页"  │
├─────────────────────────────────────────┤
│ 第四章：技能说明（Skills）               │
│   "如果有技能可用，可以激活使用"        │
├─────────────────────────────────────────┤
│ 第五章：限制规则（Blocked）              │
│   "不能透露敏感信息"                    │
└─────────────────────────────────────────┘
```

这些章节的组装在 `src/agnoclaw/prompts/system.py` 和 `sections.py` 中完成。

---

## 七、"餐桌"——Session（会话）

当你第一次用 `agnoclaw tui`，会创建一个"餐桌"（Session）：

```
session_id = "abc12345"  # 每次对话的唯一ID
```

这个 ID 被用来：
- 保存对话历史（下次还能继续聊）
- 区分不同的"餐桌"（多人同时用）

对话历史存储在 SQLite 数据库中（开发环境）或 PostgreSQL（生产环境）。

---

## 八、AgentHarness 的完整初始化流程

```
AgentHarness.__init__()
    ↓
1. 加载配置文件（get_config()）
    ↓
2. 创建 Workspace（读取 SOUL.md, USER.md 等）
    ↓
3. 解析 model 和 provider（决定用哪个AI）
    ↓
4. 构建系统提示词（SystemPromptBuilder）
    ↓
5. 获取默认工具（get_default_tools()）
    ↓
6. 创建 Agno Agent（self._agent = Agent(...)）
    ↓
7. 初始化 SkillRegistry（技能注册表）
    ↓
8. 设置权限模式（PermissionController）
```

---

## 九、关键方法一览

| 方法 | 作用 |
|------|------|
| `arun()` | 异步运行（核心方法） |
| `print_response()` | 同步运行并打印（CLI用） |
| `send_message()` | 发送消息（driver.py 调用） |
| `get_skills()` | 获取所有可用技能 |
| `load_skill()` | 加载某个技能的内容 |

---

## 十、思考题

1. `AgentHarness._agent` 和 `AgentHarness` 是什么关系？（提示：一个是厨师，一个是服务员）
2. 如果没有安装 `agno` 库，`AgentHarness` 能运行吗？
3. 为什么 AI 回复是逐字显示的（流式输出）？

---

> 下一篇：《TUI 之 03：Textual 界面是如何画出来的》——深入解析 Textual 框架和各个 Widget 的实现