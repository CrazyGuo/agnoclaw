# Core 系列 20： AsyncREPL —— 异步交互式命令行

> 目标：小朋友也能看懂！用一个"异步服务员"的比喻来讲清楚，AsyncREPL 是如何实现非阻塞输入输出的，以及 Heartbeat 是如何与 REPL 并行工作的。

---

## 一、"异步服务员"比喻

想象一个餐厅里有一个**异步服务员**：
- 普通服务员：你点菜 → 等待上菜 → 服务员回来 → 你再点下一道
- 异步服务员：你点菜 → 服务员去厨房 → **在你等待时可以继续接受其他顾客的点菜**

agnoclaw 的 **AsyncREPL** 就是这样的"异步服务员"：
- 用户输入一句话 → AI 处理（异步）
- **在 AI 处理期间，用户可以继续输入**（虽然实际上会被禁用，但通知可以显示）
- Heartbeat 检查在后台**并行运行**

---

## 二、AsyncREPL vs 同步 REPL

### 2.1 同步 REPL（旧的）

```python
# 旧的方式：阻塞
while True:
    user_input = click.prompt("> ")  # 阻塞等待输入
    agent.print_response(user_input)    # 等待 AI 回复完成
```

问题：
- 如果 AI 处理很慢，用户只能等待
- Heartbeat 通知必须等到 AI 回复完成后才能显示
- 用户无法"取消"正在进行的 AI 请求

### 2.2 AsyncREPL（新的）

```python
# 新的方式：异步
async def run():
    while True:
        user_input = await session.prompt_async("> ")  # 非阻塞等待
        await stream_response(user_input)  # 异步流式输出
```

优势：
- 使用 `prompt_toolkit` 实现真正的异步输入
- Heartbeat 在**同一 asyncio 循环**中运行，可以实时显示通知
- 流式输出逐字显示

---

## 三、AsyncREPL 的结构

文件：`src/agnoclaw/cli/async_repl.py`

### 3.1 核心组件

```python
class AsyncREPL:
    def __init__(
        self,
        agent: AgentHarness,
        *,
        enable_heartbeat: bool = True,
        debug: bool = False,
    ):
        self._agent = agent
        self._enable_heartbeat = enable_heartbeat
        self._debug = debug
        self._console = Console()
        self._session = PromptSession()
        self._notification_queue: asyncio.Queue[str] = asyncio.Queue()
        self._queued_skill: str | None = None
        self._daemon = None
```

### 3.2 主要方法

```python
async def run(self) -> None:
    """主 REPL 循环"""
    if self._enable_heartbeat:
        self._start_heartbeat()

    # 启动后台任务：打印通知
    notif_task = asyncio.create_task(self._notification_printer())

    while True:
        user_input = await self._session.prompt_async("\n[you] > ")
        await self._stream_response(user_input, skill=active_skill)
```

---

## 四、prompt_toolkit 的异步输入

### 4.1 prompt_async()

```python
user_input = await self._session.prompt_async("\n[you] > ")
```

`prompt_async()` 是 `prompt_toolkit` 提供的**异步版本**的输入函数：
- 不会阻塞 asyncio 循环
- 在等待输入时可以切换到其他协程

### 4.2 patch_stdout()

```python
with patch_stdout():
    while True:
        user_input = await self._session.prompt_async("\n[you] > ")
```

`patch_stdout()` 允许在**等待输入时**打印其他输出（如 Heartbeat 通知）。

---

## 五、Stream Response —— 流式输出

```python
async def _stream_response(self, message: str, *, skill: str | None = None) -> None:
    """Stream agent response token-by-token."""
    self._console.print("\n[bold green][agent][/bold green]")
    active_tool_labels: dict[str, str] = {}

    try:
        response = await self._agent.arun(message, stream=True, skill=skill)

        # 流式事件
        async for event in response:
            content = self._agent._extract_event_content(event)
            if content:
                print(content, end="", flush=True)  # 打印到标准输出

            # 工具调用指示器
            event_type = self._agent._map_agno_event_type(event)
            if event_type == "tool.call.started":
                self._console.print(f"\n  [dim]→ {label}...[/dim]", end="")
            elif event_type == "tool.call.completed":
                self._console.print(" [dim]done[/dim]")

        print()  # 流结束后换行
    except KeyboardInterrupt:
        self._console.print("\n[dim](interrupted)[/dim]")
```

---

## 六、Heartbeat 集成

### 6.1 启动 HeartbeatDaemon

