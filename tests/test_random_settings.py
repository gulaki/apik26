"""The random tests use fixed seeds and sizes, so every pull request runs the
same cases. The weekly workflow sets APIK_RANDOM_SCALE (more cases) and
APIK_RANDOM_SEED (other cases); the test summary header shows both, so a
failure can be run again."""
import pytest

import conftest


def test_the_defaults_keep_the_fixed_cases(monkeypatch):
    monkeypatch.delenv("APIK_RANDOM_SCALE", raising=False)
    monkeypatch.delenv("APIK_RANDOM_SEED", raising=False)
    assert conftest.random_count(300) == 300
    assert conftest.random_seed(20261023) == 20261023


def test_the_scale_multiplies_the_count(monkeypatch):
    monkeypatch.setenv("APIK_RANDOM_SCALE", "10")
    assert conftest.random_count(300) == 3000


def test_the_seed_changes_every_test_s_seed(monkeypatch):
    monkeypatch.setenv("APIK_RANDOM_SEED", "7")
    assert conftest.random_seed(1) != conftest.random_seed(2)
    assert conftest.random_seed(1) != 1
    assert conftest.random_seed(1) == conftest.random_seed(1)


@pytest.mark.parametrize("name, value", [("APIK_RANDOM_SCALE", "0"), ("APIK_RANDOM_SCALE", "x"),
                                         ("APIK_RANDOM_SEED", "-1"), ("APIK_RANDOM_SEED", "seed")])
def test_a_bad_setting_is_a_usage_error(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(pytest.UsageError, match=name):
        conftest.random_settings()


def test_the_header_shows_the_settings(monkeypatch):
    monkeypatch.setenv("APIK_RANDOM_SCALE", "10")
    monkeypatch.setenv("APIK_RANDOM_SEED", "7")
    assert conftest.pytest_report_header(None) == "random tests: APIK_RANDOM_SCALE=10 APIK_RANDOM_SEED=7"
