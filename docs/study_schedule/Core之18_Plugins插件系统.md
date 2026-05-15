# Core 系列 18： Plugins 插件系统 —— 可扩展架构

> 目标：小朋友也能看懂！用一个"手机App商店"的比喻来讲清楚，agnoclaw 的插件系统是如何工作的，如何让用户自己扩展功能。

---

## 一、"手机App商店"比喻

想象你的手机系统：
- 手机自带了一些基本功能（打电话、发短信）
- 但你想**加功能**，去 App 商店下载 App
- 每个 App 都有自己的功能，可以独立安装/卸载

agnoclaw 的**插件系统**就是这样的"App 商店"：
- agnoclaw 自带一些基本工具（bash、files、web）
- 但你可以**安装插件**来扩展功能
- 每个插件都是独立的模块，可以添加工具、技能目录、钩子等

---

## 二、插件的发现方式

文件：`src/agnoclaw/plugins.py`

### 2.1 方式1：Python Entry Points（推荐）

通过 `pyproject.toml` 注册插件：

```toml
# pyproject.toml
[project.entry-points."agnoclaw.plugins"]
my-plugin = "my_package.plugin"
```

这意味着：
- 当用户 `pip install my-package` 时
- agnoclaw 自动发现这个插件
- 不需要额外配置

### 2.2 方式2：显式模块路径

```python
from agnoclaw.plugins import PluginLoader

loader = PluginLoader()
manifest = loader.load_from_path("my_package.plugin")  # 显式加载
```

用于本地开发或测试。

---

## 三、PluginManifest —— 插件清单

每个插件必须提供一个函数 `agnoclaw_plugin()`，返回 `PluginManifest`：

```python
@dataclass
class PluginManifest:
    name: str                    # 插件名字
    version: str = "0.0.0"       # 版本
    description: str = ""         # 描述

    # 工具（Toolkit 实例列表）
    tools: list[Any] = field(default_factory=list)

    # 技能目录
    skills_dirs: list[str] = field(default_factory=list)

    # 钩子函数
    pre_run_hooks: list[Callable] = field(default_factory=list)
    post_run_hooks: list[Callable] = field(default_factory=list)

    # 配置覆盖
    config_overrides: dict[str, Any] = field(default_factory=list)
```

---

## 四、插件示例

### 4.1 一个简单的工具插件

```python
# my_package/plugin.py
from agnoclaw.plugins import PluginManifest
from agnoclaw.tools import ToolKit

class MyToolkit(Toolkit):
    def __init__(self):
        super().__init__(name="my_tools")
        self.register(self.my_tool)

    @tool(name="my_tool", description="A custom tool")
    def my_tool(self, input: str) -> str:
        return f"Processed: {input}"

def agnoclaw_plugin() -> PluginManifest:
    return PluginManifest(
        name="my-plugin",
        version="1.0.0",
        description="My custom plugin",
        tools=[MyToolkit()],
    )
```

### 4.2 一个带技能目录的插件

```python
def agnoclaw_plugin() -> PluginManifest:
    return PluginManifest(
        name="research-tools",
        version="1.0.0",
        description="Research capabilities",
        skills_dirs=["path/to/skills"],
    )
```

### 4.3 一个带钩子的插件

```python
def agnoclaw_plugin() -> PluginManifest:
    from my_package.hooks import my_pre_hook, my_post_hook

    return PluginManifest(
        name="logging-plugin",
        version="1.0.0",
        pre_run_hooks=[my_pre_hook],
        post_run_hooks=[my_post_hook],
    )
```

---

## 五、PluginLoader —— 插件加载器

