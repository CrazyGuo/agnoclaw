# TUI 系列总结：从命令行到界面的完整旅程

> 目标：用一张大地图把整个 TUI 系统的知识点串联起来，让你对整个系统有全景认识。

---

## 一、整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        用户：agnoclaw tui                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  cli/main.py :: tui()                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  _build_agent(model, provider, session, workspace, debug,         │   │
│  │                  permission_mode)                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  AgentHarness (agent.py)                                        │   │
│  │  - 读取工作区文件（SOUL.md, USER.md, IDENTITY.md...）            │   │
│  │  - 决定用哪个 AI 模型（claude-sonnet-4-6, gpt-4o...）           │   │
│  │  - 创建 Agno Agent（真正的大脑）                                │   │
│  │  - 注册技能（SkillRegistry）                                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  AgnoClawApp (tui/app.py)                                       │   │
│  │  - compose() 组装所有 Widget                                     │   │
│  │  - BINDINGS 定义快捷键                                           │   │
│  │  - on_* 处理所有消息事件                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│              ┌─────────────────────┴─────────────────────┐            │
│              ▼                     ▼                     ▼            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │   HeaderBar      │  │   ChatLog         │  │ NotificationPanel│     │
│  │   (顶部状态栏)    │  │   (对话区域)       │  │   (通知面板)      │     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘     │
│              │                     │                     │            │
│              │         ┌──────────┴──────────┐           │            │
│              │         ▼                     ▼           │            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │   InputBar       │  │   LogViewer       │  │   AgnoStatusBar  │     │
│  │   (输入框)       │  │   (日志面板)       │  │   (状态栏)        │     │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │      AgentDriver              │
                    │   (连接大脑和界面的桥梁)        │
                    │  - send_message()            │
                    │  - start_heartbeat()         │
                    │  - _heartbeat_ticker()        │
                    └───────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
        ┌─────────────────────┐         ┌─────────────────────┐
        │   HeartbeatDaemon   │         │   Agno Agent        │
        │   (心跳守护者)       │         │   (AI 大脑)         │
        │   - _run_heartbeat()│         │   - arun()          │
        │   - add_cron_job()  │         │   - stream=True     │
        └─────────────────────┘         └─────────────────────┘
```

---

## 二、数据流：用户输入 → AI 回复

```
1. 用户在 InputBar 输入 "帮我写代码"
                                    │
                                    ▼
2. InputBar.on_input_submitted() 发送 UserSubmitted
                                    │
                                    ▼
3. AgnoClawApp.on_user_submitted() 被调用
   - ChatLog.start_agent_response() 准备显示
   - InputBar.set_disabled(True) 禁用输入
   - run_worker(agent_driver.send_message(...))
                                    │
                                    ▼
4. AgentDriver.send_message() 异步运行
   - 调用 agent.arun(text, stream=True)
                                    │
                                    ▼
5. AI 开始处理，发送 StreamChunk
   ┌─────────────────────────────────────────────────────────────┐
   │  StreamChunk("好") → on_stream_chunk() → ChatLog.append_chunk()
   │  StreamChunk("的") → on_stream_chunk() → ChatLog.append_chunk()
   │  StreamChunk("，") → on_stream_chunk() → ChatLog.append_chunk()
   │  ... (持续到完成)
   │  StreamDone("好的，我来帮你...") → on_stream_done()
   └─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
6. ChatLog.finish_agent_response() 渲染 Markdown
   - InputBar.set_disabled(False) 恢复输入
