# TUI 系列 06： Streaming 实现 —— 文字如何逐字出现

> 目标：小朋友也能看懂！用一个"打字机"的比喻来讲清楚，AI 的回复是如何像"打字机一样"逐字显示出来的。

---

## 一、"打字机"比喻

想象你有一台老式**打字机**：
- 普通人打字：先把所有字打完，再一起展示给你
- AI 的流式输出：像一个超级打字机，**打一个字就给你看一个字**

```
普通人打字：
    等待...
    等待...
    "好的，我来帮你写代码"（一下子全部显示）

AI 流式输出（打字机模式）：
    打"好" → 显示"好"
    打"的" → 显示"好的"
    打"，" → 显示"好的，"
    打"我" → 显示"好的，我"
    ...（继续直到完成）
```

---

## 二、流式输出的好处

### 2.1 不需要等待

如果 AI 要花 10 秒思考，传统方式你需要等 10 秒才能看到任何内容。而流式输出让你**第 1 秒就能看到开头**。

### 2.2 知道 AI 在工作

逐字显示让你知道 AI 还在"思考"，不是卡住了。

### 2.3 提前知道答案

有时候 AI 的前几个字就能让你知道答案是否靠谱。

---

## 三、流式输出的核心机制

### 3.1 三种状态

ChatLog 在流式输出时，会经历三种状态：

```
状态1：正在输入（streaming）
    ├── 有一个活动的 StreamingWidget
    ├── 不断收到 StreamChunk
    └── 屏幕显示：Agent: 你好...

状态2：输入完成（done）
    ├── 把 StreamingWidget 变成 Markdown
    └── 屏幕显示：渲染后的格式化文本

状态3：等待下一轮（idle）
    └── 用户输入下一个问题
```

### 3.2 三个关键变量

```python
class ChatLog:
    def __init__(self):
        self._is_streaming = False      # 是否正在输入？
        self._streaming_widget = None   # 当前正在显示的组件
        self._streaming_text = []       # 累计的文本片段
```

---

## 四、StreamChunk 的处理流程

当 AgentDriver 收到 AI 的一个字（chunk）时：

```
AI 回复："好"
    ↓
AgentDriver.post_message(StreamChunk("好"))
    ↓
AgnoClawApp.on_stream_chunk(StreamChunk("好"))
    ↓
ChatLog.append_chunk("好")
    ↓
1. 把"好"加入列表：self._streaming_text = ["好"]
2. 更新显示：self._streaming_widget.update("好")
3. 滚动到底部
```

---

## 五、append_chunk 的详细过程

```python
def append_chunk(self, text: str) -> None:
    """
    把新收到的字加到屏幕上
    """
    # 只有正在流式输出时才能追加
    if self._is_streaming and self._streaming_widget is not None:
        # 1. 把新字加入累计列表
        self._streaming_text.append(text)

        # 2. 把列表合并成完整字符串
        full_text = "".join(self._streaming_text)
        # 例如：["好", "的", "，"] → "好的，"

        # 3. 更新屏幕上的显示
        self._streaming_widget.update(full_text)

        # 4. 滚动到最底部（看到最新内容）
        self.scroll_end(animate=False)
```

---

## 六、完成时的处理（finish_agent_response）

当 AI 完成回复，发送 `StreamDone` 时：

```python
def finish_agent_response(self, full_text: str = "") -> None:
    # 1. 标记流式结束
    self._is_streaming = False

    # 2. 取出累计的文本
    final = full_text or "".join(self._streaming_text)
    # 如果外面传了 full_text 就用它，否则用累计的

    # 3. 清空累计列表（准备下一轮）
    self._streaming_text.clear()

    # 4. 把临时显示变成 Markdown
    if self._streaming_widget is not None:
        if final.strip():  # 如果有内容
            try:
                # 用 Rich 库渲染 Markdown
                # 比如 **粗体** 会变成真正的粗体
                # 比如 `代码` 会变成等宽字体
                self._streaming_widget.update(RichMarkdown(final))
            except Exception:
                # 如果 Markdown 渲染失败，就显示原文
                self._streaming_widget.update(final)
        else:
            # 如果是空内容
            self._streaming_widget.update("")

        # 5. 清理引用（允许垃圾回收）
        self._streaming_widget = None

    # 6. 滚动到底部
    self.scroll_end(animate=False)
```

