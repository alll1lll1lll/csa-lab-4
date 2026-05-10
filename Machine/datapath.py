from Machine.cache import Cache


class DataPath:
    def __init__(self, memory):
        self.memory = memory
        self.cache = Cache(size=16)
        self.regs = [0] * 32
        self.pc = 0x0100
        self.epc = 0
        self.ps_ie = True
        self.ps_flags = {'N': 0, 'Z': 0, 'V': 0, 'C': 0}

    def read_reg(self, reg_num):
        return 0 if reg_num == 0 else self.regs[reg_num]

    def write_reg(self, reg_num, value):
        if reg_num != 0:
            self.regs[reg_num] = value & 0xFFFFFFFF

    def alu(self, op, val1, val2):
        flags = {'N': 0, 'Z': 0, 'V': 0, 'C': 0}

        s_val1 = val1 if val1 < 0x80000000 else val1 - 0x100000000
        s_val2 = val2 if val2 < 0x80000000 else val2 - 0x100000000

        result = 0

        if op == 0:    # add
            result = val1 + val2
            flags['C'] = 1 if result > 0xFFFFFFFF else 0
            s_result = s_val1 + s_val2
            flags['V'] = 1 if (s_val1 > 0 and s_val2 > 0 and s_result < 0) or \
                               (s_val1 < 0 and s_val2 < 0 and s_result > 0) else 0
        elif op == 1:  # sub
            result = val1 - val2
            flags['C'] = 1 if result < 0 else 0
            s_result = s_val1 - s_val2
            flags['V'] = 1 if (s_val1 > 0 and s_val2 < 0 and s_result < 0) or \
                               (s_val1 < 0 and s_val2 > 0 and s_result > 0) else 0
        elif op == 2:  # mul (low 32 bits)
            result = val1 * val2
            if abs(result) > 0x7FFFFFFF:
                flags['V'] = 1
            if result > 0xFFFFFFFF:
                flags['C'] = 1
        elif op == 3:  # div (signed)
            result = int(s_val1 / s_val2) if s_val2 != 0 else 0
        elif op == 4:  # and
            result = val1 & val2
        elif op == 5:  # or
            result = val1 | val2
        elif op == 6:  # xor
            result = val1 ^ val2
        elif op == 7:  # cmp — sub, result discarded by CU (only flags matter)
            result = val1 - val2
            s_result = s_val1 - s_val2
            flags['C'] = 1 if result < 0 else 0
            flags['V'] = 1 if (s_val1 > 0 and s_val2 < 0 and s_result < 0) or \
                               (s_val1 < 0 and s_val2 > 0 and s_result > 0) else 0
        elif op == 8:  # sll / sla
            result = val1 << (val2 & 0x1F)
        elif op == 9:  # srl
            result = (val1 & 0xFFFFFFFF) >> (val2 & 0x1F)
        elif op == 10: # sra
            sv = val1 if val1 < 0x80000000 else val1 - 0x100000000
            result = sv >> (val2 & 0x1F)
        elif op == 11: # mulh — upper 32 bits of signed product
            result = (s_val1 * s_val2) >> 32
        elif op == 12: # rem — signed remainder (sign follows dividend)
            if s_val2 == 0:
                result = 0
            else:
                result = s_val1 - int(s_val1 / s_val2) * s_val2
        elif op == 13: # slt — set less than (signed)
            result = 1 if s_val1 < s_val2 else 0

        result_masked = result & 0xFFFFFFFF
        flags['Z'] = 1 if result_masked == 0 else 0
        flags['N'] = 1 if (result_masked & 0x80000000) != 0 else 0

        return result_masked, flags