```

---

## 三、消息事件系统

| 消息 | 发送者 | 接收者 | 作用 |
|------|--------|--------|------|
| `UserSubmitted` | InputBar | AgnoClawApp | 用户按了回车 |
| `StreamChunk` | AgentDriver | AgnoClawApp | AI 回复的一个字 |
| `StreamDone` | AgentDriver | AgnoClawApp | AI 回复完成 |
| `StreamError` | AgentDriver | AgnoClawApp | AI 出错了 |
| `ToolCallStarted` | AgentDriver | AgnoClawApp | 工具开始执行 |
| `ToolCallCompleted` | AgentDriver | AgnoClawApp | 工具执行完成 |
| `HeartbeatAlert` | HeartbeatDaemon | AgnoClawApp | 心跳发出警告 |
| `HeartbeatTick` | _heartbeat_ticker | AgnoClawApp | 心跳每分钟一次 |
| `CronResult` | HeartbeatDaemon | AgnoClawApp | 定时任务完成 |

---

## 四、文件对应关系

| 文件 | 作用 | 关键类/函数 |
|------|------|------------|
| `cli/main.py` | TUI 入口，_build_agent | `tui()`, `_build_agent()` |
| `agent.py` | AgentHarness 核心 | `class AgentHarness` |
| `workspace.py` | 工作区管理 | `class Workspace` |
| `skills/loader.py` | SKILL.md 解析 | `load_skill_from_path()` |
| `skills/registry.py` | 技能注册表 | `class SkillRegistry` |
| `heartbeat/daemon.py` | 心跳守护 | `class HeartbeatDaemon` |
| `tui/app.py` | TUI 主应用 | `class AgnoClawApp` |
| `tui/driver.py` | 大脑-界面桥梁 | `class AgentDriver` |
| `tui/events.py` | 消息定义 | `StreamChunk`, `UserSubmitted`... |
| `tui/widgets/chat_log.py` | 对话组件 | `class ChatLog` |
| `tui/widgets/header_bar.py` | 顶部状态栏 | `class HeaderBar` |
| `tui/widgets/input_bar.py` | 输入框 | `class InputBar` |
| `tui/widgets/notification_panel.py` | 通知面板 | `class NotificationPanel` |
| `tui/widgets/status_bar.py` | 底部状态栏 | `class AgnoStatusBar` |
| `tui/widgets/log_viewer.py` | 日志面板 | `class LogViewer` |
| `tui/screens.py` | 技能选择器 | `class SkillPickerScreen` |

---

## 五、布局层次

```
AgnoClawApp
└── VerticalScroll
    ├── HeaderBar (dock: top, height: 1)
    ├── Horizontal
    │   ├── ChatLog (height: 1fr)
    │   └── NotificationPanel (width: 35)
    ├── LogViewer (height: 12, display: none)
    ├── InputBar (dock: bottom, height: 3)
    └── AgnoStatusBar (dock: bottom, height: 1)
```

---

## 六、快捷键一览

| 快捷键 | 作用 |
|--------|------|
| `Ctrl+Q` | 退出 |
| `Ctrl+N` | 显示/隐藏通知面板 |
| `Ctrl+S` | 打开技能选择器 |
| `Ctrl+L` | 显示/隐藏日志面板 |
| `Escape` | 关闭弹窗 |
| `Enter` | 发送消息 |
| `Tab` | 自动补全命令 |

---

## 七、AgentHarness 的初始化流程

```
1. get_config() → 加载配置
         │
         ▼
2. Workspace(path) → 读取工作区文件
         │
         ▼
3. _resolve_model() → 解析模型和提供商
         │
         ▼
4. SystemPromptBuilder → 组装系统提示词
         │
         ▼
5. get_default_tools() → 获取默认工具
         │
         ▼
6. Agent(model, tools, system_prompt, ...) → 创建 Agno Agent
         │
         ▼
7. SkillRegistry(ws.skills_dir()) → 初始化技能注册表
         │
         ▼
8. PermissionController → 设置权限控制器
```

---

## 八、心跳系统的工作流程

```
HeartbeatDaemon.start()
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│ _run_heartbeat_loop()  (每 N 分钟执行一次)               │
│   │                                                  │
│   ├── _is_active_hours() → 检查是否工作时间           │
│   │                                                  │
│   ├── _run_heartbeat()                               │
│   │   │                                              │
│   │   ├── 读取 HEARTBEAT.md                          │
│   │   ├── 发送给 AI 大脑检查                          │
│   │   └── _filter_response() → HEARTBEAT_OK?        │
│   │         │                                        │
│   │         ├── 是 → 不发送警报                       │
│   │         └── 否 → on_alert(result)                │
│   │               │                                  │
│   │               └── HeartbeatAlert → NotificationPanel│
│   │                                                  │
│   └── asyncio.sleep(interval_seconds)                │
└──────────────────────────────────────────────────────────┘

同时（并行）：

_heartbeat_ticker()  (每60秒)
         │
         └── HeartbeatTick(n) → AgnoStatusBar.update_heartbeat(n)