```python
def _start_heartbeat(self) -> None:
    """Start HeartbeatDaemon on the current asyncio loop."""
    from agnoclaw.config import get_config

    cfg = get_config()
    if not cfg.heartbeat.enabled:
        logger.debug("Heartbeat disabled in config — skipping")
        return

    if self._agent.workspace.is_empty_heartbeat():
        logger.debug("HEARTBEAT.md empty — skipping heartbeat")
        return

    from agnoclaw.heartbeat import HeartbeatDaemon

    def on_alert(msg: str) -> None:
        """Push alert to notification queue for async printing."""
        self._notification_queue.put_nowait(msg)

    self._daemon = HeartbeatDaemon(self._agent, on_alert=on_alert, config=cfg)
    self._daemon.start()
```

**关键：** HeartbeatDaemon 和 REPL 运行在**同一个 asyncio 循环**中！

### 6.2 通知打印协程

```python
async def _notification_printer(self) -> None:
    """Background task: pulls from queue, prints above prompt via patch_stdout."""
    while True:
        try:
            msg = await self._notification_queue.get()
            self._console.print(
                Panel(
                    msg,
                    title="[yellow]Heartbeat Alert[/yellow]",
                    border_style="yellow",
                )
            )
        except asyncio.CancelledError:
            break
```

这个协程在后台运行，**随时等待 Heartbeat 通知**，一旦收到就打印在界面上。

---

## 七、斜杠命令处理

```python
# Handle slash commands
if user_input.strip().startswith("/"):
    if user_input.strip() in ("/quit", "/exit", "/q"):
        self._console.print("[dim]Goodbye.[/dim]")
        break

    from agnoclaw.cli.main import _handle_slash_command

    handled, self._queued_skill = _handle_slash_command(
        user_input.strip(), self._agent, self._queued_skill
    )
    if handled:
        continue
```

支持的斜杠命令：
- `/quit`, `/exit`, `/q` — 退出
- `/skill <name>` — 激活技能
- `/skills` — 列出技能
- `/clear` — 清除会话
- `/help` — 帮助

---

## 八、完整流程图

```
AsyncREPL.run()
    │
    ├── _start_heartbeat()
    │       └── HeartbeatDaemon.start() → 后台定时检查
    │
    ├── _notification_printer() → 后台任务，等待通知队列
    │
    └── 主循环
            │
            ├── await session.prompt_async() → 等待用户输入（非阻塞）
            │
            ├── 用户输入 "帮我写代码"
            │
            ├── 检查斜杠命令
            │
            └── await _stream_response()
                    │
                    ├── await agent.arun(message, stream=True)
                    │
                    ├── async for event in response:
                    │       │
                    │       ├── content = extract_event_content(event)
                    │       └── print(content, end="", flush=True)  → 流式输出
                    │
                    └── 完成后回到主循环

同时（并行）：

HeartbeatDaemon._run_heartbeat_loop()
    │
    ├── 每 N 分钟检查一次
    │
    ├── 发现问题 → on_alert(msg)
    │
    └── notification_queue.put_nowait(msg)
            │
            └── _notification_printer() → 显示通知
```

---

## 九、为什么需要 patch_stdout()？

`patch_stdout()` 是一个**猴子补丁**，它让标准输出在**等待输入时也能被打印**。

没有它：
```
用户正在输入...（阻塞状态）
Heartbeat 通知来了 → **无法显示**（因为在等待输入）
```

有了它：
```
用户正在输入...（异步等待）
Heartbeat 通知来了 → **可以显示在输入行上方**
```

---

## 十、与 TUI 的区别

| 特征 | AsyncREPL | TUI (AgnoClawApp) |
|------|-----------|-------------------|
| 界面 | 终端文本 | Textual 图形界面 |
| 输入 | prompt_toolkit | Input 组件 |
| 通知 | patch_stdout 打印 | NotificationPanel 组件 |
| Heartbeat | 同一 asyncio 循环 | AgentDriver 管理 |
| 快捷键 | 斜杠命令 | Ctrl+L, Ctrl+S 等 |

---

## 十一、思考题

1. 为什么 HeartbeatDaemon 需要和 REPL 运行在同一个 asyncio 循环？
2. 如果用户输入 `/skill code-review` 但技能不存在，会发生什么？
3. `patch_stdout()` 为什么被称为"猴子补丁"？它有什么潜在问题？

---

> 附加总结篇：《Core 系列 21： 第二系列总结 —— 全栈知识图谱》