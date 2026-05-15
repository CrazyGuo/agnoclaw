# TUI 系列 05： 布局详解 —— 界面是如何排列的

> 目标：小朋友也能看懂！用一个"建筑图纸"的比喻来讲清楚，Textual 的 CSS 布局系统是如何让各个组件排列在正确位置的。

---

## 一、"建筑图纸"比喻

想象你要建造一栋房子：
- **建筑图纸（Layout）** 告诉你每个房间在哪里
- **房间（Widget）** 是具体的东西（厨房、卧室、客厅）
- **房间的顺序** 决定了你进入房子的路线

在 Textual 中，界面就是一张"建筑图纸"，每个组件都是图纸上的一个"房间"。

```
agnoclaw TUI 的"建筑图纸"
┌─────────────────────────────────────────────────┐
│  顶部（HeaderBar）—— 门牌号，显示这栋楼的名字    │
├────────────────────────────────┬────────────────┤
│  大厅（ChatLog）                │  右侧房          │
│  主要聊天的地方                 │  NotificationPanel│
│                                │  公告板          │
├────────────────────────────────┴────────────────┤
│  输入口（InputBar）—— 入口门                     │
├─────────────────────────────────────────────────┤
│  地下室（LogViewer）—— 默认隐藏，按键显示        │
├─────────────────────────────────────────────────┤
│  底部状态栏（AgnoStatusBar）—— 地基              │
└─────────────────────────────────────────────────┘
```

---

## 二、布局的核心概念

### 2.1 dock——固定位置

Textual 允许你把组件"钉"在某个边缘：

```css
HeaderBar {
    dock: top;    /* 钉在顶部 */
    height: 1;     /* 高度1行 */
}

InputBar {
    dock: bottom;  /* 钉在底部 */
    height: 3;     /* 高度3行 */
}

AgnoStatusBar {
    dock: bottom;  /* 钉在底部（InputBar下方） */
    height: 1;     /* 高度1行 */
}
```

### 2.2 height: 1fr——占满剩余空间

ChatLog 使用 `height: 1fr`，意思是"占满所有剩余空间"：

```css
ChatLog {
    height: 1fr;   /* fr = fraction（分数），占剩余空间的全部 */
}
```

就像一个可伸缩的房间，墙可以往外推，直到填满所有空隙。

### 2.3 width: 35——固定宽度

NotificationPanel 使用固定宽度：

```css
NotificationPanel {
    width: 35;   /* 固定35个字符宽度 */
    height: 1fr; /* 高度占满 */
}
```

---

## 三、Horizontal 容器——并排房间

ChatLog 和 NotificationPanel 需要**并排**显示。这就需要 `Horizontal` 容器：

```python
def compose(self):
    return VerticalScroll(
        HeaderBar(),
        Horizontal(        # ← 把两个房间并排放置
            ChatLog(),           # 左边的房间
            NotificationPanel(), # 右边的房间
        ),
        ...
    )
```

效果图：

```
┌──────────────────────────────────┬──────────────┐
│                                  │              │
│  ChatLog（大厅）                  │ NotificationPanel │
│  （占满大部分空间）               │ 固定宽度35   │
│                                  │              │
└──────────────────────────────────┴──────────────┘
```

---

## 四、每个组件的 CSS 详解

### 4.1 HeaderBar

```css
HeaderBar {
    dock: top;           /* 固定在顶部 */
    height: 1;           /* 1行高 */
    background: $accent; /* 背景色（蓝色） */
    color: $text;        /* 文字白色 */
    padding: 0 1;        /* 左右各1个空格 */
    text-style: bold;    /* 粗体 */
}
```

**效果：**
```
┌─────────────────────────────────────────────────┐
│  agnoclaw · claude-sonnet-4-6 · session:abc123 │  ← 蓝色背景，白色粗体
└─────────────────────────────────────────────────┘
```

### 4.2 ChatLog

```css
ChatLog {
    height: 1fr;                        /* 占满剩余高度 */
    border: solid $surface-lighten-2;  /* 边框 */
    padding: 0 1;                      /* 左右边距 */
    scrollbar-size: 1 1;                /* 滚动条大小 */
}
```

**内部样式：**

```css
/* 用户消息标签 */
ChatLog .user-label {
    color: $text;
    text-style: bold;
    background: $primary-darken-3;  /* 深蓝色背景 */
    padding: 0 1;
    margin: 1 0 0 0;               /* 上边距1 */
}

/* AI消息标签 */
ChatLog .agent-label {
    color: $success;                  /* 绿色 */
    text-style: bold;
    margin: 1 0 0 0;
}

/* 工具调用指示器 */
ChatLog .tool-indicator {
    color: $text-muted;               /* 灰色 */
    padding: 0 2;
}
```

### 4.3 NotificationPanel

```css
NotificationPanel {
    width: 35;            /* 固定宽度35字符 */
    height: 1fr;          /* 占满剩余高度 */
    border: solid $surface-lighten-2;
    padding: 0 1;
}
```

**显示内容格式：**
```
┌──────────────────┐
│ Notifications    │  ← 标题（粗体）
├──────────────────┤
│ [HB] 14:30       │  ← 心跳警报（黄色）
│ HEARTBEAT.md...  │
│                  │
│ [cron] 14:25     │  ← 定时任务结果（青色）
│ 备份完成         │
└──────────────────┘
```

