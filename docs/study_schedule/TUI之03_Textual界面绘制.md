# TUI 系列 03： Textual 界面是如何画出来的

> 目标：小朋友也能看懂！用一个"画布画家"的比喻来讲清楚，Textual 框架是如何让程序在终端里画出漂亮界面的，以及各个 Widget（组件）是如何配合工作的。

---

## 一、Textual 是什么？

想象一下，你要在纸上画一幅画：
- 你可以自由地画任何东西
- 但如果每次画一个人，都需要从头画眼睛、鼻子、嘴巴...会很累

**Textual** 就是一个专门帮你在**终端（Terminal）**里画画的"绘画框架"。它提供了很多**现成的组件（Widget）**，就像乐高积木一样，你只需要把它们拼起来，就能画出漂亮的界面。

### 对比其他框架

| 框架 | 应用场景 | 比喻 |
|------|----------|------|
| Tkinter | Python GUI | 用铅笔画画 |
| PyQt | Python GUI | 用油画颜料画画 |
| React | Web 前端 | 用颜料画网页 |
| **Textual** | **终端 UI** | **用方块字符画画** |

Textual 画出来的东西，用的是**方块字符**（ASCII art），所以看起来像这样：

```
┌──────────────────────────────────────┐
│  agnoclaw · claude-sonnet-4-6        │  ← HeaderBar
├──────────────────────────────────────┤
│  你好，有什么可以帮你的？            │
│  Agent: 好的，我来帮你...             │  ← ChatLog
├──────────────────────────────────────┤
│  > 你好...                        /skill│  ← InputBar
└──────────────────────────────────────┘
```

---

## 二、Textual 的核心概念

### 2.1 App（应用）

整个程序就是一个 `App`（应用）。在 `agnoclaw` 中，这个应用叫 `AgnoClawApp`。

```python
class AgnoClawApp(App):
    def compose(self):
        # 告诉框架："我要画这些组件"
        return [
            HeaderBar(),
            ChatLog(),
            NotificationPanel(),
            InputBar(),
            AgnoStatusBar(),
        ]
```

就像画家铺开画布，准备开始画画。

### 2.2 Widget（组件）

每个可见的元素都是一个 `Widget`（组件）：

```
App（画布）
├── HeaderBar（顶部标题栏）
├── ChatLog（中间对话区）
├── NotificationPanel（右侧通知面板）
├── LogViewer（日志面板，默认隐藏）
├── InputBar（底部输入框）
└── AgnoStatusBar（底部状态栏）
```

### 2.3 Message（消息）

当你在 InputBar 里输入文字，按下回车键，会发生什么？

```
InputBar 检测到"回车键按下"
    ↓
发送 UserSubmitted 消息
    ↓
AgnoClawApp 收到消息，决定：开始聊天！
    ↓
ChatLog 开始显示 "正在思考..."
```

这就是 **Message（消息）**系统——组件之间通过消息来"说话"。

### 2.4 CSS（样式）

Textual 允许你用类似 CSS 的语法来定义组件的外观：

```css
ChatLog {
    height: 1fr;              /* 占满剩余高度 */
    border: solid $surface-lighten-2;
    padding: 0 1;
}
```

---

## 三、AgnoClawApp 详解

文件：`src/agnoclaw/tui/app.py`

### 3.1 整体布局（ASCII 图）

```
┌─────────────────────────────────────────────────┐
│  agnoclaw · claude-sonnet-4-6 · session:abc     │  ← HeaderBar (dock: top)
├──────────────────────────────────┬──────────────┤
│                                  │ NOTIFICATIONS│
│  ChatLog                         │ [HB] alert   │  ← NotificationPanel
│  (对话区域)                       │ [cron] job   │     (width: 35)
│                                  │              │
├──────────────────────────────────┴──────────────┤
│  > 输入你的问题...                      /skill │  ← InputBar (height: 3)
├─────────────────────────────────────────────────┤
│  ● heartbeat: 28m │ tools: 6 │ ready           │  ← AgnoStatusBar (height: 1)
└─────────────────────────────────────────────────┘
         ↑ 按 Ctrl+L 显示/隐藏 LogViewer
```

### 3.2 compose() 方法——组件组装

```python
def compose(self):
    return VerticalScroll(
        HeaderBar(),
        Horizontal(        # ← 一行包含两个并排的组件
            ChatLog(),           # 左：对话区域
            NotificationPanel(), # 右：通知面板
        ),
        LogViewer(),     # 底部日志（默认隐藏）
        InputBar(),      # 输入框
        AgnoStatusBar(), # 状态栏
    )
```

注意：
- `VerticalScroll` 让整个布局可以滚动
- `Horizontal` 让 ChatLog 和 NotificationPanel **并排显示**

