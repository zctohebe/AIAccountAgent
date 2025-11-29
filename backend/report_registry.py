import importlib
import pkgutil
from typing import Callable, Dict, Any

_HANDLER_NAME = "process"

class ReportRegistry:
    def __init__(self):
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def discover(self):
        import backend.reports as reports_pkg
        for _, name, ispkg in pkgutil.iter_modules(reports_pkg.__path__):
            if ispkg:
                continue
            module = importlib.import_module(f"backend.reports.{name}")
            if hasattr(module, _HANDLER_NAME):
                handler = getattr(module, _HANDLER_NAME)
                if callable(handler):
                    # convention: module exposes REPORT_TYPE or infer from module name
                    report_type = getattr(module, "REPORT_TYPE", name)
                    self._handlers[report_type] = handler

    def register(self, report_type: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        self._handlers[report_type] = handler

    def get(self, report_type: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        return self._handlers.get(report_type)

    def list(self) -> Dict[str, str]:
        return {k: v.__module__ for k, v in self._handlers.items()}
