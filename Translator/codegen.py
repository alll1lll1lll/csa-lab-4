import re

from Isa.isa import REGISTERS, InstructionEncoder, Opcode


class CodeGenerator:

    @staticmethod
    def encode_instruction(mnemonic: str, args: list, pc: int, resolve_imm_func) -> int:
        try:
            if mnemonic in ['add', 'sub', 'mul', 'div', 'and', 'or', 'xor', 'cmp', 'sll', 'sla', 'srl', 'sra']:
                rd, rs1, rs2 = REGISTERS[args[0]], REGISTERS[args[1]], REGISTERS[args[2]]
                f3_map = {
                    'add': 0, 'sub': 1, 'mul': 2, 'div': 3,
                    'and': 4, 'or': 5,  'xor': 6,
                    'cmp': 7, 'sll': 7, 'sla': 7, 'srl': 7, 'sra': 7,
                }
                f7_map = {
                    'add': 0, 'sub': 0, 'mul': 0, 'div': 0,
                    'and': 0, 'or': 0,  'xor': 0,
                    'cmp': 0, 'sll': 1, 'sla': 2, 'srl': 3, 'sra': 4,
                }
                return InstructionEncoder.encode_r(Opcode.OP_R, rd, rs1, rs2, f3_map[mnemonic], f7_map[mnemonic])

            elif mnemonic in ['addi', 'andi', 'ori']:
                rd, rs1 = REGISTERS[args[0]], REGISTERS[args[1]]
                imm = resolve_imm_func(args[2], pc)
                f3_map = {'addi': 0, 'andi': 4, 'ori': 5}
                return InstructionEncoder.encode_i(Opcode.OP_I_ALU, rd, rs1, imm, f3_map[mnemonic])

            elif mnemonic in ['lw', 'lb', 'sw', 'sb']:
                reg = REGISTERS[args[0]]
                match = re.match(r'(-?\w+)\(([a-zA-Z0-9]+)\)', args[1])
                if not match:
                    raise ValueError(f"Invalid memory addressing format: {args[1]}")

                imm = resolve_imm_func(match.group(1), pc)
                base_reg = REGISTERS[match.group(2)]

                if mnemonic in ['lw', 'lb']:
                    funct3 = 0 if mnemonic == 'lw' else 1
                    return InstructionEncoder.encode_i(Opcode.OP_I_LOAD, reg, base_reg, imm, funct3)
                else:
                    funct3 = 0 if mnemonic == 'sw' else 1
                    return InstructionEncoder.encode_s(Opcode.OP_S_STORE, base_reg, reg, imm, funct3)

            elif mnemonic in ['beq', 'bne', 'blt', 'bge', 'ble', 'bgt', 'blo', 'bgeu']:
                rs1, rs2 = REGISTERS[args[0]], REGISTERS[args[1]]
                imm = resolve_imm_func(args[2], pc, is_relative=True)
                f3_map = {'beq': 0, 'bne': 1, 'blt': 2, 'bge': 3, 'ble': 4, 'bgt': 5, 'blo': 6, 'bgeu': 7}
                return InstructionEncoder.encode_s(Opcode.OP_B_BRANCH, rs1, rs2, imm, f3_map[mnemonic])

            elif mnemonic == 'jal':
                imm = resolve_imm_func(args[1], pc, is_relative=True)
                return InstructionEncoder.encode_u(Opcode.OP_J_JAL, REGISTERS[args[0]], imm)

            elif mnemonic == 'jalr':
                imm = resolve_imm_func(args[2], pc)
                return InstructionEncoder.encode_i(Opcode.OP_I_JALR, REGISTERS[args[0]], REGISTERS[args[1]], imm, 0)

            elif mnemonic in ['trap', 'iret', 'halt']:
                f3_map = {'trap': 0, 'iret': 1, 'halt': 2}
                return InstructionEncoder.encode_i(Opcode.OP_SYS, 0, 0, 0, f3_map[mnemonic])

            elif mnemonic == 'lui':
                imm = resolve_imm_func(args[1], pc)
                return InstructionEncoder.encode_u(Opcode.OP_U_LUI, REGISTERS[args[0]], imm)
            else:
                raise ValueError(f"Unknown instruction: {mnemonic}")

        except KeyError as e:
            raise ValueError(f"Unknown register: {e}")
