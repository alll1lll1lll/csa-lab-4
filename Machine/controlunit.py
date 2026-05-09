import logging

from Isa.isa import REGISTERS, Opcode


class ControlUnit:
    def __init__(self, datapath):
        self.dp = datapath
        self.ticks = 0
        self.halted = False

    def tick(self):
        # Advance simulation clock by one cycle
        self.ticks += 1

    # --- Instruction Decoder ---

    def decode_r_type(self, instruction):
        # IR[31:26]=opcode, [25:22]=rd, [21:18]=rs1, [17:14]=rs2, [13:11]=funct3
        opcode = (instruction >> 26) & 0x3F
        rd = (instruction >> 22) & 0xF
        rs1 = (instruction >> 18) & 0xF
        rs2 = (instruction >> 14) & 0xF
        funct3 = (instruction >> 11) & 0x7
        return opcode, rd, rs1, rs2, funct3

    def decode_i_type(self, instruction):
        # IR[31:26]=opcode, [25:22]=rd, [21:18]=rs1, [17:15]=funct3, [14:0]=imm (sign-extended)
        opcode = (instruction >> 26) & 0x3F
        rd = (instruction >> 22) & 0xF
        rs1 = (instruction >> 18) & 0xF
        funct3 = (instruction >> 15) & 0x7
        imm = instruction & 0x7FFF
        if imm & 0x4000:
            imm -= 0x8000
        return opcode, rd, rs1, funct3, imm

    def decode_s_type(self, instruction):
        # IR[31:26]=opcode, [25:22]=imm[14:11], [21:18]=rs1, [17:14]=rs2, [13:11]=funct3, [10:0]=imm[10:0]
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
        # IR[31:26]=opcode, [25:22]=rd, [21:0]=imm (sign-extended)
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
            # Deliver scheduled input characters into the FIFO at the right tick
            if schedule_idx < len(schedule):
                sched_tick, char = schedule[schedule_idx]
                if self.ticks >= sched_tick:
                    self.dp.memory.input_queue.append(ord(char))
                    self.dp.memory.irq_pending = True
                    schedule_idx += 1

            # --- Next-State Logic: EOF → HALT ---
            if self.dp.memory.eof:
                self.halted = True
                continue

            # --- Interrupt Request Logic: hardware trap if IRQ pending and interrupts enabled ---
            if self.dp.memory.irq_pending and self.dp.ps_ie:
                self.dp.epc = self.dp.pc          # save return address to EPC
                self.dp.ps_ie = False             # disable interrupts (IE_clear)
                self.dp.pc = self.dp.memory.read(0x00000008)  # MUX_PC_sel = trap_vector
                self.tick()
                self.tick()
                self.print_state("--- HARDWARE TRAP ---")
                continue

            # --- FETCH: load instruction from memory, increment PC ---
            current_pc = self.dp.pc
            instruction = self.dp.memory.read(current_pc)
            self.dp.pc += 4
            self.tick()

            # --- Instruction Decoder: extract opcode from IR[31:26] ---
            opcode = (instruction >> 26) & 0x3F

            # --- EXECUTE ---

            if opcode == Opcode.OP_R:
                # ALU Op Decoder: funct3 selects operation; funct7 disambiguates shifts/cmp
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

                # MUX_WB_sel = ALU; cmp only updates flags, does not write rd
                if not is_cmp:
                    self.dp.write_reg(rd, result)

                self.dp.ps_flags.update(calculated_flags)
                self.tick()
                self.print_state(f"alu r{rd}, r{rs1}, r{rs2}")

            elif opcode == Opcode.OP_I_ALU:
                # MUX_B_sel = imm (immediate operand from ImmGen)
                _, rd, rs1, funct3, imm = self.decode_i_type(instruction)
                val1 = self.dp.read_reg(rs1)

                result, calculated_flags = self.dp.alu(funct3, val1, imm)
                self.tick()

                # MUX_WB_sel = ALU
                self.dp.write_reg(rd, result)
                self.dp.ps_flags.update(calculated_flags)
                self.tick()
                self.print_state(f"alu_i r{rd}, r{rs1}, {imm}")

            elif opcode == Opcode.OP_I_LOAD:
                # Address calculation: rs1 + imm → memory address
                _, rd, rs1, funct3, imm = self.decode_i_type(instruction)
                val1 = self.dp.read_reg(rs1)
                address = val1 + imm
                self.tick()

                # Memory read → MDR
                data = self.dp.memory.read(address)
                if funct3 == 1:  # lb — sign-extend byte
                    data = data & 0xFF
                    if data & 0x80:
                        data -= 0x100
                self.tick()

                # MUX_WB_sel = MDR
                self.dp.write_reg(rd, data)
                self.tick()
                self.print_state(f"load r{rd}, {imm}(r{rs1})")

            elif opcode == Opcode.OP_S_STORE:
                # Address calculation: rs1 + imm → memory address
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
                # Branch Condition Logic: subtract rs1-rs2 to set flags, then evaluate funct3
                _, rs1, rs2, funct3, imm = self.decode_s_type(instruction)
                _, calculated_flags = self.dp.alu(1, self.dp.read_reg(rs1), self.dp.read_reg(rs2))
                self.dp.ps_flags.update(calculated_flags)
                self.tick()

                take_branch = False
                if funct3 == 0 and self.dp.ps_flags['Z'] == 1:    # beq
                    take_branch = True
                elif funct3 == 1 and self.dp.ps_flags['Z'] == 0:  # bne
                    take_branch = True
                elif funct3 == 2:                                   # blt
                    take_branch = (self.dp.ps_flags['N'] ^ self.dp.ps_flags['V']) == 1
                elif funct3 == 3:                                   # bge
                    take_branch = (self.dp.ps_flags['N'] ^ self.dp.ps_flags['V']) == 0
                elif funct3 == 4:                                   # ble
                    take_branch = (self.dp.ps_flags['Z'] == 1) or \
                                  ((self.dp.ps_flags['N'] ^ self.dp.ps_flags['V']) == 1)
                elif funct3 == 5:                                   # bgt
                    take_branch = (self.dp.ps_flags['Z'] == 0) and \
                                  ((self.dp.ps_flags['N'] ^ self.dp.ps_flags['V']) == 0)
                elif funct3 == 6:                                   # blo (unsigned <)
                    take_branch = self.dp.ps_flags['C'] == 1
                elif funct3 == 7:                                   # bgeu (unsigned >=)
                    take_branch = self.dp.ps_flags['C'] == 0

                # MUX_PC_sel = PC+imm if taken, else PC+4 (already set in fetch)
                if take_branch:
                    self.dp.pc = current_pc + imm
                self.tick()
                self.print_state(f"branch r{rs1}, r{rs2}, {imm}")

            elif opcode == Opcode.OP_U_LUI:
                # MUX_WB_sel = imm<<12 (no ALU involved)
                _, rd, imm = self.decode_u_type(instruction)
                self.dp.write_reg(rd, imm << 12)
                self.tick()
                self.print_state(f"lui r{rd}, {imm}")

            elif opcode == Opcode.OP_J_JAL:
                # MUX_WB_sel = PC (return address); MUX_PC_sel = PC+imm
                _, rd, imm = self.decode_u_type(instruction)
                self.dp.write_reg(rd, self.dp.pc)
                self.dp.pc = current_pc + imm
                self.tick()
                self.print_state(f"jal r{rd}, {imm}")

            elif opcode == Opcode.OP_I_JALR:
                # MUX_WB_sel = PC (return address); MUX_PC_sel = rs1+imm
                _, rd, rs1, _, imm = self.decode_i_type(instruction)
                val1 = self.dp.read_reg(rs1)
                self.dp.write_reg(rd, self.dp.pc)
                self.dp.pc = val1 + imm
                self.tick()
                self.print_state(f"jalr r{rd}, r{rs1}, {imm}")

            elif opcode == Opcode.OP_SYS:
                # System instructions: funct3 selects trap / iret / halt
                _, _, _, funct3, _ = self.decode_i_type(instruction)
                self.tick()
                if funct3 == 0:  # trap — software interrupt, jump to vector at 0x4
                    self.dp.epc = self.dp.pc
                    self.dp.ps_ie = False
                    self.dp.pc = self.dp.memory.read(0x00000004)
                    self.print_state("trap")
                elif funct3 == 1:  # iret — return from interrupt, restore IE
                    self.dp.pc = self.dp.epc
                    self.dp.ps_ie = True
                    self.print_state("iret")
                elif funct3 == 2:  # halt — stop simulation
                    self.halted = True
                    self.print_state("halt")

            else:
                raise ValueError(f"Unknown Opcode: 0x{opcode:02X} at PC: 0x{current_pc:08X}")
