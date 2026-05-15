# TUI 系列 04： 事件系统 —— Textual 的神经系统

> 目标：小朋友也能看懂！用一个"快递系统"的比喻来讲清楚，事件（Message）是如何在 Textual 程序里传递的，以及各个组件是如何协同工作的。

---

## 一、"快递系统"比喻

想象一下，你在一个大商场里：
- **每个组件**就像商场里的一个柜台（InputBar、ChatLog、NotificationPanel...）
- **消息（Message）**就像快递包裹，需要从一个柜台送到另一个柜台
- **Textual 的消息系统**就像商场的快递员，负责把包裹送到正确的柜台

```
你按了回车键（快递到达 InputBar）
        ↓
InputBar 发出 UserSubmitted 快递
        ↓
Textual 快递员找到 AgnoClawApp 柜台
        ↓
AgnoClawApp 处理快递（开始聊天）
        ↓
AgentDriver 发出 StreamChunk 快递
        ↓
Textual 快递员送到 ChatLog 柜台
        ↓
ChatLog 显示新内容
```

---

## 二、agnoclaw 中的快递包裹（Message）

文件：`src/agnoclaw/tui/events.py`

在 agnoclaw 中，有以下几种"快递包裹"：

### 2.1 流式包裹（Streaming）

| 包裹 | 内容 | 送到哪里 |
|------|------|----------|
| `StreamChunk` | 一个字或一句话 | ChatLog |
| `StreamDone` | 全部内容完成 | ChatLog |
| `StreamError` | 出错了！ | ChatLog |

### 2.2 工具调用包裹（Tool Calls）

| 包裹 | 内容 | 送到哪里 |
|------|------|----------|
| `ToolCallStarted` | "工具开始执行了！" | ChatLog + LogViewer |
| `ToolCallCompleted` | "工具执行完成了！" | ChatLog + LogViewer |

### 2.3 心跳包裹（Heartbeat）

| 包裹 | 内容 | 送到哪里 |
|------|------|----------|
| `HeartbeatAlert` | "发现问题需要处理！" | ChatLog + NotificationPanel |
| `HeartbeatTick` | "心跳计时器（每分钟）" | AgnoStatusBar |

### 2.4 用户输入包裹

| 包裹 | 内容 | 送到哪里 |
|------|------|----------|
| `UserSubmitted` | "用户按了回车，内容是..." | AgnoClawApp |
| `CronResult` | "定时任务完成" | NotificationPanel |

---

## 三、每种快递的"形状"（Message 结构）

### 3.1 StreamChunk——AI 回复的一个字

```python
class StreamChunk(Message):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text  # ← 快递里装的内容
```

### 3.2 HeartbeatAlert——心跳警告

```python
class HeartbeatAlert(Message):
    def __init__(self, alert_text: str) -> None:
        super().__init__()
        self.alert_text = alert_text  # ← 警告内容
```

### 3.3 UserSubmitted——用户输入

```python
class UserSubmitted(Message):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text  # ← 用户说的话
```

---

## 四、快递的"派送路线"（Message Flow）

### 4.1 用户输入 → AI 回复的完整路线

```
1. 用户在 InputBar 输入"帮我写代码"
2. 按下回车

   InputBar.on_input_submitted()
        ↓ 发送 UserSubmitted("帮我写代码")
   AgnoClawApp.on_user_submitted()  ← 收到快递
        ↓
   AgentDriver.send_message()  ← 调用 AI 大脑
        ↓
   AI 开始处理...
        ↓
   AI 回复："好的，我来帮你..."

   AgentDriver 发送 StreamChunk("好")
        ↓
   AgnoClawApp.on_stream_chunk()  ← 收到快递
        ↓ ChatLog.append_chunk("好")

   AgentDriver 发送 StreamChunk("的")
        ↓
   AgnoClawApp.on_stream_chunk()  ← 收到快递
        ↓ ChatLog.append_chunk("的")

   ... (重复多次)

   AgentDriver 发送 StreamDone("好的，我来帮你写代码...")
        ↓
   AgnoClawApp.on_stream_done()  ← 收到快递
        ↓ ChatLog.finish_agent_response()
        ↓ InputBar.set_disabled(False)  ← 重新启用输入
```

### 4.2 心跳监测的路线

```
HeartbeatDaemon 检测到问题
        ↓
on_alert("HEARTBEAT.md 中的 '备份数据库' 未完成")
        ↓ 发送 HeartbeatAlert("HEARTBEAT.md 中的 '备份数据库' 未完成")
   NotificationPanel.add_heartbeat_alert()  ← 显示警告
   ChatLog.add_notification()  ← 在对话中显示通知

同时...

每分钟发送 HeartbeatTick(n)
        ↓
AgnoStatusBar.update_heartbeat(n)  ← 更新心跳倒计时
```

---

## 五、"柜台"如何接收快递（Handler）

每个柜台（Widget）需要**注册一个处理函数**来接收特定的快递。

### 5.1 AgnoClawApp 接收快递

