"""The random tests use fixed seeds and sizes, so every pull request runs the
same cases. The weekly workflow sets SCRIBE_RANDOM_SCALE (more cases) and
SCRIBE_RANDOM_SEED (other cases); the test summary header shows both, so a
failure can be run again."""
import pytest

import conftest


def test_the_defaults_keep_the_fixed_cases(monkeypatch):
    monkeypatch.delenv("SCRIBE_RANDOM_SCALE", raising=False)
    monkeypatch.delenv("SCRIBE_RANDOM_SEED", raising=False)
    assert conftest.random_count(300) == 300
    assert conftest.random_seed(20261023) == 20261023


def test_the_scale_multiplies_the_count(monkeypatch):
    monkeypatch.setenv("SCRIBE_RANDOM_SCALE", "10")
    assert conftest.random_count(300) == 3000


def test_the_seed_changes_every_test_s_seed(monkeypatch):
    monkeypatch.setenv("SCRIBE_RANDOM_SEED", "7")
    assert conftest.random_seed(1) != conftest.random_seed(2)
    assert conftest.random_seed(1) != 1
    assert conftest.random_seed(1) == conftest.random_seed(1)


@pytest.mark.parametrize("name, value", [("SCRIBE_RANDOM_SCALE", "0"), ("SCRIBE_RANDOM_SCALE", "x"),
                                         ("SCRIBE_RANDOM_SEED", "-1"), ("SCRIBE_RANDOM_SEED", "seed")])
def test_a_bad_setting_is_a_usage_error(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(pytest.UsageError, match=name):
        conftest.random_settings()


def test_the_header_shows_the_settings(monkeypatch):
    monkeypatch.setenv("SCRIBE_RANDOM_SCALE", "10")
    monkeypatch.setenv("SCRIBE_RANDOM_SEED", "7")
    assert conftest.pytest_report_header(None) == "random tests: SCRIBE_RANDOM_SCALE=10 SCRIBE_RANDOM_SEED=7"
