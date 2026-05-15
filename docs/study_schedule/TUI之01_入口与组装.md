# TUI 系列 01： agnoclaw 的 TUI 入口 —— 从命令行到图形界面

> 目标：小朋友也能看懂！用一个"变形金刚"的比喻来讲清楚，当你在终端输入 `agnoclaw tui` 之后，程序是如何一步一步组建出漂亮的图形界面的。

---

## 一、"变形金刚"的组装工厂

想象一下，`agnoclaw tui` 命令就像是一声"启动！"，召唤出一台**变形金刚（Transformer）**。

这台变形金刚不是一个人组成的，而是由很多小零件（组件）组成的：

```
┌──────────────────────────────────────┐
│  头顶的"天线"（HeaderBar）            │  ← 机器人顶部的信号灯
│  显示：我在用哪个大脑（模型）         │
├─────────────────────┬────────────────┤
│                     │                │
│  身体中央           │  右侧小屏幕     │
│  （ChatLog）        │  （NotificationPanel）│
│  机器人的"脸"       │  通知区域       │
│  展示对话           │                │
│                     │                │
├─────────────────────┴────────────────┤
│  脚部输入板（InputBar）              │  ← 你说话的地方
├──────────────────────────────────────┤
│  底部状态栏（AgnoStatusBar）         │  ← 显示心跳等状态
└──────────────────────────────────────┘
```

---

## 二、命令行的"起点"

当你打开终端，输入：

```
$ agnoclaw tui
```

Python 找到 `src/agnoclaw/cli/main.py` 这个文件，运行里面的 `tui()` 函数：

```python
# cli/main.py 的 tui 命令
@cli.command()
@MODEL_OPT
@PROVIDER_OPT
@SESSION_OPT
@WORKSPACE_OPT
@DEBUG_OPT
@PERMISSION_MODE_OPT
def tui(model, provider, session, workspace, debug, permission_mode):
    """Launch the full Textual TUI (requires agnoclaw[tui])."""
    try:
        from agnoclaw.tui import AgnoClawApp
    except ImportError:
        console.print("[red]TUI dependencies not installed.[/red]")
        sys.exit(1)

    agent = _build_agent(model, provider, session, workspace, debug, permission_mode)
    app = AgnoClawApp(agent=agent, debug=debug)
    app.run()    # ← 变形金刚开始运行了！
```

---

## 三、"组装工人" —— `_build_agent` 函数

`_build_agent` 就像一个**组装工人**，它的任务是把各种零件组装成 `AgentHarness` 这个核心组件。

```python
def _build_agent(
    model: str | None,       # 用什么大脑？比如 claude-sonnet-4-6
    provider: str | None,    # 用哪家公司的AI？比如 anthropic
    session: str | None,      # 用什么会话ID？
    workspace: str | None,   # 工作目录在哪里？
    debug: bool,             # 是否开启调试模式？
    permission_mode: str | None,  # 权限模式？
):
    from agnoclaw import AgentHarness
    return AgentHarness(
        model=model,
        provider=provider,
        session_id=session,
        workspace_dir=workspace,
        debug=debug,
        permission_mode=permission_mode,
    )
```

简单来说，它把所有你在命令行输入的选项，"打包"成一个 `AgentHarness` 对象。

---

## 四、"超级大脑" —— `AgentHarness` 是什么？

`AgentHarness`（在 `agent.py` 中）是整个程序的核心。你可以把它想象成变形金刚的**控制中心**。

它内部做了几件重要的事：

### 4.1 读取工作区文件

就像变形金刚启动前要读取"任务手册"一样，`AgentHarness` 会读取工作区目录下的各种 `.md` 文件：

- `SOUL.md` → 机器人的人格设定（怎么说话）
- `USER.md` → 用户的信息（用户是谁）
- `IDENTITY.md` → 机器人的身份设定
- `AGENTS.md` → 代理的配置文件

### 4.2 创建"大脑"（Agno Agent）

在 `AgentHarness` 内部，会创建一个真正的 AI "大脑"：

```python
self._agent = Agent(
    model=self._model,           # 用什么模型
    system_message=system_prompt,  # 设定系统提示词
    tools=_all_tools,            # 给它工具（能读写文件、搜索网页等）
    session_id=session_id,      # 会话ID
    ...
)
```

这个"大脑"是 `agno` 库提供的，不是我们写的，它负责和 AI 模型对话。

### 4.3 注册技能（Skills）

变形金刚可以换上不同的"工具背包"（技能）。`SkillRegistry` 管理所有的技能，比如：
- 一个"搜索网页"的技能
- 一个"读写文件"的技能

---

