import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Isa.isa import BinaryManager
from Translator.assembler import Assembler
from Translator.preprocessor import Preprocessor


def main():
    parser = argparse.ArgumentParser(description="RISC Assembler")
    parser.add_argument("source", help="Source assembly file (.asm)")
    parser.add_argument("binary", help="Output binary file (.bin)")
    parser.add_argument("--debug", help="Output debug text file", default="debug.txt")
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"Error: File '{args.source}' not found.")
        sys.exit(1)

    with open(args.source, "r", encoding="utf-8") as f:
        source_code = f.read()

    try:
        source_code = Preprocessor().process(source_code)

        asm = Assembler()
        asm.pass_1(source_code)

        if "_start" not in asm.labels:
            print("Warning: Entry point label '_start' not found. PC will start at 0x0100.")

        asm.pass_2()

        BinaryManager.write_binary(args.binary, asm.text_section, asm.data_section)
        BinaryManager.write_debug(args.debug, asm.text_section, asm.data_section)

        print(f"Compilation successful! Wrote to {args.binary} and {args.debug}")

    except Exception as e:
        print(f"Compilation Error:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
