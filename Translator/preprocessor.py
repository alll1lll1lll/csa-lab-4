
import re


class Preprocessor:
    """
    Pre-processes assembly source before the two-pass assembler.

    Supported directives:
      .define NAME [value]   — define a symbol (default value = 1)
      .undef  NAME           — undefine a symbol
      .ifdef  NAME / .ifndef NAME / .else / .endif — conditional blocks
      .macro  NAME [p1, p2, ...]  /  .endm          — macro definition
      NAME [arg1, arg2, ...]                         — macro invocation
    """

    def __init__(self):
        self.defines: dict[str, str] = {}
        self.macros: dict[str, tuple[list[str], list[str]]] = {}

    def process(self, source: str) -> str:
        lines = source.splitlines()
        lines = self._collect(lines)
        lines = self._expand(lines)
        return '\n'.join(lines)

    # Pass A: handle .define/.undef/.ifdef/.ifndef/.else/.endif/.macro/.endm
    def _collect(self, lines: list[str]) -> list[str]:
        output: list[str] = []
        cond_stack: list[bool] = []   # True = this level is including

        in_macro = False
        macro_name = ''
        macro_params: list[str] = []
        macro_body: list[str] = []

        for line in lines:
            stripped = line.split(';')[0].strip()

            # --- Inside a macro body ---
            if in_macro:
                if stripped == '.endm':
                    self.macros[macro_name] = (macro_params, macro_body)
                    in_macro = False
                else:
                    macro_body.append(line)
                continue

            including = all(cond_stack) if cond_stack else True

            # Conditional directives (processed even when skipping,
            # because we must track nesting depth)
            if stripped.startswith('.ifdef') or stripped.startswith('.ifndef'):
                parts = stripped.split()
                symbol = parts[1] if len(parts) > 1 else ''
                defined = symbol in self.defines
                is_ifdef = stripped.startswith('.ifdef')
                # Only enter true branch if outer context allows it
                cond_stack.append((defined if is_ifdef else not defined) and including)
                continue

            if stripped == '.else':
                if cond_stack:
                    outer = all(cond_stack[:-1]) if len(cond_stack) > 1 else True
                    cond_stack[-1] = (not cond_stack[-1]) and outer
                continue

            if stripped == '.endif':
                if cond_stack:
                    cond_stack.pop()
                continue

            if not including:
                continue

            # Active directives
            if stripped.startswith('.define'):
                parts = stripped.split(None, 2)
                name = parts[1]
                value = parts[2] if len(parts) > 2 else '1'
                self.defines[name] = value
                continue

            if stripped.startswith('.undef'):
                parts = stripped.split()
                if len(parts) > 1:
                    self.defines.pop(parts[1], None)
                continue

            if stripped.startswith('.macro'):
                rest = stripped[len('.macro'):].strip()
                name_part, _, params_part = rest.partition(' ')
                macro_name = name_part.strip()
                if params_part.strip():
                    macro_params = [p.strip() for p in params_part.split(',')]
                else:
                    macro_params = []
                macro_body = []
                in_macro = True
                continue

            output.append(line)

        return output

    # Pass B: expand macro invocations
    def _expand(self, lines: list[str]) -> list[str]:
        if not self.macros:
            return lines

        output: list[str] = []
        for line in lines:
            code = line.split(';')[0].strip()
            if not code:
                output.append(line)
                continue

            tokens = re.split(r'[\s,]+', code)
            mnemonic = tokens[0]
            if mnemonic in self.macros:
                params, body = self.macros[mnemonic]
                call_args = [t for t in tokens[1:] if t]
                for body_line in body:
                    expanded = body_line
                    for param, arg in zip(params, call_args):
                        expanded = re.sub(r'\\' + re.escape(param), arg, expanded)
                    output.append(expanded)
            else:
                output.append(line)

        return output
