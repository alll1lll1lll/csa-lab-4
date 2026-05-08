import logging

from Isa.isa import REGISTERS, Opcode


class ControlUnit:
    def __init__(self, datapath):
        self.dp = datapath
        self.ticks = 0
        self.halted = False

    def tick(self):
        self.ticks += 1

    def decode_r_type(self, instruction):
        opcode = (instruction >> 26) & 0x3F
        rd = (instruction >> 22) & 0xF
        rs1 = (instruction >> 18) & 0xF
        rs2 = (instruction >> 14) & 0xF
        funct3 = (instruction >> 11) & 0x7
        return opcode, rd, rs1, rs2, funct3

    def decode_i_type(self, instruction):
        opcode = (instruction >> 26) & 0x3F
        rd = (instruction >> 22) & 0xF
        rs1 = (instruction >> 18) & 0xF
        funct3 = (instruction >> 15) & 0x7
        imm = instruction & 0x7FFF
        if imm & 0x4000:
            imm -= 0x8000
        return opcode, rd, rs1, funct3, imm

    def decode_s_type(self, instruction):
        opcode = (instruction >> 26) & 0x3F
        imm_high = (instruction >> 22) & 0xF
        rs1 = (instruction >> 18) & 0xF
        rs2 = (instruction >> 14) & 0xF
        funct3 = (instruction >> 11) & 0x7
        imm_low = instruction & 0x7FF
        imm = (imm_high << 11) | imm_low
        if imm & 0x4000:
            imm -= 0x8000
        return opcode, rs1, rs2, funct3, imm

    def decode_u_type(self, instruction):
        opcode = (instruction >> 26) & 0x3F
        rd = (instruction >> 22) & 0xF
        imm = instruction & 0x3FFFFF
        if imm & 0x200000:
            imm -= 0x400000
        return opcode, rd, imm

    def print_state(self, mnemonic):
        ie = int(self.dp.ps_ie)
        logging.info(f"Tick: {self.ticks:04d} | PC: 0x{self.dp.pc:08X} | {mnemonic:20} | "
                     f"t0: {self.dp.regs[REGISTERS['t0']]}, t1: {self.dp.regs[REGISTERS['t1']]}, "
                     f"sp: 0x{self.dp.regs[REGISTERS['sp']]:X} | "
                     f"N:{self.dp.ps_flags['N']} Z:{self.dp.ps_flags['Z']} V:{self.dp.ps_flags['V']} C:{self.dp.ps_flags['C']} IE:{ie}")

    def run(self, schedule=None):
        if schedule is None:
            schedule = []

        schedule_idx = 0

        while not self.halted:
            # deliver input at the scheduled tick regardless of port state — no magic queues
            if schedule_idx < len(schedule):
                sched_tick, char = schedule[schedule_idx]
                if self.ticks >= sched_tick:
                    self.dp.memory.mmio_in_data = ord(char)
                    self.dp.memory.mmio_in_status = 1
                    self.dp.memory.irq_pending = True
                    schedule_idx += 1

            if self.dp.memory.irq_pending and self.dp.ps_ie:
                self.dp.epc = self.dp.pc
                self.dp.ps_ie = False
                self.dp.pc = self.dp.memory.read(0x00000008)
                self.tick()
                self.tick()
                self.print_state("--- HARDWARE TRAP ---")
                continue

            current_pc = self.dp.pc
            instruction = self.dp.memory.read(current_pc)
            self.dp.pc += 4
            self.tick()

            opcode = (instruction >> 26) & 0x3F

            if opcode == Opcode.OP_R:
                _, rd, rs1, rs2, funct3 = self.decode_r_type(instruction)
                funct7 = instruction & 0x7FF
                val1, val2 = self.dp.read_reg(rs1), self.dp.read_reg(rs2)

                if funct3 < 7:
                    alu_op, is_cmp = funct3, False
                else:
                    _f7_to_op = {0: 7, 1: 8, 2: 8, 3: 9, 4: 10}
                    alu_op = _f7_to_op.get(funct7, 7)
                    is_cmp = (funct7 == 0)

                result, calculated_flags = self.dp.alu(alu_op, val1, val2)
                self.tick()

                if not is_cmp:
                    self.dp.write_reg(rd, result)

                self.dp.ps_flags.update(calculated_flags)
                self.tick()
                self.print_state(f"alu r{rd}, r{rs1}, r{rs2}")

            elif opcode == Opcode.OP_I_ALU:
                _, rd, rs1, funct3, imm = self.decode_i_type(instruction)
                val1 = self.dp.read_reg(rs1)

                result, calculated_flags = self.dp.alu(funct3, val1, imm)
                self.tick()

                self.dp.write_reg(rd, result)
                self.dp.ps_flags.update(calculated_flags)
                self.tick()
                self.print_state(f"alu_i r{rd}, r{rs1}, {imm}")

            elif opcode == Opcode.OP_I_LOAD:
                _, rd, rs1, funct3, imm = self.decode_i_type(instruction)
                val1 = self.dp.read_reg(rs1)
                address = val1 + imm
                self.tick()

                data = self.dp.memory.read(address)
                if funct3 == 1:  # lb — sign-extend byte
                    data = data & 0xFF
                    if data & 0x80:
                        data -= 0x100
                self.tick()

                self.dp.write_reg(rd, data)
                self.tick()
                self.print_state(f"load r{rd}, {imm}(r{rs1})")

            elif opcode == Opcode.OP_S_STORE:
                _, rs1, rs2, funct3, imm = self.decode_s_type(instruction)
                val1, val2 = self.dp.read_reg(rs1), self.dp.read_reg(rs2)
                address = val1 + imm
                self.tick()

                if funct3 == 1:  # sb — write only the low byte, preserve the rest of the word
                    aligned_address = address & ~3
                    byte_offset = address % 4
                    word_in_mem = self.dp.memory.read(aligned_address)
                    mask_clear = ~(0xFF << (byte_offset * 8))
                    word_in_mem = (word_in_mem & mask_clear) | ((val2 & 0xFF) << (byte_offset * 8))
                    self.dp.memory.write(aligned_address, word_in_mem)
                else:
                    self.dp.memory.write(address, val2)
                self.tick()
                self.print_state(f"store r{rs2}, {imm}(r{rs1})")

            elif opcode == Opcode.OP_B_BRANCH:
                _, rs1, rs2, funct3, imm = self.decode_s_type(instruction)
                _, calculated_flags = self.dp.alu(1, self.dp.read_reg(rs1), self.dp.read_reg(rs2))
                self.dp.ps_flags.update(calculated_flags)
                self.tick()

                take_branch = False
                if funct3 == 0 and self.dp.ps_flags['Z'] == 1:
                    take_branch = True
                elif funct3 == 1 and self.dp.ps_flags['Z'] == 0:
                    take_branch = True
                elif funct3 == 2:
                    take_branch = (self.dp.ps_flags['N'] ^ self.dp.ps_flags['V']) == 1
                elif funct3 == 3:
                    take_branch = (self.dp.ps_flags['N'] ^ self.dp.ps_flags['V']) == 0
                elif funct3 == 4:
                    take_branch = (self.dp.ps_flags['Z'] == 1) or \
                                  ((self.dp.ps_flags['N'] ^ self.dp.ps_flags['V']) == 1)
                elif funct3 == 5:
                    take_branch = (self.dp.ps_flags['Z'] == 0) and \
                                  ((self.dp.ps_flags['N'] ^ self.dp.ps_flags['V']) == 0)
                elif funct3 == 6:
                    take_branch = self.dp.ps_flags['C'] == 1
                elif funct3 == 7:
                    take_branch = self.dp.ps_flags['C'] == 0

                if take_branch:
                    self.dp.pc = current_pc + imm
                self.tick()
                self.print_state(f"branch r{rs1}, r{rs2}, {imm}")

            elif opcode == Opcode.OP_U_LUI:
                _, rd, imm = self.decode_u_type(instruction)
                self.dp.write_reg(rd, imm << 12)
                self.tick()
                self.print_state(f"lui r{rd}, {imm}")

            elif opcode == Opcode.OP_J_JAL:
                _, rd, imm = self.decode_u_type(instruction)
                self.dp.write_reg(rd, self.dp.pc)
                self.dp.pc = current_pc + imm
                self.tick()
                self.print_state(f"jal r{rd}, {imm}")

            elif opcode == Opcode.OP_I_JALR:
                _, rd, rs1, _, imm = self.decode_i_type(instruction)
                val1 = self.dp.read_reg(rs1)
                self.dp.write_reg(rd, self.dp.pc)
                self.dp.pc = val1 + imm
                self.tick()
                self.print_state(f"jalr r{rd}, r{rs1}, {imm}")

            elif opcode == Opcode.OP_SYS:
                _, _, _, funct3, _ = self.decode_i_type(instruction)
                self.tick()
                if funct3 == 0:  # trap
                    self.dp.epc = self.dp.pc
                    self.dp.ps_ie = False
                    self.dp.pc = self.dp.memory.read(0x00000004)
                    self.print_state("trap")
                elif funct3 == 1:  # iret
                    self.dp.pc = self.dp.epc
                    self.dp.ps_ie = True
                    self.print_state("iret")
                elif funct3 == 2:  # halt
                    self.halted = True
                    self.print_state("halt")

            else:
                raise ValueError(f"Unknown Opcode: 0x{opcode:02X} at PC: 0x{current_pc:08X}")
