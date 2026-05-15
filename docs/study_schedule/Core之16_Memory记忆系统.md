# Core 系列 16： Memory 记忆系统 —— 长期学习

> 目标：小朋友也能看懂！用一个"笔记本和大脑"的比喻来讲清楚，agnoclaw 的记忆系统是如何工作的，LearningMachine 和 MemoryManager 有什么区别。

---

## 一、"笔记本和大脑"比喻

想象 AI 有两种记忆方式：

**第一种：笔记本（Workspace 文件）**
- 记在笔记本上的东西，AI 可以随时翻看
- 但笔记本不会"自动总结"，需要 AI 手动写
- 例：MEMORY.md、AGENTS.md、SOUL.md

**第二种：长期记忆大脑（LearningMachine）**
- AI 会自动学习，把重要的东西记住
- 这些记忆会跨会话保存
- 例：学会了一个模式，下次自动应用

---

## 二、两层记忆架构

文件：`src/agnoclaw/memory.py`

```
记忆层级（从近到远）：

┌─────────────────────────────────────────────────────────────┐
│  第一层：会话记忆（Session Memory）                          │
│  当前对话的上下文，在内存中，关闭后消失                     │
├─────────────────────────────────────────────────────────────┤
│  第二层：工作区文件（Workspace Files）                       │
│  AGENTS.md, SOUL.md, USER.md, MEMORY.md                      │
│  跨会话存在，人工写入                                       │
├─────────────────────────────────────────────────────────────┤
│  第三层：LearningMachine（机构记忆）                        │
│  user_profile, user_memory, learned_knowledge,             │
│  entity_memory, decision_log                               │
│  跨会话存在，AI 自动学习                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、build_learning_machine() 工厂函数

```python
def build_learning_machine(
    db,                           # 数据库连接
    model_id,                     # 模型 ID
    provider,                     # 提供商
    namespace,                    # 命名空间（团队隔离）
    mode,                         # 学习模式
    enable_user_memory,          # 是否启用用户记忆
    enable_session_context,      # 是否启用会话上下文
) -> LearningMachine:
    """
    构建 Agno LearningMachine。
    LearningMachine 是跨会话的机构学习系统。
    """
```

### 3.1 记忆存储

**Per-user stores（可选，需要 enable_user_memory）**：
- `user_profile` — 用户基本信息
- `user_memory` — 用户偏好和习惯

**Institutional stores（总是启用）**：
- `learned_knowledge` — 学到的知识（跨用户共享）
- `entity_memory` — 实体记忆（知道某个项目、某个术语是什么）
- `decision_log` — 决策日志（为什么做了某个决定）

**Optional**：
- `session_context` — 会话上下文（需要 enable_session_context）

---

## 四、学习模式

```python
learning_mode: str = "agentic"
```

| 模式 | 含义 | 说明 |
|------|------|------|
| `always` | 每次运行后自动学习 | AI 每次完成任务后自动记录学到的东西 |
| `agentic` | AI 决定什么时候学习 | AI 判断什么东西值得记录（推荐） |
| `propose` | AI 提出学习建议 | AI 提出建议，用户审核后记录 |
| `hitl` | 用户必须批准 | 用户手动批准每个学习记录 |

---

## 五、build_memory_manager()（已废弃）

```python
def build_memory_manager(db, model_id, provider, namespace) -> MemoryManager:
    """
    [已废弃] 使用 build_learning_machine() 代替。
    """
```

`MemoryManager` 是旧的 API，`LearningMachine` 是新的。

---

## 六、在 AgentHarness 中的使用

```python
# agent.py 中
if self.config.enable_learning:
    self._learning_machine = build_learning_machine(
        db=self._db,
        model_id=self._model,
        provider=self._provider,
        namespace=learning_namespace,
        mode=self.config.learning_mode,
        enable_user_memory=enable_user_memory,
        enable_session_context=enable_session_context,
    )
    self._agent.learning = self._learning_machine
```

然后在系统提示词中注入学习指令：

```python
# prompts/system.py 中
if include_learning:
    parts.append(LEARNING_INSTRUCTIONS)
```

---

## 七、Team 中的 LearningMachine

```python
# teams.py 中
def _build_member_agent(
    member_name: str,
    model_id: str,
    provider: str,
    *,
    config: HarnessConfig,
    session_id: str,
    enable_learning: bool,
    backend: RuntimeBackend,
    skill_install_approver: SkillInstallApprover,
) -> AgentHarness:
    agent = AgentHarness(
        ...
        enable_learning=enable_learning,
        learning_namespace=f"team_{team_id}_{member_name}",  # 团队隔离
        ...
    )
```

每个团队成员有自己的 `learning_namespace`，这样团队之间不会互相干扰学习。

---

## 八、MEMORY.md vs LearningMachine

| 特征 | MEMORY.md | LearningMachine |
|------|-----------|-----------------|
| 来源 | 人工写入 | AI 自动学习 |
| 格式 | 纯文本 Markdown | 结构化数据库 |
| 更新 | AI 手动写入 | AI 自动记录 |
| 可见性 | AI 每次都读取 | AI 按需查询 |
| 持久性 | 跨会话（文件） | 跨会话（数据库） |
| 隔离性 | 按工作区 | 按 namespace |

---

## 九、思考题

1. 为什么 LearningMachine 需要 `namespace` 参数？有什么作用？
2. `learning_mode = "agentic"` 和 `learning_mode = "always"` 有什么区别？
3. 为什么 `user_profile` 和 `user_memory` 是可选的？什么情况下不需要？

---

> 下一篇：《Core 系列 17： Teams 多智能体团队 —— 协作完成任务》——深入解析多智能体团队的构建和工作方式