## 五、"变形金刚身体" —— `AgnoClawApp`

拿到 `AgentHarness` 之后，`tui()` 函数创建了真正的变形金刚身体：`AgnoClawApp`。

这个类是用 `textual` 库写的。`textual` 就像一个"画布"，让我们可以在终端里画出一个有按钮、有输入框的漂亮界面。

### 5.1 组装顺序（compose 方法）

```python
def compose(self):
    return VerticalScroll(
        HeaderBar(),
        Horizontal(      # ← 一行包含两个部件
            ChatLog(),           # 左侧：对话区域（机器人脸）
            NotificationPanel(), # 右侧：通知面板
        ),
        LogViewer(),     # 底部日志（默认隐藏）
        InputBar(),      # 输入框（脚部）
        AgnoStatusBar(), # 状态栏
    )
```

### 5.2 每个部件的作用

| 部件 | 文件位置 | 作用 |
|------|----------|------|
| `HeaderBar` | `tui/widgets/header_bar.py` | 顶部显示"agnoclaw · 模型名 · 会话ID" |
| `ChatLog` | `tui/widgets/chat_log.py` | 中间的大区域，显示你和机器人的对话 |
| `NotificationPanel` | `tui/widgets/notification_panel.py` | 右侧小屏幕，显示心跳警告、计划任务提醒 |
| `LogViewer` | `tui/widgets/log_viewer.py` | 调试日志，按 Ctrl+L 显示 |
| `InputBar` | `tui/widgets/input_bar.py` | 底部输入框，你在这里打字 |
| `AgnoStatusBar` | `tui/widgets/status_bar.py` | 最底部，显示心跳倒计时、工具数量等 |

---

## 六、用户输入的流程

当你对着 InputBar 输入一句话，按下回车：

```
你：帮我写一个"Hello World"程序
```

### 消息传递链

```
InputBar（你的输入）
    ↓ 发送 UserSubmitted 消息
AgnoClawApp.on_user_submitted()
    ↓ 创建 worker 运行 AgentDriver.send_message()
AgentDriver.send_message()
    ↓ 调用 agent.arun() 获取 AI 回复
    ↓ 发送 StreamChunk 消息（逐字显示）
    ↓ 发送 StreamDone 消息（完成）
AgnoClawApp.on_stream_chunk() → ChatLog 显示文字
AgnoClawApp.on_stream_done()  → ChatLog 渲染 Markdown
```

---

## 七、"自动驾驶仪" —— AgentDriver

`AgentDriver` 是一个**中介者**，连接 Textual 的界面和真正的 AI 大脑。

```python
class AgentDriver:
    def __init__(self, app: App, agent: AgentHarness) -> None:
        self._app = app          # 变形金刚的身体
        self._agent = agent       # 变形金刚的大脑

    async def send_message(self, text: str, *, skill: str | None = None):
        # 启动 AI 对话
        response = await self._agent.arun(text, stream=True, skill=skill)
        
        async for event in response:  # 逐字获取 AI 回复
            content = self._agent._extract_event_content(event)
            if content:
                self._app.post_message(StreamChunk(content))  # 发送给界面
```

---

## 八、心跳守护（HeartbeatDaemon）

变形金刚有一个"心跳监测仪"，每隔一段时间检查一下工作计划（`HEARTBEAT.md`）是否完成。

```python
class AgentDriver:
    def start_heartbeat(self):
        daemon = HeartbeatDaemon(self._agent, on_alert=...)
        # 每分钟发送 HeartbeatTick
        # 当发现问题时发送 HeartbeatAlert
```

当心跳发出警告时，`NotificationPanel` 会显示提醒，`AgnoStatusBar` 会更新倒计时。

---

## 九、总结

整个 `agnoclaw tui` 的启动过程：

```
命令行输入 agnoclaw tui
    ↓
cli/main.py :: tui()
    ↓
_build_agent() 创建 AgentHarness
    ↓ (核心大脑 + 工作区文件 + 技能注册)
AgnoClawApp(agent=agent).run()
    ↓
Textual 组装各个 Widget
    ↓
显示漂亮界面，等待用户输入
    ↓
用户输入 → AgentDriver → agent.arun() → 流式返回
    ↓
Textual 消息循环更新界面
```

---

## 思考题

1. `_build_agent` 和 `AgentHarness.__init__` 谁更早运行？
2. 如果没有安装 `agnoclaw[tui]`，运行 `agnoclaw tui` 会发生什么？
3. `ChatLog` 和 `NotificationPanel` 有什么区别？

---

> 下一篇：《TUI 之 02：AgentHarness 超级大脑的秘密》——深入解析 agent.py