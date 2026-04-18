"""
Results log — TSV append with atomic writes and provenance guarantees.

Every autoresearch iteration ends with exactly one row appended here.
The log is the training set for future iterations; it's also the audit trail
for every decision the loop has ever made.

Design constraints, in priority order:

1. **Append-only.** Rows are never modified. Mistakes become new rows that
   reference the mistake row.
2. **Atomic.** Power loss during a write must not produce a half-row. We
   write to a temp file + rename under `os.O_APPEND`.
3. **Grep-able.** TSV so `grep`, `cut`, `sort`, `awk` all work. No JSON logs.
4. **Self-describing.** First line is the header; every subsequent line has
   exactly the same number of columns.
5. **Cheap.** No dependencies. stdlib only. A 6-month-old TSV on a VPS must
   still parse.
"""

from __future__ import annotations

import csv
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


# --------------------------------------------------------------------------- #
# Row schema
# --------------------------------------------------------------------------- #

COLUMNS = [
    "iteration",        # monotonic integer, 6 digits zero-padded
    "timestamp",        # ISO 8601 UTC
    "action",           # ship_test / rederive / discard / calibrate / ...
    "target",           # candidate ID or pattern name
    "score",            # score vs weight map (signed float, 1 decimal)
    "result",           # kept / discarded / failed / skipped
    "notes",            # human-readable context
    "provenance",       # git commit hash at time of execution
]


@dataclass
class LogRow:
    iteration:   int
    timestamp:   str
    action:      str
    target:      str
    score:       float
    result:      str
    notes:       str
    provenance:  str

    def to_tsv(self) -> str:
        return "\t".join([
            f"{self.iteration:06d}",
            self.timestamp,
            self.action,
            self.target,
            f"{self.score:+.1f}",
            self.result,
            self.notes.replace("\t", " ").replace("\n", " "),
            self.provenance,
        ])


# --------------------------------------------------------------------------- #
# The log
# --------------------------------------------------------------------------- #

class ResultsLog:
    """Append-only TSV log with atomic writes."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Init the file if it doesn't exist OR exists but is empty (e.g. a
        # freshly-created tempfile). Either way, we need the header row first.
        if not self.path.exists() or self.path.stat().st_size == 0:
            self._init_file()
        self._iteration_counter = self._recover_iteration_counter()

    def _init_file(self) -> None:
        """Write the header on first use."""
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("\t".join(COLUMNS) + "\n")

    def _recover_iteration_counter(self) -> int:
        """On startup, read the last row to continue the iteration sequence."""
        last = 0
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    try:
                        last = max(last, int(row["iteration"]))
                    except (KeyError, ValueError):
                        continue
        except FileNotFoundError:
            return 0
        return last

    def next_iteration(self) -> int:
        self._iteration_counter += 1
        return self._iteration_counter

    def append(self, action: str, target: str, score: float, result: str, notes: str = "",
               provenance: str = "") -> LogRow:
        """Append one row. Atomic under POSIX — single write() call."""
        row = LogRow(
            iteration  = self.next_iteration(),
            timestamp  = datetime.now(timezone.utc).isoformat(),
            action     = action,
            target     = target,
            score      = score,
            result     = result,
            notes      = notes,
            provenance = provenance,
        )
        line = row.to_tsv() + "\n"
        # O_APPEND + single-write is atomic on POSIX for writes <= PIPE_BUF (4096).
        # Our rows are well under 4096 bytes in practice.
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
        return row

    # --- Read-side helpers ---------------------------------------------- #

    def tail(self, n: int = 10) -> list[LogRow]:
        """Return the last n rows. Used by the hypothesis generator."""
        rows: list[LogRow] = []
        with open(self.path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for r in reader:
                try:
                    rows.append(LogRow(
                        iteration  = int(r["iteration"]),
                        timestamp  = r["timestamp"],
                        action     = r["action"],
                        target     = r["target"],
                        score      = float(r["score"]),
                        result     = r["result"],
                        notes      = r["notes"],
                        provenance = r["provenance"],
                    ))
                except (KeyError, ValueError):
                    continue
        return rows[-n:]

    def kept_count(self) -> int:
        """Total iterations whose result was 'kept'. The main success metric."""
        return sum(1 for r in self.tail(n=10**9) if r.result == "kept")

    def discarded_count(self) -> int:
        return sum(1 for r in self.tail(n=10**9) if r.result == "discarded")


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    # Use a temp file so we don't pollute real logs
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as tf:
        path = Path(tf.name)

    log = ResultsLog(path)
    log.append("ship_test", "selfreply_v3", +18.4, "kept",
               notes="+203% vs ctl, n=412, z=2.84", provenance="abc1234")
    log.append("ship_test", "meme_plug",    -24.1, "discarded",
               notes="triggered tier-C gate",       provenance="abc1234")
    log.append("rederive",  "weight_map",    0.0,  "kept",
               notes="LinkedIn: dwell 48→52, reshare 18→22", provenance="abc1234")

    print(f"Wrote to:  {path}")
    print(f"Kept:      {log.kept_count()}")
    print(f"Discarded: {log.discarded_count()}")
    print("\nTail(3):")
    for row in log.tail(3):
        print(f"  {row.to_tsv()}", file=sys.stdout)

    path.unlink(missing_ok=True)