```

---

## 九、技能的加载流程

```
用户：/skill code-review src/app.py
         │
         ▼
SkillRegistry.load_skill("code-review")
         │
         ▼
load_skill_from_path(skills/code-review/SKILL.md)
         │
         ├── 解析 frontmatter (元数据)
         ├── 提取 content (指令内容)
         └── 构建 Skill 对象
         │
         ▼
skill.render(arguments="src/app.py")
         │
         ├── 替换 $ARGUMENTS
         ├── 替换 $ARGUMENTS[N]
         └── 执行 !`cmd` (如果 allow_exec=True)
         │
         ▼
把渲染后的内容注入系统提示词
         │
         ▼
AI 处理请求
```

---

## 十、Workspace 的层级查找

```
read_file("soul")
         │
         ▼
search_dirs = [workspace, project, global]
         │
         ▼
for each dir in search_dirs:
    path = dir / "SOUL.md"
    if path.exists():
        return content  # 找到就返回，不继续找
         │
         ▼
都没找到 → return None
```

---

## 十一、Streaming 的状态机

```
                    start_agent_response()
                          │
                    ┌─────▼─────┐
                    │  IDLE     │
                    └─────┬─────┘
                          │
              UserSubmitted 事件
                          │
                    ┌─────▼─────┐
         start()    │ STREAMING │  _is_streaming = True
                    └─────┬─────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    StreamChunk      StreamError      StreamDone
         │                │                │
    append_chunk()   显示错误      finish_agent_response()
         │                │                │
         │                │         ┌─────▼─────┐
         └────────────────┴────────►│   IDLE   │
                                     └─────────┘
```

---

## 十二、关键数字总结

| 项目 | 数字 | 说明 |
|------|------|------|
| MEMORY_STARTUP_LINES | 200 | MEMORY.md 只加载前 200 行 |
| BOOTSTRAP_MAX_CHARS | 20,000 | 单个文件最大字符数 |
| BOOTSTRAP_TOTAL_MAX_CHARS | 150,000 | 所有文件总最大字符数 |
| NotificationPanel width | 35 | 固定 35 字符宽度 |
| LogViewer height | 12 | 默认隐藏，高度 12 行 |
| InputBar height | 3 | 底部输入框高度 |
| HeaderBar height | 1 | 顶部状态栏高度 |
| StatusBar height | 1 | 底部状态栏高度 |
| 心跳 tick 间隔 | 60 秒 | 每分钟发送一次 HeartbeatTick |

---

## 十三、学习路径建议

1. **先看第 01 篇**：了解整个入口和组装过程
2. **再看第 02 篇**：深入理解 AgentHarness 核心
3. **再看第 03 篇**：理解 Textual 界面如何绘制
4. **再看第 04 篇**：理解事件系统
5. **再看第 05 篇**：理解布局系统
6. **再看第 06 篇**：理解流式输出
7. **再看第 07 篇**：理解心跳系统
8. **再看第 08 篇**：理解技能系统
9. **再看第 09 篇**：理解工作区系统
10. **再看本篇**：串联所有知识点

---

## 十四、常见问题

**Q: 为什么 Textual 能画出界面？**
A: Textual 使用了 Rich 库来渲染文字和颜色，用 ANSI 转义序列来控制终端的光标位置和颜色。

**Q: 为什么 AI 回复是逐字显示的？**
A: 因为 AgentHarness.arun() 使用了 `stream=True` 参数，这会让 AI 模型边生成边返回，AgentDriver 收到每个 chunk 后发送给界面。

**Q: HeartbeatDaemon 和主 AI 会话是同一个吗？**
A: 是的，HeartbeatDaemon 在主会话中运行检查，这样它能访问完整的对话历史。

**Q: 如果 HEARTBEAT.md 是空的，会发生什么？**
A: HeartbeatDaemon 会跳过检查，不消耗任何 AI 调用。

**Q: Skills 是如何注入到系统提示词的？**
A: SkillRegistry.load_skill() 返回 Skill 对象，render() 方法把内容中的占位符替换后，注入到系统提示词中。

---

> 恭喜你完成了 TUI 系列的所有学习！现在你对 agnoclaw 的 TUI 系统有了全面的理解。