import struct
from enum import Enum

REGISTERS = {
    'r0': 0, 'zero': 0,
    'r1': 1, 't0': 1, 'r2': 2, 't1': 2, 'r3': 3, 't2': 3, 'r4': 4, 't3': 4, 'r5': 5, 't4': 5,
    'r6': 6, 'a0': 6, 'r7': 7, 'a1': 7, 'r8': 8, 'a2': 8, 'r9': 9, 'a3': 9,
    'r10': 10, 's0': 10, 'r11': 11, 's1': 11, 'r12': 12, 's2': 12, 'r13': 13, 's3': 13,
    'r14': 14, 'sp': 14,
    'r15': 15, 'ra': 15
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
    def encode_r(opcode, rd, rs1, rs2, funct3, funct7):
        return (opcode << 26) | ((rd & 0xF) << 22) | ((rs1 & 0xF) << 18) | ((rs2 & 0xF) << 14) | (
                    (funct3 & 0x7) << 11) | (funct7 & 0x7FF)

    @staticmethod
    def encode_i(opcode, rd, rs1, imm, funct3):
        return (opcode << 26) | ((rd & 0xF) << 22) | ((rs1 & 0xF) << 18) | ((funct3 & 0x7) << 15) | (imm & 0x7FFF)

    @staticmethod
    def encode_s(opcode, rs1, rs2, imm, funct3):
        imm14_11 = (imm >> 11) & 0xF
        imm10_0 = imm & 0x7FF
        return (opcode << 26) | (imm14_11 << 22) | ((rs1 & 0xF) << 18) | ((rs2 & 0xF) << 14) | (
                    (funct3 & 0x7) << 11) | imm10_0

    @staticmethod
    def encode_u(opcode, rd, imm):
        return (opcode << 26) | ((rd & 0xF) << 22) | (imm & 0x3FFFFF)


class BinaryManager:
    MAGIC = 0xDEADBEEF

    @staticmethod
    def write_binary(filename, text_section, data_section):
        with open(filename, 'wb') as f:
            f.write(struct.pack('>I', BinaryManager.MAGIC))

            f.write(struct.pack('>I', 0x0000))
            f.write(struct.pack('>I', len(text_section)))
            for _, word, _ in text_section:
                f.write(struct.pack('>i', word))

            f.write(struct.pack('>I', 0x10000))
            f.write(struct.pack('>I', len(data_section)))
            for _, word, _ in data_section:
                f.write(struct.pack('>i', word))

    @staticmethod
    def write_debug(filename, text_section, data_section):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("ADDRESS  - HEXCODE  - MNEMONIC\n")
            f.write("-" * 32 + "\n")
            for addr, word, text in text_section:
                f.write(f"{addr:08X} - {word & 0xFFFFFFFF:08X} - {text}\n")
            f.write("\nDATA SECTION\n")
            for addr, word, text in data_section:
                f.write(f"{addr:08X} - {word & 0xFFFFFFFF:08X} - {text}\n")
