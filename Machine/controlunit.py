import logging
from enum import Enum, auto
from Isa.isa import REGISTERS, Opcode

_R_DISPATCH = {
    (0, 0): (0, False),
    (1, 0): (1, False),
    (2, 0): (2, False),
    (2, 1): (11, False),
    (3, 0): (3, False),
    (3, 1): (12, False),
    (4, 0): (4, False),
    (5, 0): (5, False),
    (6, 0): (6, False),
    (7, 0): (7, True),
    (7, 1): (8, False),
    (7, 3): (9, False),
    (7, 4): (10, False),
}
_I_ALU_DISPATCH = {0: 0, 1: 8, 2: 13, 3: 9, 4: 4, 5: 5, 6: 6, 7: 10}
_I_SHIFT_FUNCT3 = {1, 3, 7}


class CpuState(Enum):
    FETCH = auto()
    FETCH_WAIT = auto()  # wait instruction cache
    DECODE = auto()
    EXECUTE = auto()
    MEMORY = auto()
    MEMORY_WAIT = auto()  # wait data cache
    WRITE_BACK = auto()
    TRAP = auto()
    TRAP_WAIT = auto()  # wait trap vector
    HALTED = auto()


class ControlUnit:
    def __init__(self, datapath):
        self.dp = datapath
        self.ticks = 0
        self.state = CpuState.FETCH
        self.wait_ticks = 0

        # latches for data transfer between stages
        self.latch = {
            "instr": 0,
            "pending_instr": 0,
            "pc": 0,
            "opcode": 0,
            "rd": 0,
            "rs1": 0,
            "rs2": 0,
            "funct3": 0,
            "funct7": 0,
            "imm": 0,
            "val1": 0,
            "val2": 0,
            "alu_res": 0,
            "alu_flags": {},
            "mem_addr": 0,
            "mem_data": 0,
            "pending_mem_data": 0,
            "pending_trap_pc": 0,
            "trap_msg": "",
            "mnemonic": "",
        }

    def decode_r_type(self, instr):
        return (
            (instr >> 26) & 0x3F,
            (instr >> 21) & 0x1F,
            (instr >> 16) & 0x1F,
            (instr >> 11) & 0x1F,
            (instr >> 8) & 0x7,
            instr & 0xFF,
        )

    def decode_i_type(self, instr):
        return (instr >> 26) & 0x3F, (instr >> 21) & 0x1F, (instr >> 16) & 0x1F, (instr >> 13) & 0x7, instr & 0x1FFF

    def decode_s_type(self, instr):
        return (
            (instr >> 26) & 0x3F,
            (instr >> 17) & 0x1F,
            (instr >> 12) & 0x1F,
            (instr >> 9) & 0x7,
            ((instr >> 22) & 0xF) << 9 | (instr & 0x1FF),
        )

    def decode_u_type(self, instr):
        return (instr >> 26) & 0x3F, (instr >> 21) & 0x1F, instr & 0x1FFFFF

    def sign_extend(self, val, bits):
        if val & (1 << (bits - 1)):
            return val - (1 << bits)
        return val

    def print_state(self, message=""):
        ie = int(self.dp.ps_ie)
        logging.info(
            f"Tick: {self.ticks:04d} | PC: 0x{self.dp.pc:08X} | {message:20} | "
            f"t0: {self.dp.regs[REGISTERS['t0']]}, t1: {self.dp.regs[REGISTERS['t1']]}, "
            f"sp: 0x{self.dp.regs[REGISTERS['sp']]:X} | "
            f"N:{self.dp.ps_flags['N']} Z:{self.dp.ps_flags['Z']} "
            f"V:{self.dp.ps_flags['V']} C:{self.dp.ps_flags['C']} IE:{ie}"
        )

    def handle_io(self, schedule):
        for sched_tick, char in schedule:
            if self.ticks == sched_tick:
                self.dp.memory.input_char = ord(char)

    def step(self, schedule=None):
        if self.state == CpuState.HALTED:
            return False

        if schedule:
            self.handle_io(schedule)

        # hardware stall
        if self.wait_ticks > 0:
            self.wait_ticks -= 1
            self.ticks += 1
            return True

        # fsm
        if self.state == CpuState.FETCH:
            if self.dp.memory.eof:
                self.state = CpuState.HALTED
                return True

            if self.dp.memory.input_char is not None and self.dp.ps_ie:
                self.state = CpuState.TRAP
                return True

            self.latch["pc"] = self.dp.pc
            instr, fetch_ticks = self.dp.cache.read(self.dp.pc, self.dp.memory)
            self.dp.pc += 4

            # separate data arrival and latency
            if fetch_ticks > 1:
                self.latch["pending_instr"] = instr
                self.wait_ticks = fetch_ticks - 1
                self.state = CpuState.FETCH_WAIT
            else:
                self.latch["instr"] = instr
                self.state = CpuState.DECODE

        elif self.state == CpuState.FETCH_WAIT:
            self.latch["instr"] = self.latch["pending_instr"]
            self.state = CpuState.DECODE

        elif self.state == CpuState.DECODE:
            instr = self.latch["instr"]
            opcode = (instr >> 26) & 0x3F
            self.latch["opcode"] = opcode

            if opcode == Opcode.OP_R:
                _, rd, rs1, rs2, funct3, funct7 = self.decode_r_type(instr)
                self.latch.update({"rd": rd, "rs1": rs1, "rs2": rs2, "funct3": funct3, "funct7": funct7})
                self.latch["val1"], self.latch["val2"] = self.dp.read_reg(rs1), self.dp.read_reg(rs2)
                self.latch["mnemonic"] = f"alu r{rd}, r{rs1}, r{rs2}"
            elif opcode == Opcode.OP_I_ALU:
                _, rd, rs1, funct3, imm = self.decode_i_type(instr)
                self.latch.update({"rd": rd, "rs1": rs1, "funct3": funct3, "imm": self.sign_extend(imm, 13)})
                self.latch["val1"] = self.dp.read_reg(rs1)
                self.latch["mnemonic"] = f"alu_i r{rd}, r{rs1}, {self.latch['imm']}"
            elif opcode == Opcode.OP_I_LOAD:
                _, rd, rs1, funct3, imm = self.decode_i_type(instr)
                self.latch.update({"rd": rd, "rs1": rs1, "funct3": funct3, "imm": self.sign_extend(imm, 13)})
                self.latch["val1"] = self.dp.read_reg(rs1)
                self.latch["mnemonic"] = f"load r{rd}, {self.latch['imm']}(r{rs1})"
            elif opcode == Opcode.OP_S_STORE:
                _, rs1, rs2, funct3, imm = self.decode_s_type(instr)
                self.latch.update({"rs1": rs1, "rs2": rs2, "funct3": funct3, "imm": self.sign_extend(imm, 13)})
                self.latch["val1"], self.latch["val2"] = self.dp.read_reg(rs1), self.dp.read_reg(rs2)
                self.latch["mnemonic"] = f"store r{rs2}, {self.latch['imm']}(r{rs1})"
            elif opcode == Opcode.OP_B_BRANCH:
                _, rs1, rs2, funct3, imm = self.decode_s_type(instr)
                self.latch.update({"rs1": rs1, "rs2": rs2, "funct3": funct3, "imm": self.sign_extend(imm, 13)})
                self.latch["val1"], self.latch["val2"] = self.dp.read_reg(rs1), self.dp.read_reg(rs2)
                self.latch["mnemonic"] = f"branch r{rs1}, r{rs2}, {self.latch['imm']}"
            elif opcode == Opcode.OP_U_LUI:
                _, rd, imm = self.decode_u_type(instr)
                self.latch.update({"rd": rd, "imm": self.sign_extend(imm, 21)})
                self.latch["mnemonic"] = f"lui r{rd}, {self.latch['imm']}"
            elif opcode == Opcode.OP_J_JAL:
                _, rd, imm = self.decode_u_type(instr)
                self.latch.update({"rd": rd, "imm": self.sign_extend(imm, 21)})
                self.latch["mnemonic"] = f"jal r{rd}, {self.latch['imm']}"
            elif opcode == Opcode.OP_I_JALR:
                _, rd, rs1, funct3, imm = self.decode_i_type(instr)
                self.latch.update({"rd": rd, "rs1": rs1, "funct3": funct3, "imm": self.sign_extend(imm, 13)})
                self.latch["val1"] = self.dp.read_reg(rs1)
                self.latch["mnemonic"] = f"jalr r{rd}, r{rs1}, {self.latch['imm']}"
            elif opcode == Opcode.OP_SYS:
                _, _, _, funct3, _ = self.decode_i_type(instr)
                self.latch["funct3"] = funct3
                if funct3 == 0:
                    self.latch["mnemonic"] = "trap"
                elif funct3 == 1:
                    self.latch["mnemonic"] = "iret"
                elif funct3 == 2:
                    self.latch["mnemonic"] = "halt"

            self.state = CpuState.EXECUTE

        elif self.state == CpuState.EXECUTE:
            opc = self.latch["opcode"]

            if opc == Opcode.OP_R:
                alu_op, is_cmp = _R_DISPATCH.get((self.latch["funct3"], self.latch["funct7"]), (0, False))
                res, flags = self.dp.alu(alu_op, self.latch["val1"], self.latch["val2"])
                self.latch.update({"alu_res": res, "alu_flags": flags, "is_cmp": is_cmp})
                self.dp.ps_flags.update(flags)
                self.state = CpuState.WRITE_BACK

            elif opc == Opcode.OP_I_ALU:
                f3, imm = self.latch["funct3"], self.latch["imm"]
                alu_op = _I_ALU_DISPATCH.get(f3, 0)
                eff_imm = (imm & 0x1F) if f3 in _I_SHIFT_FUNCT3 else imm
                res, flags = self.dp.alu(alu_op, self.latch["val1"], eff_imm)
                self.latch.update({"alu_res": res, "alu_flags": flags})
                self.dp.ps_flags.update(flags)
                self.state = CpuState.WRITE_BACK

            elif opc in (Opcode.OP_I_LOAD, Opcode.OP_S_STORE):
                self.latch["mem_addr"] = self.latch["val1"] + self.latch["imm"]
                self.state = CpuState.MEMORY

            elif opc == Opcode.OP_B_BRANCH:
                _, flags = self.dp.alu(1, self.latch["val1"], self.latch["val2"])
                self.dp.ps_flags.update(flags)
                N, Z, V, C = flags["N"], flags["Z"], flags["V"], flags["C"]
                f3 = self.latch["funct3"]
                take = False
                if f3 == 0:
                    take = Z == 1
                elif f3 == 1:
                    take = Z == 0
                elif f3 == 2:
                    take = (N ^ V) == 1
                elif f3 == 3:
                    take = (N ^ V) == 0
                elif f3 == 4:
                    take = Z == 1 or (N ^ V) == 1
                elif f3 == 5:
                    take = Z == 0 and (N ^ V) == 0
                elif f3 == 6:
                    take = C == 1
                elif f3 == 7:
                    take = C == 0

                if take:
                    self.dp.pc = self.latch["pc"] + self.latch["imm"]
                self.print_state(self.latch["mnemonic"])
                self.state = CpuState.FETCH

            elif opc == Opcode.OP_U_LUI:
                self.latch["alu_res"] = self.latch["imm"] << 12
                self.state = CpuState.WRITE_BACK

            elif opc == Opcode.OP_J_JAL:
                self.latch["alu_res"] = self.latch["pc"] + 4
                self.dp.pc = self.latch["pc"] + self.latch["imm"]
                self.state = CpuState.WRITE_BACK

            elif opc == Opcode.OP_I_JALR:
                self.latch["alu_res"] = self.latch["pc"] + 4
                self.dp.pc = self.latch["val1"] + self.latch["imm"]
                self.state = CpuState.WRITE_BACK

            elif opc == Opcode.OP_SYS:
                f3 = self.latch["funct3"]
                if f3 == 0:
                    self.dp.epc, self.dp.eflags = self.dp.pc, self.dp.ps_flags.copy()
                    self.dp.ps_ie = False
                    vec, ticks = self.dp.cache.read(0x00000004, self.dp.memory)
                    self.latch["trap_msg"] = "SYS Trap"
                    if ticks > 1:
                        self.latch["pending_trap_pc"] = vec
                        self.wait_ticks = ticks - 1
                        self.state = CpuState.TRAP_WAIT
                    else:
                        self.dp.pc = vec
                        self.print_state(self.latch["trap_msg"])
                        self.state = CpuState.FETCH
                elif f3 == 1:
                    self.dp.pc, self.dp.ps_flags = self.dp.epc, self.dp.eflags.copy()
                    self.dp.ps_ie = True
                    self.print_state("SYS Iret")
                    self.state = CpuState.FETCH
                elif f3 == 2:
                    self.print_state("halt")
                    self.state = CpuState.HALTED

        elif self.state == CpuState.MEMORY:
            addr, opc = self.latch["mem_addr"], self.latch["opcode"]

            if opc == Opcode.OP_I_LOAD:
                data, mem_ticks = self.dp.cache.read(addr, self.dp.memory)
                if self.latch["funct3"] == 1:
                    data = data & 0xFF
                    if data & 0x80:
                        data -= 0x100

                if mem_ticks > 1:
                    self.latch["pending_mem_data"] = data
                    self.wait_ticks = mem_ticks - 1
                    self.state = CpuState.MEMORY_WAIT
                else:
                    self.latch["mem_data"] = data
                    self.state = CpuState.WRITE_BACK

            elif opc == Opcode.OP_S_STORE:
                total_ticks = 1
                if self.latch["funct3"] == 1:
                    aligned, byte_off = addr & ~3, addr % 4
                    word, r_ticks = self.dp.cache.read(aligned, self.dp.memory)
                    word = (word & ~(0xFF << (byte_off * 8))) | ((self.latch["val2"] & 0xFF) << (byte_off * 8))
                    w_ticks = self.dp.cache.write(aligned, word, self.dp.memory)
                    total_ticks = max(r_ticks, w_ticks)
                else:
                    total_ticks = self.dp.cache.write(addr, self.latch["val2"], self.dp.memory)

                if total_ticks > 1:
                    self.wait_ticks = total_ticks - 1
                    self.state = CpuState.MEMORY_WAIT
                else:
                    self.print_state(self.latch["mnemonic"])
                    self.state = CpuState.FETCH

        elif self.state == CpuState.MEMORY_WAIT:
            if self.latch["opcode"] == Opcode.OP_I_LOAD:
                self.latch["mem_data"] = self.latch["pending_mem_data"]
                self.state = CpuState.WRITE_BACK
            else:
                self.print_state(self.latch["mnemonic"])
                self.state = CpuState.FETCH

        elif self.state == CpuState.WRITE_BACK:
            opc = self.latch["opcode"]
            if opc in (Opcode.OP_R, Opcode.OP_I_ALU, Opcode.OP_U_LUI, Opcode.OP_J_JAL, Opcode.OP_I_JALR):
                if not self.latch.get("is_cmp", False):
                    self.dp.write_reg(self.latch["rd"], self.latch["alu_res"])
            elif opc == Opcode.OP_I_LOAD:
                self.dp.write_reg(self.latch["rd"], self.latch["mem_data"])

            self.print_state(self.latch["mnemonic"])
            self.state = CpuState.FETCH

        elif self.state == CpuState.TRAP:
            self.dp.epc, self.dp.eflags = self.dp.pc, self.dp.ps_flags.copy()
            self.dp.ps_ie = False
            vec, mem_ticks = self.dp.cache.read(0x00000008, self.dp.memory)
            self.latch["trap_msg"] = "--- HARDWARE TRAP ---"

            if mem_ticks > 1:
                self.latch["pending_trap_pc"] = vec
                self.wait_ticks = mem_ticks - 1
                self.state = CpuState.TRAP_WAIT
            else:
                self.dp.pc = vec
                self.print_state(self.latch["trap_msg"])
                self.state = CpuState.FETCH

        elif self.state == CpuState.TRAP_WAIT:
            self.dp.pc = self.latch["pending_trap_pc"]
            self.print_state(self.latch["trap_msg"])
            self.state = CpuState.FETCH

        self.ticks += 1
        return True

    def run(self, schedule=None):
        if schedule is None:
            schedule = []
        while self.step(schedule):
            pass
