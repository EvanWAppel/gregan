"""Glendora's Tiresias config: valid, consistent with the dbt artifacts, page safe."""

import json
from pathlib import Path

import pytest
from tiresias.check import check_config
from tiresias.config import load_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def config():
    return load_config(ROOT / "tiresias.yml")


def test_config_loads(config):
    assert config.city == "Glendora"
    assert config.gold.answers.exists() and config.gold.retrieval.exists()


@pytest.fixture(scope="module")
def built(config):
    if not config.catalog_path.exists():
        pytest.skip("dbt artifacts absent; run dbt build + dbt docs generate")
    return config


def test_config_has_no_problems_against_the_artifacts(built):
    assert [p.message for p in check_config(built)] == []


def test_every_built_mart_is_classified(built):
    # A new mart must be deliberately opted in or out of the agent's scope.
    nodes = json.loads(built.catalog_path.read_text())["nodes"].values()
    marts = {n["metadata"]["name"] for n in nodes if n["metadata"]["name"].startswith("mart_")}
    assert marts == built.tables.allowed | built.tables.excluded


def test_ask_page_without_a_key_shows_a_notice(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    at = AppTest.from_file(str(ROOT / "views" / "ask.py"), default_timeout=30).run()
    assert not at.exception
    assert "Glendora" in at.title[0].value
    assert "ANTHROPIC_API_KEY" in at.info[0].value
    assert len(at.chat_input) == 0
