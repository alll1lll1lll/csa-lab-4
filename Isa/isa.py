import struct
from enum import Enum
from typing import Dict, List, Tuple

REGISTERS: Dict[str, int] = {
    # x-notation
    "x0": 0,
    "x1": 1,
    "x2": 2,
    "x3": 3,
    "x4": 4,
    "x5": 5,
    "x6": 6,
    "x7": 7,
    "x8": 8,
    "x9": 9,
    "x10": 10,
    "x11": 11,
    "x12": 12,
    "x13": 13,
    "x14": 14,
    "x15": 15,
    "x16": 16,
    "x17": 17,
    "x18": 18,
    "x19": 19,
    "x20": 20,
    "x21": 21,
    "x22": 22,
    "x23": 23,
    "x24": 24,
    "x25": 25,
    "x26": 26,
    "x27": 27,
    "x28": 28,
    "x29": 29,
    "x30": 30,
    "x31": 31,
    # ABI aliases
    "zero": 0,
    "ra": 1,
    "sp": 2,
    "gp": 3,
    "tp": 4,
    "t0": 5,
    "t1": 6,
    "t2": 7,
    "s0": 8,
    "fp": 8,
    "s1": 9,
    "a0": 10,
    "a1": 11,
    "a2": 12,
    "a3": 13,
    "a4": 14,
    "a5": 15,
    "a6": 16,
    "a7": 17,
    "s2": 18,
    "s3": 19,
    "s4": 20,
    "s5": 21,
    "s6": 22,
    "s7": 23,
    "s8": 24,
    "s9": 25,
    "s10": 26,
    "s11": 27,
    "t3": 28,
    "t4": 29,
    "t5": 30,
    "t6": 31,
}


class Opcode(int, Enum):
    OP_R = 0x00
    OP_I_ALU = 0x01
    OP_I_LOAD = 0x02
    OP_S_STORE = 0x03
    OP_B_BRANCH = 0x04
    OP_U_LUI = 0x05
    OP_J_JAL = 0x06
    OP_I_JALR = 0x07
    OP_SYS = 0x08


class InstructionEncoder:
    @staticmethod
    def encode_r(opcode: int, rd: int, rs1: int, rs2: int, funct3: int, funct7: int) -> int:
        return (
            ((opcode & 0x3F) << 26)
            | ((rd & 0x1F) << 21)
            | ((rs1 & 0x1F) << 16)
            | ((rs2 & 0x1F) << 11)
            | ((funct3 & 0x7) << 8)
            | (funct7 & 0xFF)
        )

    @staticmethod
    def encode_i(opcode: int, rd: int, rs1: int, imm: int, funct3: int) -> int:
        return (
            ((opcode & 0x3F) << 26)
            | ((rd & 0x1F) << 21)
            | ((rs1 & 0x1F) << 16)
            | ((funct3 & 0x7) << 13)
            | (imm & 0x1FFF)
        )

    @staticmethod
    def encode_s(opcode: int, rs1: int, rs2: int, imm: int, funct3: int) -> int:
        imm = imm & 0x1FFF
        return (
            ((opcode & 0x3F) << 26)
            | (((imm >> 9) & 0xF) << 22)
            | ((rs1 & 0x1F) << 17)
            | ((rs2 & 0x1F) << 12)
            | ((funct3 & 0x7) << 9)
            | (imm & 0x1FF)
        )

    @staticmethod
    def encode_u(opcode: int, rd: int, imm: int) -> int:
        return ((opcode & 0x3F) << 26) | ((rd & 0x1F) << 21) | (imm & 0x1FFFFF)


class BinaryManager:
    MAGIC: int = 0xDEADBEEF

    @staticmethod
    def write_binary(
        filename: str, text_section: List[Tuple[int, int, str]], data_section: List[Tuple[int, int, str]]
    ) -> None:
        with open(filename, "wb") as f:
            f.write(struct.pack(">I", BinaryManager.MAGIC))
            f.write(struct.pack(">I", 0x0000))
            f.write(struct.pack(">I", len(text_section)))
            for _, word, _ in text_section:
                f.write(struct.pack(">i", word))
            f.write(struct.pack(">I", 0x10000))
            f.write(struct.pack(">I", len(data_section)))
            for _, word, _ in data_section:
                f.write(struct.pack(">i", word))

    @staticmethod
    def write_debug(
        filename: str, text_section: List[Tuple[int, int, str]], data_section: List[Tuple[int, int, str]]
    ) -> None:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("ADDRESS  - HEXCODE  - MNEMONIC\n")
            f.write("-" * 32 + "\n")
            for addr, word, text in text_section:
                f.write(f"{addr:08X} - {word & 0xFFFFFFFF:08X} - {text}\n")
            f.write("\nDATA SECTION\n")
            for addr, word, text in data_section:
                f.write(f"{addr:08X} - {word & 0xFFFFFFFF:08X} - {text}\n")