```python
class PluginLoader:
    """发现和加载 agnoclaw 插件"""

    ENTRY_POINT_GROUP = "agnoclaw.plugins"
    PLUGIN_FUNC_NAME = "agnoclaw_plugin"

    def discover(self) -> list[PluginManifest]:
        """通过 entry points 发现所有插件"""
        manifests = []

        try:
            from importlib.metadata import entry_points
        except ImportError:
            return manifests

        eps = entry_points()
        if hasattr(eps, "select"):
            plugin_eps = eps.select(group=self.ENTRY_POINT_GROUP)
        else:
            plugin_eps = eps.get(self.ENTRY_POINT_GROUP, [])

        for ep in plugin_eps:
            try:
                module = ep.load()
                manifest = self._extract_manifest(module, ep.name)
                if manifest:
                    manifests.append(manifest)
                    self._loaded[manifest.name] = manifest
            except Exception as e:
                logger.warning("Failed to load plugin '%s': %s", ep.name, e)

        return manifests

    def load_from_path(self, module_path: str) -> Optional[PluginManifest]:
        """从显式模块路径加载插件"""
        try:
            module = importlib.import_module(module_path)
            manifest = self._extract_manifest(module, module_path)
            if manifest:
                self._loaded[manifest.name] = manifest
            return manifest
        except Exception as e:
            logger.warning("Failed to load plugin from '%s': %s", module_path, e)
            return None

    def _extract_manifest(self, module, source_name: str) -> Optional[PluginManifest]:
        """从模块中提取 PluginManifest"""
        func = getattr(module, self.PLUGIN_FUNC_NAME, None)
        if func is None:
            logger.warning("Plugin '%s' has no %s() function", source_name, self.PLUGIN_FUNC_NAME)
            return None

        if not callable(func):
            logger.warning("Plugin '%s': %s is not callable", source_name, self.PLUGIN_FUNC_NAME)
            return None

        try:
            manifest = func()
        except Exception as e:
            logger.warning("Plugin '%s': %s() raised: %s", source_name, self.PLUGIN_FUNC_NAME, e)
            return None

        if not isinstance(manifest, PluginManifest):
            logger.warning(...)
            return None

        return manifest
```

---

## 六、收集插件内容

```python
def get_all_tools(self) -> list:
    """收集所有插件的工具"""
    tools = []
    for manifest in self._loaded.values():
        tools.extend(manifest.tools)
    return tools

def get_all_skills_dirs(self) -> list[str]:
    """收集所有插件的技能目录"""
    dirs = []
    for manifest in self._loaded.values():
        dirs.extend(manifest.skills_dirs)
    return dirs

def get_all_pre_run_hooks(self) -> list[Callable]:
    """收集所有插件的前置钩子"""
    hooks = []
    for manifest in self._loaded.values():
        hooks.extend(manifest.pre_run_hooks)
    return hooks

def get_all_post_run_hooks(self) -> list[Callable]:
    """收集所有插件的后置钩子"""
    hooks = []
    for manifest in self._loaded.values():
        hooks.extend(manifest.post_run_hooks)
    return hooks
```

---

## 七、在 AgentHarness 中的集成

```python
# agent.py 中
if self.config.enable_plugins:
    loader = PluginLoader()
    manifests = loader.discover()

    # 收集所有插件的工具
    all_tools = list(self._tools or [])
    for manifest in manifests:
        all_tools.extend(manifest.tools)

    # 收集所有插件的技能目录
    for manifest in manifests:
        for skill_dir in manifest.skills_dirs:
            self.skills.add_dir(skill_dir)

    # 收集所有插件的钩子
    for manifest in manifests:
        self._pre_run_hooks.extend(manifest.pre_run_hooks)
        self._post_run_hooks.extend(manifest.post_run_hooks)
```

---

## 八、思考题

1. 为什么插件需要返回一个 `PluginManifest` 而不是直接注册工具？
2. 如果两个插件都提供了同名的工具，会发生什么？
3. 插件的 `config_overrides` 有什么作用？

---

> 下一篇：《Core 系列 19： Skills Hub & Backends —— 技能生态》——深入解析 ClawHub 客户端和技能运行时后端