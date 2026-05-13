import json
import logging
import os
import struct
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Isa.isa import REGISTERS, BinaryManager
from Machine.controlunit import ControlUnit
from Machine.datapath import DataPath
from Machine.memory import Memory

logging.basicConfig(level=logging.INFO, format="%(message)s")


def load_binary(filename, memory):
    with open(filename, "rb") as f:
        magic = struct.unpack(">I", f.read(4))[0]
        if magic != BinaryManager.MAGIC:
            raise ValueError("Invalid magic number in binary file!")

        text_base = struct.unpack(">I", f.read(4))[0]
        text_size = struct.unpack(">I", f.read(4))[0]
        for i in range(text_size):
            memory.write(text_base + i * 4, struct.unpack(">i", f.read(4))[0])

        data_base = struct.unpack(">I", f.read(4))[0]
        data_size = struct.unpack(">I", f.read(4))[0]
        for i in range(data_size):
            memory.write(data_base + i * 4, struct.unpack(">i", f.read(4))[0])


def main():
    if len(sys.argv) < 2:
        print("Usage: python machine.py <target.bin> [schedule.json]")
        sys.exit(1)

    bin_file = sys.argv[1]
    schedule_file = sys.argv[2] if len(sys.argv) > 2 else None

    schedule = []
    if schedule_file and os.path.exists(schedule_file):
        with open(schedule_file, "r") as f:
            schedule = json.load(f)

    mem = Memory()
    load_binary(bin_file, mem)
    dp = DataPath(mem)
    cu = ControlUnit(dp)

    dp.write_reg(REGISTERS["sp"], 0x000F0000)

    print("--- START SIMULATION ---")
    # if we want to stop at a target tick:
    # TARGET=N
    # while True:
    #     is_running = cu.step(schedule)
    #     if cu.ticks == TARGET:
    #         cu.print_state("Breakpoint hit")
    #         break
    #     if not is_running:
    #         break
    while True:
        is_running = cu.step(schedule)
        if not is_running:
            break
    print("--- END SIMULATION ---")
    print(f"Total ticks: {cu.ticks}")
    print(dp.cache.stats())

    output_str = "".join(mem.output_buffer)
    print(f"OUTPUT BUFFER:\n{output_str}")


if __name__ == "__main__":
    main()
