import re
from typing import Callable, Dict, List

from Isa.isa import REGISTERS, InstructionEncoder, Opcode

# R-type funct3 / funct7 tables
_R_F3: Dict[str, int] = {
    "add": 0,
    "sub": 1,
    "mul": 2,
    "mulh": 2,
    "div": 3,
    "rem": 3,
    "and": 4,
    "or": 5,
    "xor": 6,
    "sll": 7,
    "srl": 7,
    "sra": 7,
}
_R_F7: Dict[str, int] = {
    "add": 0,
    "sub": 0,
    "mul": 0,
    "mulh": 1,
    "div": 0,
    "rem": 1,
    "and": 0,
    "or": 0,
    "xor": 0,
    "sll": 1,
    "srl": 3,
    "sra": 4,
}

# I-type ALU funct3 table
_I_ALU_F3: Dict[str, int] = {
    "addi": 0,
    "slli": 1,
    "slti": 2,
    "srli": 3,
    "andi": 4,
    "ori": 5,
    "xori": 6,
    "srai": 7,
}

# Branch funct3 table
_B_F3: Dict[str, int] = {
    "beq": 0,
    "bne": 1,
    "blt": 2,
    "bge": 3,
    "ble": 4,
    "bgt": 5,
    "blo": 6,
    "bgeu": 7,
}


class CodeGenerator:
    @staticmethod
    def encode_instruction(
        mnemonic: str,
        args: List[str],
        pc: int,
        resolve_imm_func: Callable[[str, int, bool], int],
    ) -> int:
        try:
            if mnemonic in _R_F3:
                rd, rs1, rs2 = REGISTERS[args[0]], REGISTERS[args[1]], REGISTERS[args[2]]
                return int(InstructionEncoder.encode_r(Opcode.OP_R, rd, rs1, rs2, _R_F3[mnemonic], _R_F7[mnemonic]))

            elif mnemonic == "cmp":
                rs1, rs2 = REGISTERS[args[0]], REGISTERS[args[1]]
                return int(InstructionEncoder.encode_r(Opcode.OP_R, 0, rs1, rs2, 7, 0))

            elif mnemonic in _I_ALU_F3:
                rd, rs1 = REGISTERS[args[0]], REGISTERS[args[1]]
                # Передаем 3-й аргумент False (не относительный адрес)
                imm = resolve_imm_func(args[2], pc, False)
                return int(InstructionEncoder.encode_i(Opcode.OP_I_ALU, rd, rs1, imm, _I_ALU_F3[mnemonic]))

            elif mnemonic in ("lw", "lb", "sw", "sb"):
                reg = REGISTERS[args[0]]
                m = re.match(r"(-?\w+)\((\w+)\)", args[1])
                if not m:
                    raise ValueError(f"Bad memory addressing: {args[1]}")
                # Передаем 3-й аргумент False
                imm = resolve_imm_func(m.group(1), pc, False)
                base = REGISTERS[m.group(2)]

                if mnemonic in ("lw", "lb"):
                    f3 = 0 if mnemonic == "lw" else 1
                    return int(InstructionEncoder.encode_i(Opcode.OP_I_LOAD, reg, base, imm, f3))
                else:
                    f3 = 0 if mnemonic == "sw" else 1
                    return int(InstructionEncoder.encode_s(Opcode.OP_S_STORE, base, reg, imm, f3))

            elif mnemonic in _B_F3:
                rs1, rs2 = REGISTERS[args[0]], REGISTERS[args[1]]
                # Передаем True позиционно (без ключа is_relative)
                imm = resolve_imm_func(args[2], pc, True)
                return int(InstructionEncoder.encode_s(Opcode.OP_B_BRANCH, rs1, rs2, imm, _B_F3[mnemonic]))

            elif mnemonic == "jal":
                rd = REGISTERS[args[0]]
                imm = resolve_imm_func(args[1], pc, True)
                return int(InstructionEncoder.encode_u(Opcode.OP_J_JAL, rd, imm))

            elif mnemonic == "jalr":
                rd, rs1 = REGISTERS[args[0]], REGISTERS[args[1]]
                imm = resolve_imm_func(args[2], pc, False)
                return int(InstructionEncoder.encode_i(Opcode.OP_I_JALR, rd, rs1, imm, 0))

            elif mnemonic == "lui":
                rd = REGISTERS[args[0]]
                imm = resolve_imm_func(args[1], pc, False)
                return int(InstructionEncoder.encode_u(Opcode.OP_U_LUI, rd, imm))

            elif mnemonic in ("trap", "iret", "halt"):
                f3 = {"trap": 0, "iret": 1, "halt": 2}[mnemonic]
                return int(InstructionEncoder.encode_i(Opcode.OP_SYS, 0, 0, 0, f3))

            elif mnemonic == "mv":
                rd, rs1 = REGISTERS[args[0]], REGISTERS[args[1]]
                return int(InstructionEncoder.encode_i(Opcode.OP_I_ALU, rd, rs1, 0, 0))

            elif mnemonic == "j":
                imm = resolve_imm_func(args[0], pc, True)
                return int(InstructionEncoder.encode_u(Opcode.OP_J_JAL, 0, imm))

            elif mnemonic == "jr":
                rs = REGISTERS[args[0]]
                return int(InstructionEncoder.encode_i(Opcode.OP_I_JALR, 0, rs, 0, 0))

            elif mnemonic == "beqz":
                rs1 = REGISTERS[args[0]]
                imm = resolve_imm_func(args[1], pc, True)
                return int(InstructionEncoder.encode_s(Opcode.OP_B_BRANCH, rs1, 0, imm, 0))

            elif mnemonic == "bnez":
                rs1 = REGISTERS[args[0]]
                imm = resolve_imm_func(args[1], pc, True)
                return int(InstructionEncoder.encode_s(Opcode.OP_B_BRANCH, rs1, 0, imm, 1))

            elif mnemonic == "bgtu":
                rs1, rs2 = REGISTERS[args[0]], REGISTERS[args[1]]
                imm = resolve_imm_func(args[2], pc, True)
                return int(InstructionEncoder.encode_s(Opcode.OP_B_BRANCH, rs2, rs1, imm, 6))

            elif mnemonic == "bleu":
                rs1, rs2 = REGISTERS[args[0]], REGISTERS[args[1]]
                imm = resolve_imm_func(args[2], pc, True)
                return int(InstructionEncoder.encode_s(Opcode.OP_B_BRANCH, rs2, rs1, imm, 7))

            else:
                raise ValueError(f"Unknown instruction: {mnemonic}")

        except KeyError as e:
            raise ValueError(f"Unknown register: {e}")
