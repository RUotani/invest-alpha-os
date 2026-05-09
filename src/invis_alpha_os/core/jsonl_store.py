from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Generic, Iterable, TypeVar

from .serialization import to_jsonable

T = TypeVar("T")


@dataclass(frozen=True)
class JsonlStore(Generic[T]):
    path: Path
    encode: Callable[[T], dict[str, Any]]
    decode: Callable[[dict[str, Any]], T]

    def append(self, item: T) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(to_jsonable(self.encode(item)), ensure_ascii=False) + "\n")

    def iter_all(self) -> Iterable[T]:
        if not self.path.exists():
            return []
        items: list[T] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                items.append(self.decode(json.loads(line)))
        return items

