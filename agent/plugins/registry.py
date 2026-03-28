"""Plugin registry — D-118.

Discovers, loads, and registers plugins from agent/plugins/.
Plugins are enabled via config files in config/plugins/.
"""
import importlib
import json
import logging
from pathlib import Path
from typing import Callable

from plugins.manifest import PluginManifest, load_manifest
from plugins.executor import execute_handler

logger = logging.getLogger("mcc.plugins.registry")


class PluginRegistry:
    """Discovers and manages plugins per D-118 contract."""

    def __init__(self, plugins_dir: Path | None = None, config_dir: Path | None = None):
        self._plugins_dir = plugins_dir or Path(__file__).parent
        self._config_dir = config_dir or Path(__file__).resolve().parent.parent.parent / "config" / "plugins"
        self._loaded: dict[str, dict] = {}  # name -> {manifest, handlers, config}

    def discover(self) -> list[str]:
        """Discover available plugins (directories with manifest.json)."""
        plugins = []
        if not self._plugins_dir.is_dir():
            return plugins

        for child in sorted(self._plugins_dir.iterdir()):
            if child.is_dir() and (child / "manifest.json").exists():
                plugins.append(child.name)
        return plugins

    def load_all(self) -> int:
        """Load all enabled plugins. Returns count of loaded plugins."""
        loaded = 0
        for name in self.discover():
            if self._is_enabled(name):
                if self._load_plugin(name):
                    loaded += 1
        logger.info("Loaded %d plugins", loaded)
        return loaded

    def _is_enabled(self, name: str) -> bool:
        """Check if plugin has a config file and is not disabled."""
        config_path = self._config_dir / f"{name}.json"
        if not config_path.exists():
            return False
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            return config.get("enabled", True)
        except (json.JSONDecodeError, OSError):
            return False

    def _load_plugin(self, name: str) -> bool:
        """Load a single plugin: validate manifest, import handler module."""
        plugin_dir = self._plugins_dir / name
        manifest = load_manifest(plugin_dir / "manifest.json")
        if manifest is None:
            logger.warning("Plugin %s: invalid manifest, skipping", name)
            return False

        # Load config
        config_path = self._config_dir / f"{name}.json"
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            config = {}

        # Import handler module
        try:
            module = importlib.import_module(f"plugins.{name}.handler")
        except (ImportError, ModuleNotFoundError) as e:
            logger.error("Plugin %s: cannot import handler module: %s", name, e)
            return False

        # Resolve handler functions
        handlers = {}
        for spec in manifest.handlers:
            func = getattr(module, spec.handler, None)
            if func is None:
                logger.warning("Plugin %s: handler %s not found in module", name, spec.handler)
                continue
            handlers[spec.event_type] = {
                "func": func,
                "priority": spec.priority,
            }

        # Init plugin if init() exists
        init_func = getattr(module, "init", None)
        if init_func:
            try:
                init_func(config)
            except Exception as e:
                logger.error("Plugin %s: init failed: %s", name, e)
                return False

        self._loaded[name] = {
            "manifest": manifest,
            "handlers": handlers,
            "config": config,
            "module": module,
        }
        logger.info("Plugin %s v%s loaded (%d handlers)", name, manifest.version, len(handlers))
        return True

    def register_on_bus(self, bus) -> int:
        """Register all loaded plugin handlers on an EventBus. Returns count."""
        count = 0
        for name, plugin in self._loaded.items():
            for event_type, handler_info in plugin["handlers"].items():
                func = handler_info["func"]
                priority = handler_info["priority"]

                # Wrap handler with executor for timeout/error isolation
                def _make_wrapper(f, pname):
                    def wrapper(event):
                        from events.bus import HandlerResult
                        result = execute_handler(f, event.data, pname)
                        return HandlerResult.proceed(**(result or {}))
                    return wrapper

                bus.on(
                    event_type,
                    _make_wrapper(func, name),
                    priority=priority,
                    name=f"plugin:{name}:{event_type}",
                )
                count += 1
        logger.info("Registered %d plugin handlers on EventBus", count)
        return count

    @property
    def loaded_plugins(self) -> list[str]:
        return list(self._loaded.keys())
