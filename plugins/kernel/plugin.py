from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core.plugin_manifest import get_hive_metadata


class Plugin:
    def __init__(self, hub: Any = None, manifest: Dict[str, Any] | None = None):
        self.hub = hub
        self.manifest = manifest or {}
        hive_meta = get_hive_metadata(self.manifest)
        self.hive = str(hive_meta.get("hive") or "guild").lower()
        self.name = f"{self.hive}.kernel"

    def commands(self) -> Dict[str, Any]:
        return {
            f"{self.hive}.hive.status": self.hive_status,
            f"{self.hive}.hive.plugins": self.hive_plugins,
            f"{self.hive}.hive.io": self.hive_io,
        }

    def hive_status(self) -> Dict[str, Any]:
        status = self._guild_runtime_status()
        return {
            "ok": True,
            "hive": self.hive,
            "runtime": status,
            "plugin_count": len(self._collect_plugins()),
        }

    def hive_plugins(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "hive": self.hive,
            "plugins": self._collect_plugins(),
        }

    def hive_io(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "hive": self.hive,
            "communication": self._communication_config(),
        }

    def _collect_plugins(self) -> List[str]:
        if not self.hub or not hasattr(self.hub, "hives"):
            return []
        grouped = self.hub.hives
        metas = grouped.get(self.hive, [])
        return sorted([meta.name for meta in metas])

    def _guild_runtime_status(self) -> Dict[str, Any]:
        if not self.hub or not hasattr(self.hub, "module_registry"):
            return {}
        runtime = self.hub.module_registry.hives.get(self.hive)
        if runtime is None:
            return {"running": False}
        try:
            status = runtime.status()
            status["running"] = True
            return status
        except Exception:
            return {"running": True}

    def _communication_config(self) -> Dict[str, Any]:
        candidates = [
            Path.cwd() / "guild" / "aas-hive.json",
            Path.cwd() / "aas-hive.json",
        ]
        for path in candidates:
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                communication = payload.get("communication", {})
                if isinstance(communication, dict):
                    return communication
            except Exception:
                continue
        return {}
