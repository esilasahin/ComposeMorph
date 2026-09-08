"""Line-based diff metrics shared by the round-trip and modification benchmarks."""
from __future__ import annotations

import difflib


def changed_line_count(a_lines: list[str], b_lines: list[str]) -> int:
    """Number of lines touched (inserted/deleted/replaced) turning a into b."""
    sm = difflib.SequenceMatcher(a=a_lines, b=b_lines, autojunk=False)
    changed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            changed += max(i2 - i1, j2 - j1)
    return changed


def line_levenshtein(a_lines: list[str], b_lines: list[str]) -> int:
    """Edit distance over lines (insert/delete/substitute), two-row DP."""
    n, m = len(a_lines), len(b_lines)
    if n == 0:
        return m
    if m == 0:
        return n
    prev = list(range(m + 1))
    curr = [0] * (m + 1)
    for i in range(1, n + 1):
        curr[0] = i
        ai = a_lines[i - 1]
        for j in range(1, m + 1):
            cost = 0 if ai == b_lines[j - 1] else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev, curr = curr, prev
    return prev[m]
