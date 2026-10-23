"""The tiresias pin: v0.1.1 (CTE-scope allowlist fix), identical in every install path."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Commit the v0.1.1 tag points at (HIGH CTE-scope allowlist bypass fix + locked-down DuckDB).
V0_1_1 = "0ae91238f19070d6453762dee831d110d0f2e5f9"
ARCHIVE = f"https://github.com/EvanWAppel/tiresias/archive/{V0_1_1}.zip"


def test_pyproject_pins_tiresias_v0_1_1():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert pyproject["tool"]["uv"]["sources"]["tiresias"]["url"] == ARCHIVE


def test_uv_lock_resolves_tiresias_v0_1_1():
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    [pkg] = [p for p in lock["package"] if p["name"] == "tiresias"]
    assert pkg["source"]["url"] == ARCHIVE


def test_docker_requirements_pin_matches_pyproject():
    # The Docker image installs from requirements.txt, so it must carry the same pin.
    pins = re.findall(
        r"^tiresias\[streamlit\] @ (\S+)$",
        (ROOT / "requirements.txt").read_text(),
        re.MULTILINE,
    )
    assert pins == [ARCHIVE]