---

## 七、Markdown 渲染示例

假设 AI 回复了：
```
我来帮你写代码。首先，打开终端...
```

### 渲染前（纯文本）：
```
Agent: 我来帮你写代码。首先，打开终端...
```

### 渲染后（Markdown）：
```
Agent:
我来帮你写代码。首先，打开终端...
    ↑ 正常段落显示
```

更复杂的例子，如果 AI 回复了：
```
**步骤1**：打开终端
**步骤2**：输入 `python --version`
```

### 渲染后会变成：
```
步骤1（粗体）：打开终端
步骤2（粗体）：输入 python --version（等宽字体）
```

---

## 八、Streaming 的完整时序图

```
用户：帮我写代码
    ↓
InputBar 发送 UserSubmitted
    ↓
AgnoClawApp.on_user_submitted()
    ↓
ChatLog.start_agent_response()
    ↓
1. 添加 "Agent" 标签
2. 创建 _streaming_widget = Static("...")
3. 添加到界面
4. _is_streaming = True
    ↓
AgentDriver.send_message()
    ↓
┌─────────────────────────────────────────────────────────────┐
│ AI 回复流开始                                               │
│    ↓                                                       │
│    StreamChunk("好")                                        │
│        ↓                                                   │
│    ChatLog.append_chunk("好")                               │
│        ↓ 显示 "好"                                         │
│    StreamChunk("的")                                        │
│        ↓                                                   │
│    ChatLog.append_chunk("的")                              │
│        ↓ 显示 "好的"                                       │
│    StreamChunk("，")                                       │
│        ↓                                                   │
│    ChatLog.append_chunk("，")                              │
│        ↓ 显示 "好的，"                                     │
│    ...（继续）                                             │
│    ↓                                                       │
│    StreamDone("好的，我来帮你...")                          │
│        ↓                                                   │
│    ChatLog.finish_agent_response()                         │
│        ↓                                                   │
│    _streaming_widget.update(RichMarkdown(...))（渲染Markdown）│
│    _is_streaming = False                                   │
│    _streaming_widget = None                                │
│    InputBar.set_disabled(False)                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 九、为什么用 list 来累计文本？

你可能会问：为什么要用 `self._streaming_text = []` 来累计，而不是每次直接更新？

**答案：因为字符串不可变！**

```python
# 错误做法：每次都创建新字符串
text = ""  # 空字符串
text += "好"   # 创建新字符串 "好"
text += "的"   # 创建新字符串 "好的"
text += "，"   # 创建新字符串 "好的，"
# 每次 + 都会创建新字符串，效率低

# 正确做法：用列表累计，最后一次性合并
self._streaming_text = []
self._streaming_text.append("好")
self._streaming_text.append("的")
self._streaming_text.append("，")
final = "".join(self._streaming_text)  # "好的，" 一次性创建
```

---

## 十、Streaming 的状态机

```
                    start_agent_response()
                          ↓
                        ┌────┐
                        │IDLE│ ← 初始状态
                        └──┬─┘
                           │
          UserSubmitted 事件到达
                           ↓
                        ┌───────┐
          start_agent   │STREAMING│ ← _is_streaming = True
          response()    └───┬───┘
                           │
              ┌────────────┼────────────┐
              ↓            ↓            ↓
        StreamChunk   StreamError   StreamDone
              ↓            ↓            ↓
      append_chunk()   显示错误    finish_agent
              │            │           _response()
              │            │            ↓
              └────────────┴────→ ┌────┐
                                 │IDLE│ ← 回到初始状态
                                 └────┘
```

---

## 十一、思考题

1. 如果 AI 回复很快（比如 0.1 秒），用户会看到什么？
2. 如果 AI 回复很长（几千字），ChatLog 会怎么处理？
3. 如果网络断了（在流式输出过程中），会发生什么？

---

> 附加篇：《TUI 之 07：Heartbeat 心跳守护者》——深入解析心跳监控系统的实现