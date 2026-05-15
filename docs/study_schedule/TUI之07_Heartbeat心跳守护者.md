# TUI 系列 07： Heartbeat 心跳守护者

> 目标：小朋友也能看懂！用一个"健康监测仪"的比喻来讲清楚，HeartbeatDaemon 是如何像一台健康监测仪一样，定期检查工作是否完成，并发出警报的。

---

## 一、"健康监测仪"比喻

想象你有一台**健康监测仪**：
- 它会每隔一段时间（比如 30 分钟）自动检查你的身体状态
- 如果一切正常，就不打扰你
- 如果发现问题，就发出警报让你注意

`HeartbeatDaemon` 就是 agnoclaw 的"健康监测仪"：
- 它会每隔一段时间（比如 30 分钟）检查 `HEARTBEAT.md` 文件
- 如果所有任务都完成，就不打扰你
- 如果发现问题，就通过 `on_alert` 回调通知 TUI 显示警报

---

## 二、HeartbeatDaemon 的位置和结构

文件：`src/agnoclaw/heartbeat/daemon.py`

```python
class HeartbeatDaemon:
    """心跳守护者——定期检查工作状态"""

    def __init__(
        self,
        agent: "AgentHarness",           # AI 大脑
        on_alert: Optional[Callable[[str], None]] = None,  # 警报回调
        config: Optional[HarnessConfig] = None,
        workspace: Optional[Workspace] = None,
    ):
        self._agent = agent
        self._on_alert = on_alert        # 警报通知函数
        self._config = config
        self._workspace = workspace
        self._task: Optional[asyncio.Task] = None  # 主循环任务
        self._cron_tasks: list[asyncio.Task] = []  # 定时任务列表
        self._running = False
        self._cron_jobs: list[CronJob] = []
```

---

## 三、检查过程（如何检查 HEARTBEAT.md）

### 3.1 读取 HEARTBEAT.md

```python
async def _run_heartbeat(self) -> Optional[str]:
    # 1. 读取 HEARTBEAT.md 文件内容
    if self._workspace.is_empty_heartbeat():
        return None  # 空文件，不检查

    heartbeat_content = self._workspace.heartbeat_md() or ""

    # 2. 构造检查提示词
    prompt = HEARTBEAT_PROMPT
    if heartbeat_content:
        prompt = f"{HEARTBEAT_PROMPT}\n\nYour HEARTBEAT.md:\n{heartbeat_content}"

    # 3. 发送个 AI 大脑检查
    response = await self._agent.arun(prompt)
    content = str(response.content) if response and response.content else ""

    # 4. 返回检查结果（或者 None 如果一切正常）
    return self._filter_response(content)
```

### 3.2 检查提示词

```python
HEARTBEAT_PROMPT = """Read HEARTBEAT.md in your workspace if it exists.
检查清单中的每个项目，确定是否有任何事情需要立即处理。
如果不需要处理，回复 HEARTBEAT_OK（以及其他非常简短的说明）。
如果有问题需要处理，清楚地描述它，以便用户可以采取行动。"""
```

AI 收到这个提示词后，会：
- 读取 HEARTBEAT.md 的内容
- 检查每个项目是否完成
- 回复"HEARTBEAT_OK"表示一切正常，或者描述问题

---

## 四、两种心跳模式

### 4.1 心跳检查（Heartbeat）

定期检查工作状态，使用主 AI 会话（有完整对话历史）：

```python
async def _run_heartbeat_loop(self) -> None:
    """主心跳循环"""
    interval_seconds = self._config.heartbeat.interval_minutes * 60

    while self._running:
        # 检查是否在"工作时间"内
        if self._is_active_hours():
            result = await self._run_heartbeat()  # 执行检查
            if result:
                self._on_alert(result)  # 有问题，发送警报
        else:
            logger.debug("Outside active hours — skipping heartbeat")

        # 等待下一个检查周期
        await asyncio.sleep(interval_seconds)
```

### 4.2 定时任务（Cron Jobs）

可以注册多个定时任务，每个任务有自己的执行时间：

```python
class CronJob:
    name: str           # 任务名称
    schedule: str        # 时间表（比如 "0 9 * * 1-5" = 每天早上9点周一到周五）
    prompt: str          # 发送什么消息
    skill: Optional[str] = None  # 使用什么技能
    isolated: bool = False  # 是否在新会话中运行
    model_id: Optional[str] = None  # 使用什么模型
    provider: Optional[str] = None  # 使用什么提供商
    enabled: bool = True
```

---

## 五、调度时间解析

### 5.1 支持两种时间格式

**格式1：间隔字符串**
```
30m     → 30分钟
1h      → 1小时
6h      → 6小时
2h30m   → 2小时30分钟
45s     → 45秒
```

**格式2：Cron 表达式**
```
0 9 * * 1-5    → 每天早上9点，周一到周五
*/15 * * * *  → 每15分钟
0 0 * * *      → 每天午夜
```

### 52 解析代码