### 3.3 快捷键绑定

```python
BINDINGS = [
    Binding("ctrl+q", "quit", "Quit"),            # Ctrl+Q 退出
    Binding("ctrl+n", "toggle_notifications", "Notif"),  # Ctrl+N 显示/隐藏通知
    Binding("ctrl+s", "open_skill_picker", "Skills"),    # Ctrl+S 打开技能选择器
    Binding("ctrl+l", "toggle_log_viewer", "Log"),       # Ctrl+L 显示/隐藏日志
]
```

---

## 四、组件详解

### 4.1 HeaderBar（顶部状态栏）

文件：`src/agnoclaw/tui/widgets/header_bar.py`

```python
class HeaderBar(Static):
    """顶部栏，显示模型名和会话ID"""
    
    DEFAULT_CSS = """
    HeaderBar {
        dock: top;           # 固定在顶部
        height: 1;           # 高度1行
        background: $accent; # 背景色
    }
    """
    
    def _build_text(self):
        return f"agnoclaw · {self._model} · session:{short_id}"
```

**显示效果：**
```
┌─────────────────────────────────────────────────┐
│  agnoclaw · claude-sonnet-4-6 · session:abc1234 │  ← HeaderBar
└─────────────────────────────────────────────────┘
```

### 4.2 ChatLog（对话区域）——最复杂的组件

文件：`src/agnoclaw/tui/widgets/chat_log.py`

这是**最重要的组件**，负责显示你和 AI 的对话内容。

#### 4.2.1 三种消息类型

```python
def add_user_message(self, text: str):
    """添加用户消息——绿色标签 + 文字"""
    # 显示：You
    # 显示：用户的文字

def start_agent_response(self):
    """开始AI回复——显示"..."表示正在思考"""
    # 显示：Agent
    # 显示：...（闪烁提示）

def append_chunk(self, text: str):
    """追加AI回复的每一个字——边打边显示"""
    # 正在输入：今、天、天、气...
```

#### 4.2.2 流式输出原理

当你输入"今天天气如何？"：

```
时刻1：Agent: 今
时刻2：Agent: 今天
时刻3：Agent: 今天天
时刻4：Agent: 今天天气
...
最终：Agent: 今天天气晴朗，适合出行。
```

每来一个"字"（chunk），就调用一次 `append_chunk()`，这个方法会：
1. 把新字加到累计文本里
2. 更新屏幕上显示的内容
3. 滚动到底部

#### 4.2.3 完成后渲染 Markdown

当 AI 说完后，`finish_agent_response()` 会把纯文本重新渲染成**Markdown 格式**：

```
输入：今天天气晴朗，适合出行。

输出（Markdown渲染后）：
┌────────────────────────────────────┐
│ 今天天气晴朗，适合出行。            │
└────────────────────────────────────┘
```

代码：
```python
def finish_agent_response(self, full_text: str = "") -> None:
    if self._streaming_widget is not None:
        self._streaming_widget.update(RichMarkdown(final))  # 渲染Markdown
        self._streaming_widget = None
```

### 4.3 InputBar（输入框）

文件：`src/agnoclaw/tui/widgets/input_bar.py`

**功能：**
1. 让用户输入文字
2. 按 Tab 可以自动补全命令（如 `/skill`）
3. 发送时禁用自己（防止重复发送）

#### 4.3.1 自动补全（Suggester）

```python
BASE_SLASH_COMMANDS = [
    "/skill",   # 激活技能
    "/skills",  # 列出技能
    "/clear",  # 清除对话
    "/help",   # 帮助
    "/quit",   # 退出
    "/compact", # 压缩历史
]

# 用户输入"/sk" + Tab → 自动补全为 "/skill"
```

#### 4.3.2 禁用状态

当 AI 正在"思考"时（stream=True），InputBar 会变成灰色：

```python
def set_disabled(self, disabled: bool) -> None:
    if disabled:
        self.disabled = True
        self.placeholder = "Agent is responding..."  # 提示文字
    else:
        self.disabled = False
        self.placeholder = "Type a message or /command..."
```

### 4.4 NotificationPanel（通知面板）

文件：`src/agnoclaw/tui/widgets/notification_panel.py`

**作用：** 显示心跳警告、计划任务结果等。

```
┌──────────────────┐
│ NOTIFICATIONS    │
├──────────────────┤
│ [HB] 28分钟前检查 │  ← Heartbeat 提醒
│ [cron] 备份完成   │  ← 定时任务结果
└──────────────────┘
```

### 4.5 AgnoStatusBar（状态栏）

文件：`src/agnoclaw/tui/widgets/status_bar.py`

**作用：** 显示底部状态信息。