### 4.4 InputBar

```css
InputBar {
    dock: bottom;        /* 固定在底部 */
    height: 3;           /* 高度3行 */
    border: solid $surface-lighten-2;
    padding: 0 1;
}
InputBar:focus {
    border: solid $accent;  /* 聚焦时边框变蓝色 */
}
InputBar.-disabled {
    opacity: 0.5;           /* 禁用时半透明 */
}
```

**效果：**
```
┌─────────────────────────────────────────────────┐
│  > 你好...                                  /skill│  ← 底部输入框
└─────────────────────────────────────────────────┘
```

### 4.5 AgnoStatusBar

```css
AgnoStatusBar {
    dock: bottom;        /* 固定在底部（最下方） */
    height: 1;           /* 1行高 */
    background: $surface;  /* 深色背景 */
    color: $text-muted;     /* 灰色文字 */
    padding: 0 1;
}
```

**效果：**
```
┌─────────────────────────────────────────────────┐
│  ● heartbeat: 28m │ tools: 6 │ ready           │  ← 最底部状态栏
└─────────────────────────────────────────────────┘
```

### 4.6 LogViewer（隐藏面板）

```css
LogViewer {
    height: 12;               /* 高度12行 */
    border: solid $surface-lighten-2;
    display: none;            /* 默认隐藏！ */
}
LogViewer.-visible {
    display: block;            /* 加上这个类就显示 */
}
```

默认 `display: none`，所以你看不到它。按 `Ctrl+L` 才显示。

---

## 五、compose() 的组装顺序

**重要规则：** `compose()` 返回的组件顺序很重要！组件会按照顺序"放置"。

```python
def compose(self):
    return [
        HeaderBar(),          # 1. 先放顶部（dock: top）
        Horizontal(           # 2. 然后放中间的并排区域
            ChatLog(),
            NotificationPanel(),
        ),
        LogViewer(),          # 3. 然后放日志（默认隐藏）
        InputBar(),          # 4. 然后放输入框（dock: bottom）
        AgnoStatusBar(),     # 5. 最后放状态栏（dock: bottom）
    ]
```

**dock 的效果：**
- `dock: top` 的组件按顺序从顶部往下排
- `dock: bottom` 的组件按顺序从底部往上排

所以，即使 InputBar 写在 AgnoStatusBar 前面，AgnoStatusBar 还是会在最底部，因为它 `dock: bottom`。

---

## 六、VerticalScroll——滚动容器

整个布局包在一个 `VerticalScroll` 里：

```python
def compose(self):
    return VerticalScroll(
        HeaderBar(),
        Horizontal(
            ChatLog(),
            NotificationPanel(),
        ),
        LogViewer(),
        InputBar(),
        AgnoStatusBar(),
    )
```

`VerticalScroll` 让整个界面可以**上下滚动**，如果内容太多（比如对话很长），就会显示滚动条。

---

## 七、display: none 与类的切换

LogViewer 使用了一个技巧：**通过切换类来控制显示/隐藏**：

```python
# 默认 CSS
LogViewer {
    display: none;  /* 看不见 */
}

# 添加了 .visible 类之后
LogViewer.-visible {
    display: block;  /* 看见了！ */
}

# 切换方法
def toggle_visible(self) -> None:
    self.toggle_class("-visible")  # 切换类的有无
```

---

## 八、布局的完整 ASCII 图

```
┌─────────────────────────────────────────────────┐
│  HeaderBar (dock: top, height: 1)              │  ← 最顶部蓝色条
├────────────────────────────────┬────────────────┤
│                                │                │
│  ChatLog                       │ NotificationPanel│
│  (height: 1fr)                 │ (width: 35)    │
│  对话区域                       │ 通知区域       │
│  可滚动                         │ 可滚动         │
│                                │                │
├────────────────────────────────┴────────────────┤
│  LogViewer (height: 12, display: none)         │  ← 默认隐藏，按Ctrl+L显示
├─────────────────────────────────────────────────┤
│  InputBar (dock: bottom, height: 3)            │  ← 底部输入框
├─────────────────────────────────────────────────┤
│  AgnoStatusBar (dock: bottom, height: 1)        │  ← 最底部状态栏
└─────────────────────────────────────────────────┘
```

---

## 九、CSS 变量（颜色主题）

Textual 使用了 CSS 变量来定义颜色：

| 变量 | 含义 |
|------|------|
| `$accent` | 强调色（蓝色） |
| `$surface` | 表面色（深灰） |
| `$surface-lighten-2` | 稍微亮的灰 |
| `$text` | 主要文字色（白） |
| `$text-muted` | 次要文字色（灰） |
| `$success` | 成功色（绿） |
| `$error` | 错误色（红） |

这些变量让主题切换更容易。

---

## 十、思考题

1. 如果把 `HeaderBar` 的 `dock: top` 改成 `dock: bottom`，会发生什么？
2. 为什么 NotificationPanel 用固定宽度 `width: 35`，而 ChatLog 用 `height: 1fr`？
3. 如果没有 `VerticalScroll` 包裹整个布局，会发生什么？

---

> 下一篇：《TUI 之 06： Streaming 实现 —— 文字如何逐字出现》——深入解析流式输出的实现原理