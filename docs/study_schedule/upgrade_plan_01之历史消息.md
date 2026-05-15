# TUI 聊天历史恢复 — 计划

## Context

当前 TUI 的 `ChatLog` 只负责**展示**消息，不存储历史。每次用户发消息，`AgentDriver.send_message` 只传递当前输入的 `text` 给 `arun()`。

**好消息**：Agno Agent 内部通过 `session_id` 管理会话历史，`add_history_to_context=True` 让模型在每次 `arun` 时自动收到历史上下文。所以**同一 TUI 会话内**，历史是正常的。

**真正的问题**：当 TUI 重启后，之前的历史消息不会加载到 `ChatLog` 显示。

---

## 修复方案

### 步骤 1：`ChatLog` 添加 `add_history_assistant_message`

修改 `src/agnoclaw/tui/widgets/chat_log.py`，在 `finish_agent_response` 之后添加：

```python
def add_history_assistant_message(self, text: str) -> None:
    """Display an assistant message from history (no streaming, rendered as Markdown)."""
    label = Static("Agent", classes="agent-label", id=self._next_id("al"))
    msg_body = Static(text, classes="message-text", id=self._next_id("am"))
    self.mount(label)
    if text.strip():
        try:
            msg_body.update(RichMarkdown(text))
        except Exception:
            pass
    self.mount(msg_body)
    self.scroll_end(animate=False)
```

### 步骤 2：`App.on_mount` 加载历史

修改 `src/agnoclaw/tui/app.py`，在 `on_mount` 中 `start_heartbeat` 之后插入：

```python
def on_mount(self) -> None:
    from agnoclaw.config import get_config
    cfg = get_config()
    if cfg.theme and cfg.theme != "textual-dark":
        try:
            self.theme = cfg.theme
        except Exception:
            pass

    self._agent_driver.start_heartbeat()
    self._load_chat_history()                            # ← 新增
    self.query_one("#input-bar", InputBar).focus()

def _load_chat_history(self) -> None:
    """Load prior session messages from storage into ChatLog."""
    chat = self.query_one("#chat-log", ChatLog)
    try:
        history = self._agent.get_chat_history()
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "") or ""
            if role == "user":
                chat.add_user_message(content)
            elif role == "assistant" and content:
                chat.add_history_assistant_message(content)
    except Exception:
        pass  # 历史加载失败不影响启动
```

### 关键文件

| 文件 | 改动 |
|------|------|
| `src/agnoclaw/tui/widgets/chat_log.py` | 添加 `add_history_assistant_message()` |
| `src/agnoclaw/tui/app.py` | `on_mount` 调用 `_load_chat_history()`，`_load_chat_history()` 方法 |

### 验证方法

1. 启动 TUI，发送几条消息（包含工具调用）
2. 退出 TUI（Ctrl+Q）
3. 重新启动 TUI，观察历史消息是否加载显示
4. 继续对话，验证模型能正确理解上下文