```python
class AgnoClawApp(App):
    # 这个方法接收 StreamChunk 快递
    def on_stream_chunk(self, event: StreamChunk) -> None:
        self.query_one(ChatLog).append_chunk(event.text)

    # 这个方法接收 StreamDone 快递
    def on_stream_done(self, event: StreamDone) -> None:
        chat_log = self.query_one(ChatLog)
        chat_log.finish_agent_response(event.full_text)
        self.query_one(InputBar).set_disabled(False)

    # 这个方法接收 ToolCallStarted 快递
    def on_tool_call_started(self, event: ToolCallStarted) -> None:
        chat_log = self.query_one(ChatLog)
        chat_log.add_tool_indicator(event.tool_name, done=False)
        self.query_one(LogViewer).log(f"Tool started: {event.display_name}")
```

### 5.2 命名规则

在 Textual 中，处理函数有固定的命名规则：

```
on_ + 事件名 = 处理函数

StreamChunk    → on_stream_chunk()
StreamDone     → on_stream_done()
UserSubmitted  → on_user_submitted()
HeartbeatAlert → on_heartbeat_alert()
```

### 5.3 谁接收谁不管接收？

并不是每个组件都接收所有快递：

| 组件 | 接收的快递 |
|------|------------|
| AgnoClawApp | 所有快递（总指挥部） |
| ChatLog | StreamChunk, StreamDone, ToolCallStarted, ToolCallCompleted, HeartbeatAlert, StreamError |
| NotificationPanel | HeartbeatAlert, CronResult |
| AgnoStatusBar | HeartbeatTick, StreamDone |
| LogViewer | ToolCallStarted, ToolCallCompleted |

---

## 六、AgentDriver——快递中转站

文件：`src/agnoclaw/tui/driver.py`

AgentDriver 扮演**快递中转站**的角色：

```python
class AgentDriver:
    def __init__(self, app: App, agent: AgentHarness) -> None:
        self._app = app           # 商场总部
        self._agent = agent       # AI 大脑

    async def send_message(self, text: str, *, skill: str | None = None):
        # 1. 调用 AI 大脑获取回复
        response = await self._agent.arun(text, stream=True, skill=skill)

        # 2. 把 AI 的回复"打包"成快递，发送给商场总部
        async for event in response:
            content = self._agent._extract_event_content(event)
            if content:
                # 发送 StreamChunk 快递
                self._app.post_message(StreamChunk(content))

            # 处理工具调用事件
            event_type = self._agent._map_agno_event_type(event)
            if event_type == "tool.call.started":
                # 发送 ToolCallStarted 快递
                self._app.post_message(ToolCallStarted(...))
            elif event_type == "tool.call.completed":
                # 发送 ToolCallCompleted 快递
                self._app.post_message(ToolCallCompleted(...))

        # 3. 发送完成快递
        self._app.post_message(StreamDone("".join(accumulated)))
```

---

## 七、心跳系统的特殊快递

心跳系统有一个"定时闹钟"，每分钟发送一次 `HeartbeatTick` 快递：

```python
async def _heartbeat_ticker(self) -> None:
    """每分钟发送一次心跳倒计时"""
    while True:
        await asyncio.sleep(60)      # 等60秒
        self._minutes_since_heartbeat += 1  # 计数器+1
        self._app.post_message(
            HeartbeatTick(self._minutes_since_heartbeat)
        )  # 发送快递
```

这就像商场的时钟，每分钟报时一次，让每个人都知道现在几点。

---

## 八、Message 和 POST 的区别

在 Textual 中，发送消息有两种方式：

### 8.1 post_message（快递送到最近的柜台）

```python
# 发送快递到最近的柜台（自己的父组件）
self.post_message(StreamChunk("hello"))
```

### 8.2 app.post_message（快递送到总部）

```python
# 发送快递到 App 总部
self._app.post_message(StreamChunk("hello"))
```

在 AgentDriver 中，因为它是独立于 Textual 组件树的，所以需要用 `self._app.post_message()` 发送到 App 总部。

---

## 九、完整的事件流程图

```
用户输入
    ↓
InputBar 发送 UserSubmitted
    ↓
AgnoClawApp.on_user_submitted()
    ↓
启动 AgentDriver.send_message()（后台 Worker）
    ↓
AI 处理中...
    ↓
┌─────────────────────────────────────────────────────────────┐
│  AgentDriver 循环：                                        │
│    收到 AI 事件                                            │
│    ↓                                                       │
│    是文本内容？→ 发送 StreamChunk → ChatLog 显示           │
│    ↓                                                       │
│    是工具开始？→ 发送 ToolCallStarted → ChatLog+LogViewer  │
│    ↓                                                       │
│    是工具完成？→ 发送 ToolCallCompleted → ChatLog+LogViewer│
│    ↓                                                       │
│    AI 完成？→ 发送 StreamDone → ChatLog渲染 + InputBar恢复 │
└─────────────────────────────────────────────────────────────┘

同时（并行）：

HeartbeatDaemon.is_empty_heartbeat()
    ↓
满足条件？→ 发送 HeartbeatAlert → NotificationPanel + ChatLog

每分钟：
    HeartbeatTick → AgnoStatusBar 更新倒计时
```

---

## 十、思考题

1. 为什么 AgentDriver 要用 `self._app.post_message()` 而不是 `self.post_message()`？
2. 如果 `on_stream_chunk` 处理函数写得有问题（抛异常），会发生什么？
3. HeartbeatTick 每分钟发送一次，但如果 App 关闭了，这个定时器会怎样？

---

> 下一篇：《TUI 之 05：布局详解 —— 界面是如何排列的》——深入解析 Textual 的 CSS 布局系统和各个 Widget 的布局关系