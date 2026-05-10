import logging

from Isa.isa import REGISTERS, Opcode

# R-type dispatch: (funct3, funct7) -> (alu_op, is_cmp)
_R_DISPATCH = {
    (0, 0): (0,  False),  # add
    (1, 0): (1,  False),  # sub
    (2, 0): (2,  False),  # mul
    (2, 1): (11, False),  # mulh
    (3, 0): (3,  False),  # div
    (3, 1): (12, False),  # rem
    (4, 0): (4,  False),  # and
    (5, 0): (5,  False),  # or
    (6, 0): (6,  False),  # xor
    (7, 0): (7,  True),   # cmp (flags only, no rd write)
    (7, 1): (8,  False),  # sll
    (7, 3): (9,  False),  # srl
    (7, 4): (10, False),  # sra
}

# I-type ALU dispatch: funct3 -> alu_op
_I_ALU_DISPATCH = {
    0: 0,   # addi
    1: 8,   # slli
    2: 13,  # slti
    3: 9,   # srli
    4: 4,   # andi
    5: 5,   # ori
    6: 6,   # xori
    7: 10,  # srai
}
_I_SHIFT_FUNCT3 = {1, 3, 7}  # funct3 values where imm is a shift amount


class ControlUnit:
    def __init__(self, datapath):
        self.dp = datapath
        self.ticks = 0
        self.halted = False

    def tick(self):
        self.ticks += 1

    # --- Decoders ---

    def decode_r_type(self, instruction):
        # [opcode:6][rd:5][rs1:5][rs2:5][funct3:3][funct7:8]
        opcode = (instruction >> 26) & 0x3F
        rd     = (instruction >> 21) & 0x1F
        rs1    = (instruction >> 16) & 0x1F
        rs2    = (instruction >> 11) & 0x1F
        funct3 = (instruction >> 8)  & 0x7
        funct7 =  instruction        & 0xFF
        return opcode, rd, rs1, rs2, funct3, funct7

    def decode_i_type(self, instruction):
        # [opcode:6][rd:5][rs1:5][funct3:3][imm:13]
        opcode = (instruction >> 26) & 0x3F
        rd     = (instruction >> 21) & 0x1F
        rs1    = (instruction >> 16) & 0x1F
        funct3 = (instruction >> 13) & 0x7
        imm    =  instruction        & 0x1FFF
        if imm & 0x1000:
            imm -= 0x2000
        return opcode, rd, rs1, funct3, imm

    def decode_s_type(self, instruction):
        # [opcode:6][imm[12:9]:4][rs1:5][rs2:5][funct3:3][imm[8:0]:9]
        opcode   = (instruction >> 26) & 0x3F
        imm_12_9 = (instruction >> 22) & 0xF
        rs1      = (instruction >> 17) & 0x1F
        rs2      = (instruction >> 12) & 0x1F
        funct3   = (instruction >> 9)  & 0x7
        imm_8_0  =  instruction        & 0x1FF
        imm = (imm_12_9 << 9) | imm_8_0
        if imm & 0x1000:
            imm -= 0x2000
        return opcode, rs1, rs2, funct3, imm

    def decode_u_type(self, instruction):
        # [opcode:6][rd:5][imm:21]
        opcode = (instruction >> 26) & 0x3F
        rd     = (instruction >> 21) & 0x1F
        imm    =  instruction        & 0x1FFFFF
        if imm & 0x100000:
            imm -= 0x200000
        return opcode, rd, imm

    def print_state(self, mnemonic):
        ie = int(self.dp.ps_ie)
        logging.info(
            f"Tick: {self.ticks:04d} | PC: 0x{self.dp.pc:08X} | {mnemonic:20} | "
            f"t0: {self.dp.regs[REGISTERS['t0']]}, t1: {self.dp.regs[REGISTERS['t1']]}, "
            f"sp: 0x{self.dp.regs[REGISTERS['sp']]:X} | "
            f"N:{self.dp.ps_flags['N']} Z:{self.dp.ps_flags['Z']} "
            f"V:{self.dp.ps_flags['V']} C:{self.dp.ps_flags['C']} IE:{ie}"
        )

    def run(self, schedule=None):
        if schedule is None:
            schedule = []

        schedule_idx = 0

        while not self.halted:
            # Deliver all chars whose scheduled tick has arrived.
            # If a previous char was not yet read by the ISR, it is overwritten (lost).
            while schedule_idx < len(schedule):
                sched_tick, char = schedule[schedule_idx]
                if self.ticks >= sched_tick:
                    self.dp.memory.input_char = ord(char)
                    schedule_idx += 1
                else:
                    break

            if self.dp.memory.eof:
                self.halted = True
                continue

            # Hardware interrupt: fires when input register has data and IE is enabled
            if self.dp.memory.input_char is not None and self.dp.ps_ie:
                self.dp.epc = self.dp.pc
                self.dp.ps_ie = False
                vec, _ = self.dp.cache.read(0x00000008, self.dp.memory)
                self.dp.pc = vec
                self.tick()
                self.tick()
                self.print_state("--- HARDWARE TRAP ---")
                continue

            # FETCH
            current_pc = self.dp.pc
            instruction, fetch_ticks = self.dp.cache.read(current_pc, self.dp.memory)
            self.dp.pc += 4
            for _ in range(fetch_ticks):
                self.tick()

            opcode = (instruction >> 26) & 0x3F

            # EXECUTE

            if opcode == Opcode.OP_R:
                _, rd, rs1, rs2, funct3, funct7 = self.decode_r_type(instruction)
                val1, val2 = self.dp.read_reg(rs1), self.dp.read_reg(rs2)

                alu_op, is_cmp = _R_DISPATCH.get((funct3, funct7), (0, False))
                result, flags = self.dp.alu(alu_op, val1, val2)
                self.tick()

                if not is_cmp:
                    self.dp.write_reg(rd, result)
                self.dp.ps_flags.update(flags)
                self.tick()
                self.print_state(f"alu r{rd}, r{rs1}, r{rs2}")

            elif opcode == Opcode.OP_I_ALU:
                _, rd, rs1, funct3, imm = self.decode_i_type(instruction)
                val1 = self.dp.read_reg(rs1)
                alu_op = _I_ALU_DISPATCH.get(funct3, 0)
                eff_imm = (imm & 0x1F) if funct3 in _I_SHIFT_FUNCT3 else imm

                result, flags = self.dp.alu(alu_op, val1, eff_imm)
                self.tick()

                self.dp.write_reg(rd, result)
                self.dp.ps_flags.update(flags)
                self.tick()
                self.print_state(f"alu_i r{rd}, r{rs1}, {imm}")

            elif opcode == Opcode.OP_I_LOAD:
                _, rd, rs1, funct3, imm = self.decode_i_type(instruction)
                address = self.dp.read_reg(rs1) + imm
                self.tick()

                data, mem_ticks = self.dp.cache.read(address, self.dp.memory)
                if funct3 == 1:  # lb — sign-extend byte
                    data = data & 0xFF
                    if data & 0x80:
                        data -= 0x100
                for _ in range(mem_ticks):
                    self.tick()

                self.dp.write_reg(rd, data)
                self.tick()
                self.print_state(f"load r{rd}, {imm}(r{rs1})")

            elif opcode == Opcode.OP_S_STORE:
                _, rs1, rs2, funct3, imm = self.decode_s_type(instruction)
                val1, val2 = self.dp.read_reg(rs1), self.dp.read_reg(rs2)
                address = val1 + imm
                self.tick()

                if funct3 == 1:  # sb — read-modify-write
                    aligned = address & ~3
                    byte_off = address % 4
                    word, r_ticks = self.dp.cache.read(aligned, self.dp.memory)
                    word = (word & ~(0xFF << (byte_off * 8))) | ((val2 & 0xFF) << (byte_off * 8))
                    w_ticks = self.dp.cache.write(aligned, word, self.dp.memory)
                    for _ in range(max(r_ticks, w_ticks)):
                        self.tick()
                else:
                    w_ticks = self.dp.cache.write(address, val2, self.dp.memory)
                    for _ in range(w_ticks):
                        self.tick()
                self.print_state(f"store r{rs2}, {imm}(r{rs1})")

            elif opcode == Opcode.OP_B_BRANCH:
                _, rs1, rs2, funct3, imm = self.decode_s_type(instruction)
                _, flags = self.dp.alu(1, self.dp.read_reg(rs1), self.dp.read_reg(rs2))
                self.dp.ps_flags.update(flags)
                self.tick()

                N, Z, V, C = flags['N'], flags['Z'], flags['V'], flags['C']
                take = False
                if   funct3 == 0: take = Z == 1                      # beq
                elif funct3 == 1: take = Z == 0                      # bne
                elif funct3 == 2: take = (N ^ V) == 1                # blt
                elif funct3 == 3: take = (N ^ V) == 0                # bge
                elif funct3 == 4: take = Z == 1 or (N ^ V) == 1      # ble
                elif funct3 == 5: take = Z == 0 and (N ^ V) == 0     # bgt
                elif funct3 == 6: take = C == 1                      # blo (unsigned <)
                elif funct3 == 7: take = C == 0                      # bgeu (unsigned >=)

                if take:
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
                self.dp.write_reg(rd, self.dp.pc)   # rd = PC+4 (already incremented)
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
                if funct3 == 0:    # trap
                    self.dp.epc = self.dp.pc
                    self.dp.ps_ie = False
                    vec, _ = self.dp.cache.read(0x00000004, self.dp.memory)
                    self.dp.pc = vec
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