```
┌─────────────────────────────────────────────────┐
│ ● heartbeat: 28m │ tools: 6 │ ready             │  ← AgnoStatusBar
└─────────────────────────────────────────────────┘
```

- `heartbeat: 28m` — 距离上次心跳检查已经 28 分钟
- `tools: 6` — 可用的工具数量
- `ready` — 当前状态（ready=空闲，streaming=正在回复）

### 4.6 LogViewer（日志查看器）

文件：`src/agnoclaw/tui/widgets/log_viewer.py`

**作用：** 显示调试日志，按 `Ctrl+L` 切换显示/隐藏。

```
┌─────────────────────────────────────────────────┐
│ [12:30:01] ToolCall: bash - "ls -la"           │
│ [12:30:02] ToolResult: ...                     │
│ [12:30:03] StreamChunk: "好的，我来..."        │
└─────────────────────────────────────────────────┘
```

### 4.7 SkillPickerScreen（技能选择器）

文件：`src/agnoclaw/tui/screens.py`

**作用：** 按 `Ctrl+S` 打开技能选择对话框。

```
┌─────────────────────────────────────────────────┐
│            选择一个技能                          │
├─────────────────────────────────────────────────┤
│  [ ] code-review   代码审查技能                  │
│  [ ] debug        调试助手                       │
│  [ ] web-search   网页搜索                       │
├─────────────────────────────────────────────────┤
│  Enter 确认    ESC 取消                         │
└─────────────────────────────────────────────────┘
```

---

## 五、消息通信机制

### 5.1 消息流程图

```
用户输入"帮我写代码" + 按回车
    ↓
InputBar.on_input_submitted()
    ↓ 发送 UserSubmitted("帮我写代码")
AgnoClawApp.on_user_submitted()
    ↓
AgentDriver.send_message("帮我写代码")
    ↓
agent.arun() → AI 开始处理
    ↓
StreamChunk("好") → app.post_message()
    ↓
AgnoClawApp.on_stream_chunk() → ChatLog.append_chunk("好")
    ↓
StreamChunk("的") → app.post_message()
    ↓
AgnoClawApp.on_stream_chunk() → ChatLog.append_chunk("的")
    ↓
StreamChunk("...") → app.post_message()
    ↓
StreamDone("好的，我来帮你写代码...") → app.post_message()
    ↓
AgnoClawApp.on_stream_done() → ChatLog.finish_agent_response()
    ↓
InputBar.set_disabled(False) → 重新启用输入
```

### 5.2 关键事件一览

| 事件 | 发送者 | 接收者 | 作用 |
|------|--------|--------|------|
| `UserSubmitted` | InputBar | AgnoClawApp | 用户按了回车，开始聊天 |
| `StreamChunk` | AgentDriver | AgnoClawApp | AI 回复的一个字 |
| `StreamDone` | AgentDriver | AgnoClawApp | AI 回复完成 |
| `ToolCallStarted` | AgentDriver | AgnoClawApp | 工具开始执行 |
| `ToolCallCompleted` | AgentDriver | AgnoClawApp | 工具执行完成 |
| `HeartbeatAlert` | AgentDriver | AgnoClawApp | 心跳发出警告 |
| `HeartbeatTick` | AgentDriver | AgnoClawApp | 心跳计时器 |

---

## 六、AgentDriver——连接大脑和界面

文件：`src/agnoclaw/tui/driver.py`

AgentDriver 是一个**翻译官**，连接 `AgentHarness`（大脑）和 `AgnoClawApp`（界面）。

```python
class AgentDriver:
    def __init__(self, app: App, agent: AgentHarness):
        self._app = app    # 界面
        self._agent = agent  # 大脑
    
    async def send_message(self, text: str, *, skill: str | None = None):
        # 1. 调用大脑处理输入
        response = await self._agent.arun(text, stream=True, skill=skill)
        
        # 2. 把大脑的回复翻译成界面能懂的消息
        async for event in response:
            content = self._agent._extract_event_content(event)
            if content:
                self._app.post_message(StreamChunk(content))  # 发给界面
```

### 6.1 心跳监控

AgentDriver 还负责启动"心跳监测仪"：

```python
def start_heartbeat(self):
    daemon = HeartbeatDaemon(self._agent, on_alert=lambda msg: 
        self._app.post_message(HeartbeatAlert(msg)))
    # 每分钟发送 HeartbeatTick 给状态栏
```

---

## 七、思考题

1. Textual 的 Widget 和 HTML/CSS 的 div/span 有什么相似之处？
2. 为什么 ChatLog 需要"流式输出"？如果一次性显示所有内容会怎样？
3. 为什么 InputBar 在 AI 回复时要变成灰色（禁用）？

---

> 下一篇：《TUI 之 04：事件系统——Textual 的神经系统》——深入解析消息的传递和事件的处理