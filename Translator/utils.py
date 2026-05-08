def parse_int(val: str) -> int:
    if val.startswith('0x') or val.startswith('-0x'):
        return int(val, 16)
    return int(val)
