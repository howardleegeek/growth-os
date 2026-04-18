"""Tests for engine/results_log.py — append-only TSV with atomic writes."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from results_log import COLUMNS, LogRow, ResultsLog


@pytest.fixture()
def fresh_log(tmp_path: Path) -> ResultsLog:
    return ResultsLog(tmp_path / "test.tsv")


def test_init_writes_header(fresh_log: ResultsLog):
    content = fresh_log.path.read_text().splitlines()[0].split("\t")
    assert content == COLUMNS


def test_append_adds_one_row(fresh_log: ResultsLog):
    fresh_log.append("ship_test", "target_a", 18.4, "kept", notes="ok", provenance="abc1234")
    lines = fresh_log.path.read_text().splitlines()
    assert len(lines) == 2  # header + 1 row


def test_iteration_counter_monotonic(fresh_log: ResultsLog):
    fresh_log.append("ship_test", "t1", 1.0, "kept")
    fresh_log.append("ship_test", "t2", 2.0, "discarded")
    fresh_log.append("ship_test", "t3", 3.0, "kept")
    rows = fresh_log.tail(3)
    assert [r.iteration for r in rows] == [1, 2, 3]


def test_kept_and_discarded_counts(fresh_log: ResultsLog):
    fresh_log.append("ship_test", "a", 1.0, "kept")
    fresh_log.append("ship_test", "b", 2.0, "discarded")
    fresh_log.append("ship_test", "c", 3.0, "kept")
    assert fresh_log.kept_count() == 2
    assert fresh_log.discarded_count() == 1


def test_counter_persists_across_reopens(tmp_path: Path):
    path = tmp_path / "persist.tsv"
    log1 = ResultsLog(path)
    log1.append("ship_test", "a", 1.0, "kept")
    log1.append("ship_test", "b", 2.0, "kept")

    # Reopen — should continue from iteration 2
    log2 = ResultsLog(path)
    log2.append("ship_test", "c", 3.0, "kept")
    rows = log2.tail(10)
    assert [r.iteration for r in rows] == [1, 2, 3]


def test_notes_with_tabs_are_sanitized(fresh_log: ResultsLog):
    """TSV invariant: notes containing tabs would break the row shape."""
    fresh_log.append("ship_test", "t", 1.0, "kept", notes="has\ttab\tinside")
    raw = fresh_log.path.read_text().splitlines()[1]
    # Row should have exactly len(COLUMNS) fields — tabs in notes got replaced
    assert len(raw.split("\t")) == len(COLUMNS)


def test_notes_with_newlines_are_sanitized(fresh_log: ResultsLog):
    fresh_log.append("ship_test", "t", 1.0, "kept", notes="line1\nline2")
    lines = fresh_log.path.read_text().splitlines()
    assert len(lines) == 2  # header + 1 row (not 3)


def test_tail_returns_last_n_only(fresh_log: ResultsLog):
    for i in range(10):
        fresh_log.append("ship_test", f"t{i}", float(i), "kept")
    assert len(fresh_log.tail(3)) == 3
    assert [r.iteration for r in fresh_log.tail(3)] == [8, 9, 10]


def test_log_row_to_tsv_formats_correctly():
    row = LogRow(
        iteration=42, timestamp="2026-04-18T00:00:00+00:00",
        action="ship_test", target="x", score=10.5, result="kept",
        notes="ok", provenance="abc1234",
    )
    parts = row.to_tsv().split("\t")
    assert parts[0] == "000042"
    assert parts[4] == "+10.5"
    assert parts[5] == "kept"


def test_header_matches_schema(tmp_path: Path):
    """TSV structure is part of the contract — don't let it drift."""
    log = ResultsLog(tmp_path / "schema.tsv")
    log.append("ship_test", "t", 1.0, "kept")

    with open(log.path) as f:
        reader = csv.DictReader(f, delimiter="\t")
        assert reader.fieldnames == COLUMNS
        row = next(reader)
        assert set(row.keys()) == set(COLUMNS)
