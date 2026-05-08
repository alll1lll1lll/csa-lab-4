import logging

MMIO_BASE       = 0x000FF000
MMIO_IN_STATUS  = MMIO_BASE + 0x00
MMIO_IN_DATA    = MMIO_BASE + 0x04
MMIO_OUT_DATA   = MMIO_BASE + 0x08
MMIO_OUT_STATUS = MMIO_BASE + 0x0C
MMIO_IRQ_ACK    = MMIO_BASE + 0x10


class Memory:
    def __init__(self):
        self.memory = {}
        self.mmio_in_data = 0
        self.mmio_in_status = 0
        self.irq_pending = False
        self.output_buffer = []

    def read(self, address):
        if address % 4 != 0:
            raise ValueError(f"Unaligned memory read at 0x{address:08X}")
        if address == MMIO_IN_STATUS:
            return self.mmio_in_status
        if address == MMIO_IN_DATA:
            return self.mmio_in_data
        if address == MMIO_OUT_STATUS:
            return 1
        return self.memory.get(address, 0)

    def write(self, address, value):
        if address % 4 != 0:
            raise ValueError(f"Unaligned memory write at 0x{address:08X}")
        if address == MMIO_OUT_DATA:
            char = chr(value & 0xFF)
            self.output_buffer.append(char)
            logging.info(f"OUTPUT: '{char}'")
            return
        if address == MMIO_IRQ_ACK:
            if value != 0:
                self.irq_pending = False
                self.mmio_in_status = 0
            return
        self.memory[address] = value & 0xFFFFFFFF
