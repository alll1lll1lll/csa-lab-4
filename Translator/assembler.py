import re

from Translator.codegen import CodeGenerator
from Translator.utils import parse_int

TEXT_START = 0x0000
DATA_START = 0x10000


class Assembler:

    def __init__(self):
        self.labels = {}
        self.text_section = []
        self.data_section = []
        self.pc = TEXT_START
        self.dc = DATA_START
        self.current_section = '.text'
        self.lines_info = []

    def resolve_imm(self, imm_str: str, current_pc: int, is_relative: bool = False) -> int:
        # %hi(sym) → upper bits of address (sym >> 12)
        m = re.match(r'%hi\((\w+)\)$', imm_str)
        if m:
            sym = m.group(1)
            addr = self.labels[sym] if sym in self.labels else parse_int(sym)
            return (addr >> 12) & 0x1FFFFF

        # %lo(sym) → lower 12 bits of address
        m = re.match(r'%lo\((\w+)\)$', imm_str)
        if m:
            sym = m.group(1)
            addr = self.labels[sym] if sym in self.labels else parse_int(sym)
            return addr & 0xFFF

        if imm_str in self.labels:
            target = self.labels[imm_str]
            return (target - current_pc) if is_relative else target
        return parse_int(imm_str)

    def pass_1(self, source_code: str):
        for line in source_code.splitlines():
            original_line = line
            line = line.split(';')[0].strip()
            if not line:
                continue

            label_match = re.match(r'^([a-zA-Z_]\w*):(.*)', line)
            if label_match:
                label_name = label_match.group(1)
                self.labels[label_name] = self.pc if self.current_section == '.text' else self.dc
                line = label_match.group(2).strip()
                if not line:
                    continue

            if line in ['.section .text', '.section .data']:
                self.current_section = line.split()[1]
                continue

            if line.startswith('.equ'):
                parts = line.split()
                if len(parts) >= 3:
                    name = parts[1]
                    value = parse_int(parts[2])
                    self.labels[name] = value
                continue

            if line.startswith('.org'):
                target_addr = parse_int(line.split()[1])
                if self.current_section == '.text':
                    if target_addr < self.pc:
                        raise ValueError(f".org moves backwards in .text (from {hex(self.pc)} to {hex(target_addr)})")
                    self.pc = target_addr
                elif self.current_section == '.data':
                    if target_addr < self.dc:
                        raise ValueError(f".org moves backwards in .data (from {hex(self.dc)} to {hex(target_addr)})")
                    self.dc = target_addr
                self.lines_info.append((self.current_section, line, original_line))
                continue

            self.lines_info.append((self.current_section, line, original_line))

            if self.current_section == '.data':
                if line.startswith('.word'):
                    args = line.replace('.word', '').split(',')
                    self.dc += 4 * len(args)
                elif line.startswith('.string'):
                    match = re.search(r'"(.*)"', line)
                    if match:
                        str_val = match.group(1).encode('utf-8').decode('unicode_escape')
                        self.dc += 4 * (len(str_val) + 1)
            elif self.current_section == '.text':
                self.pc += 4

    def pass_2(self):
        self.pc = TEXT_START
        self.dc = DATA_START

        for section, line, original in self.lines_info:

            if line.startswith('.org'):
                target_addr = parse_int(line.split()[1])
                if section == '.text':
                    while self.pc < target_addr:
                        self.text_section.append((self.pc, 0, "nop"))
                        self.pc += 4
                elif section == '.data':
                    while self.dc < target_addr:
                        self.data_section.append((self.dc, 0, "0"))
                        self.dc += 4
                continue

            if section == '.data':
                if line.startswith('.word'):
                    args = [a.strip() for a in line.replace('.word', '').split(',')]
                    for arg in args:
                        val = self.resolve_imm(arg, self.pc, False)
                        self.data_section.append((self.dc, val, f".word {val}"))
                        self.dc += 4
                elif line.startswith('.string'):
                    str_val = re.search(r'"(.*)"', line).group(1).encode('utf-8').decode('unicode_escape')
                    for char in str_val:
                        self.data_section.append((self.dc, ord(char), f".string '{char}'"))
                        self.dc += 4
                    self.data_section.append((self.dc, 0, ".string '\\0'"))
                    self.dc += 4

            elif section == '.text':
                if line.startswith('.word'):
                    arg = line.replace('.word', '').strip()
                    val = self.resolve_imm(arg, self.pc, False)
                    self.text_section.append((self.pc, val, f".word {val}"))
                    self.pc += 4
                    continue

                tokens = line.replace(',', ' ').split()
                mnemonic, args = tokens[0], tokens[1:]

                try:
                    machine_word = CodeGenerator.encode_instruction(mnemonic, args, self.pc, self.resolve_imm)
                except ValueError as e:
                    raise ValueError(f"Error in line: '{original.strip()}' -> {e}")

                self.text_section.append((self.pc, machine_word, original.strip()))
                self.pc += 4
