"""The tiresias pin: v0.1.2 (settings/introspection function ban), identical in every install path."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Commit the v0.1.2 tag points at (SQL guard bans settings/introspection functions;
# rejection text hidden in the public trace panel; carries v0.1.1's CTE-scope fix).
V0_1_2 = "6d5de45cec83cb1f912263be0f968c5f38d76d75"
ARCHIVE = f"https://github.com/EvanWAppel/tiresias/archive/{V0_1_2}.zip"


def test_pyproject_pins_tiresias_v0_1_2():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert pyproject["tool"]["uv"]["sources"]["tiresias"]["url"] == ARCHIVE


def test_uv_lock_resolves_tiresias_v0_1_2():
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
