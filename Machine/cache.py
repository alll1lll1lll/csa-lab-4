import logging
from typing import Any, Dict, List, Tuple

HIT_TICKS = 1
MISS_TICKS = 10
MMIO_BASE = 0x000FF000


class Cache:
    def __init__(self, size: int = 16) -> None:
        self.size: int = size
        self.lines: List[Dict[str, Any]] = [{"valid": False, "tag": -1, "data": 0} for _ in range(size)]
        self.hits: int = 0
        self.misses: int = 0

    def _idx(self, address: int) -> int:
        return (address >> 2) % self.size

    def _tag(self, address: int) -> int:
        return (address >> 2) // self.size

    def read(self, address: int, memory: Any) -> Tuple[int, int]:
        if address >= MMIO_BASE:
            return int(memory.read(address)), HIT_TICKS

        idx = self._idx(address)
        tag = self._tag(address)
        line = self.lines[idx]

        if line["valid"] and line["tag"] == tag:
            self.hits += 1
            logging.info(f"CACHE HIT  0x{address:08X}")
            return int(line["data"]), HIT_TICKS

        self.misses += 1
        data = memory.read(address)
        self.lines[idx] = {"valid": True, "tag": tag, "data": data}
        logging.info(f"CACHE MISS 0x{address:08X}")
        return int(data), MISS_TICKS

    def write(self, address: int, value: int, memory: Any) -> int:
        if address >= MMIO_BASE:
            memory.write(address, value)
            return HIT_TICKS

        idx = self._idx(address)
        tag = self._tag(address)
        line = self.lines[idx]

        if line["valid"] and line["tag"] == tag:
            line["data"] = value & 0xFFFFFFFF
            self.hits += 1
            memory.write(address, value)
            return HIT_TICKS

        self.misses += 1
        memory.write(address, value)
        return MISS_TICKS

    def invalidate(self) -> None:
        for line in self.lines:
            line["valid"] = False
        self.hits = self.misses = 0

    def stats(self) -> str:
        total = self.hits + self.misses
        ratio = self.hits / total * 100 if total else 0
        return f"Cache stats: {self.hits} hits, {self.misses} misses, {total} total, hit rate {ratio:.1f}%"