```python
@staticmethod
def _seconds_until_next(schedule: str) -> float:
    """计算距离下次执行还有多少秒"""

    # 先尝试间隔字符串（如 "30m"）
    interval_pattern = re.compile(
        r'^(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s)?$',
        re.IGNORECASE,
    )
    m = interval_pattern.match(schedule)
    if m and any(m.group(k) for k in ("hours", "minutes", "seconds")):
        total = 0
        if m.group("hours"):
            total += int(m.group("hours")) * 3600
        if m.group("minutes"):
            total += int(m.group("minutes")) * 60
        if m.group("seconds"):
            total += int(m.group("seconds"))
        return float(total)

    # 再尝试 Cron 表达式
    try:
        from croniter import croniter
        now = datetime.now()
        ci = croniter(schedule, now)
        next_dt = ci.get_next(datetime)
        return max(0.0, (next_dt - now).total_seconds())
    except ImportError:
        pass

    return -1.0  # 解析失败
```

---

## 六、警报系统

### 6.1 on_alert 回调

当发现问题，HeartbeatDaemon 调用 `on_alert` 回调：

```python
def on_alert(msg: str) -> None:
    # 在 TUI 中，这会发送 HeartbeatAlert 消息
    self._app.post_message(HeartbeatAlert(msg))
```

### 6.2 TUI 中的显示

```
收到 HeartbeatAlert 消息后：
    ↓
NotificationPanel.add_heartbeat_alert()  → 显示在右侧面板
    ↓
ChatLog.add_notification()               → 显示在对话区域
    ↓
终端响铃（bell）                          → 引起注意
```

### 6.3 HEARTBEAT_OK 过滤

如果 AI 回复的是"HEARTBEAT_OK"（一切正常），就**不发送警报**：

```python
def _filter_response(self, content: str) -> Optional[str]:
    if HEARTBEAT_OK_TOKEN in content:
        # 如果回复很短（少于阈值），认为是正常的
        if len(content) <= self._config.heartbeat.ok_threshold_chars:
            return None  # 不发送警报
        # 否则去掉 HEARTBEAT_OK 标记后返回
        content = content.replace(HEARTBEAT_OK_TOKEN, "").strip()
    return content if content else None
```

---

## 七、工作时间限制

HeartbeatDaemon 可以在"工作时间"内才执行检查：

```python
def _is_active_hours(self) -> bool:
    """检查当前时间是否在配置的 active hours 内"""
    now = datetime.now().time()
    start_h, start_m = map(int, self._config.heartbeat.active_hours_start.split(":"))
    end_h, end_m = map(int, self._config.heartbeat.active_hours_end.split(":"))
    start = time(start_h, start_m)
    end = time(start_h, end_m)

    if start <= end:
        # 普通范围（如 9:00 - 18:00）
        return start <= now <= end
    else:
        # 跨越午夜的范围（如 22:00 - 06:00）
        return now >= start or now <= end
```

---

## 八、AgentDriver 中的集成

在 `driver.py` 中，HeartbeatDaemon 被启动和停止：

```python
class AgentDriver:
    def start_heartbeat(self) -> None:
        from agnoclaw.config import get_config
        cfg = get_config()

        if not cfg.heartbeat.enabled:
            return  # 配置中禁用心跳
        if self._agent.workspace.is_empty_heartbeat():
            return  # 没有 HEARTBEAT.md 文件

        from agnoclaw.heartbeat import HeartbeatDaemon

        # 设置警报回调
        def on_alert(msg: str) -> None:
            self._app.post_message(HeartbeatAlert(msg))

        # 启动心跳守护进程
        self._daemon = HeartbeatDaemon(self._agent, on_alert=on_alert, config=cfg)
        self._daemon.start()

        # 启动心跳计时器（每分钟发送一次 HeartbeatTick）
        self._heartbeat_tick_task = asyncio.create_task(
            self._heartbeat_ticker(), name="agnoclaw-hb-tick"
        )

    def stop_heartbeat(self) -> None:
        if self._daemon:
            self._daemon.stop()
            self._daemon = None
        if self._heartbeat_tick_task:
            self._heartbeat_tick_task.cancel()
            self._heartbeat_tick_task = None
```

---

## 九、完整流程图

```
启动 TUI
    ↓
AgentDriver.start_heartbeat()
    ↓
HeartbeatDaemon.start()
    ↓
┌─────────────────────────────────────────────────────────┐
│  主循环（每 N 分钟执行一次）                            │
│    ↓                                                   │
│    检查是否在工作时间内？                               │
│      ↓ 否 → 等待 N 分钟后再检查                        │
│      ↓ 是 →                                            │
│    读取 HEARTBEAT.md                                   │
│      ↓                                                 │
│    发送检查请求给 AI 大脑                               │
│      ↓                                                 │
│    AI 回复：HEARTBEAT_OK？                             │
│      ↓ 是 → 不发送警报                                 │
│      ↓ 否 → 发送 HeartbeatAlert(msg)                  │
│           ↓                                            │
│    NotificationPanel 显示警报                         │
│    ChatLog 显示通知                                     │
│    响铃                                               │
│      ↓                                                 │
│    等待 N 分钟                                         │
└─────────────────────────────────────────────────────────┘

同时（并行）：

每分钟：
    _heartbeat_ticker() → 发送 HeartbeatTick(n)
         ↓
    AgnoStatusBar.update_heartbeat(n)
```

---

## 十、思考题

1. 如果 HEARTBEAT.md 文件是空的，HeartbeatDaemon 会做什么？
2. 为什么 HeartbeatDaemon 要在"工作时间"内才检查？不在工作时间检查有什么好处？
3. 如果 AI 大脑在处理心跳检查时"卡住了"（响应很慢），会发生什么？

---

> 附加篇2：《TUI 之 08：Skill 系统 —— 技能是如何工作的》——深入解析 SKILL.md 的结构和技能注入机制