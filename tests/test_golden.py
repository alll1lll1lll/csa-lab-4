import json
import logging
import os
import sys
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from typing import Any

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Machine.machine import main as machine_main
from Translator.translator import main as asm_main

logging.getLogger().setLevel(logging.INFO)


def truncate_log(log_text: str, max_lines: int = 100) -> str:
    lines = log_text.strip().split("\n")
    if len(lines) <= max_lines:
        return log_text
    half = max_lines // 2
    truncated = lines[:half] + ["\n... [LOG TRUNCATED] ...\n"] + lines[-half:]
    return "\n".join(truncated)


@pytest.mark.golden_test("../golden/*.yml")
def test_programs(golden: Any, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = os.path.join(tmpdir, "source.asm")
        binary_path = os.path.join(tmpdir, "out.bin")
        debug_path = os.path.join(tmpdir, "out.txt")
        schedule_path = os.path.join(tmpdir, "schedule.json")

        with open(source_path, "w", encoding="utf-8") as f:
            f.write(golden["source"])

        with open(schedule_path, "w", encoding="utf-8") as f:
            json.dump(golden.get("input_schedule", []), f)

        monkeypatch.setattr(sys, "argv", ["translator", source_path, binary_path, "--debug", debug_path])
        try:
            asm_main()
        except SystemExit as e:
            assert e.code == 0, "Assembler failed"

        with open(debug_path, "r", encoding="utf-8") as f:
            machine_code = f.read()

        caplog.clear()
        f_out = StringIO()
        with redirect_stdout(f_out):
            monkeypatch.setattr(sys, "argv", ["machine", binary_path, schedule_path])
            try:
                machine_main()
            except SystemExit as e:
                assert e.code == 0, "Machine failed"

        output = f_out.getvalue()

        log_text = "\n".join([rec.message for rec in caplog.records])
        log_text = truncate_log(log_text)

        assert machine_code == golden.out["machine_code"]
        assert output == golden.out["output"]
        assert log_text == golden.out["log"]
