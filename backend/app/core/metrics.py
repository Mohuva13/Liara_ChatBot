import threading
from collections import defaultdict


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = (
            defaultdict(float)
        )

    def increment(self, name: str, value: float = 1, **labels: str) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self._counters[key] += value

    def render(self) -> str:
        with self._lock:
            values = sorted(self._counters.items())
        lines = ["# Liara Assistant bounded operational metrics"]
        described: set[str] = set()
        for (name, labels), value in values:
            if name not in described:
                lines.append(f"# TYPE {name} counter")
                described.add(name)
            label_text = ""
            if labels:
                serialized = ",".join(
                    f'{key}="{self._escape(item)}"' for key, item in labels
                )
                label_text = "{" + serialized + "}"
            lines.append(f"{name}{label_text} {value:g}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


metrics = MetricsRegistry()
