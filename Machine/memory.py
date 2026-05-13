import logging
from typing import Dict, List, Optional

MMIO_BASE = 0x000FF000
MMIO_IN_STATUS = MMIO_BASE + 0x00
MMIO_IN_DATA = MMIO_BASE + 0x04
MMIO_OUT_DATA = MMIO_BASE + 0x08
MMIO_OUT_STATUS = MMIO_BASE + 0x0C
MMIO_IRQ_ACK = MMIO_BASE + 0x10


class Memory:
    def __init__(self) -> None:
        self.memory: Dict[int, int] = {}
        self.output_buffer: List[str] = []
        self.input_char: Optional[int] = None
        self.eof: bool = False

    def read(self, address: int) -> int:
        if address % 4 != 0:
            raise ValueError(f"Unaligned memory read at 0x{address:08X}")
        if address == MMIO_IN_STATUS:
            return 1 if self.input_char is not None else 0
        if address == MMIO_IN_DATA:
            if self.input_char is not None:
                return self.input_char
            self.eof = True
            return 0
        if address == MMIO_OUT_STATUS:
            return 1
        return self.memory.get(address, 0)

    def write(self, address: int, value: int) -> None:
        if address % 4 != 0:
            raise ValueError(f"Unaligned memory write at 0x{address:08X}")
        if address == MMIO_OUT_DATA:
            char = chr(value & 0xFF)
            self.output_buffer.append(char)
            logging.info(f"OUTPUT: '{char}'")
            return
        if address == MMIO_IRQ_ACK:
            if value != 0:
                self.input_char = None
            return
        self.memory[address] = value & 0xFFFFFFFF
