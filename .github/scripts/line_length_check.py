#!/usr/bin/env python3
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Measure the effective size of a PR: added code lines, excluding comments, blanks and Markdown."""
import argparse
import os
import re
import statistics
import subprocess
import sys

HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")
HASH = {".py", ".yml", ".yaml", ".sh", ".bash", ".cfg", ".ini", ".toml", ".j2", ".env", ".conf", ".service"}
SLASH = {".js", ".ts", ".go", ".c", ".h", ".java", ".css"}
SKIP_EXT = {".md", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".gz", ".tar", ".zip", ".rpm", ".iso", ".lock", ".json"}


def strip_comment(line, marker):
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote and line[i - 1] != "\\":
                quote = None
        elif ch in "\"'":
            quote = ch
        elif line.startswith(marker, i) and (marker != "#" or i == 0 or line[i - 1].isspace()):
            return line[:i]
    return line


def effective(line, ext):
    marker = "//" if ext in SLASH else "#" if ext in HASH or ext == "" else None
    return (strip_comment(line, marker) if marker else line).strip()


def diff_lines(base):
    """Yield (path, content, is_added) for every changed line, parsing hunks by their line counts."""
    out = subprocess.run(["git", "-c", "core.quotepath=off", "diff", "-U0", "--no-color", "--no-ext-diff",
                          "--diff-filter=d", f"{base}...HEAD"],
                         capture_output=True, text=True, errors="replace", check=True).stdout
    path, old_left, new_left = None, 0, 0
    for raw in out.splitlines():
        if old_left > 0 or new_left > 0:
            if raw.startswith("+"):
                new_left -= 1
                yield path, raw[1:], True
            elif raw.startswith("-"):
                old_left -= 1
                yield path, raw[1:], False
            continue
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else None
        else:
            m = HUNK.match(raw)
            if m:
                old_left = int(m.group(1) or 1)
                new_left = int(m.group(2) or 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=int, default=1000, help="max effective added lines in the PR")
    ap.add_argument("--base", required=True)
    ap.add_argument("--no-fail", action="store_true", help="report only; always exit 0")
    args = ap.parse_args()

    added, removed, per_file = [], 0, {}
    for path, line, is_add in diff_lines(args.base):
        ext = os.path.splitext(path)[1].lower()
        if ext in SKIP_EXT or path.startswith(".github/workflows/"):
            continue
        eff = effective(line, ext)
        if not eff:
            continue
        if is_add:
            added.append(len(eff))
            per_file[path] = per_file.get(path, 0) + 1
        else:
            removed += 1

    total = len(added)
    over = total > args.threshold
    out = ["## PR Effective Size Report", "",
           "Counts added lines only; comments, blank lines and Markdown/JSON/binary files excluded.", "",
           f"- Effective added lines: **{total}** (limit {args.threshold})",
           f"- Effective removed lines: {removed}",
           f"- Net: {total - removed:+d}",
           f"- Files touched: {len(per_file)}"]
    if added:
        out.append(f"- Average effective line length: {statistics.mean(added):.1f}")
        out += ["", "Largest files:", "", "| File | Added lines |", "|---|---|"]
        out += [f"| {f} | {n} |" for f, n in sorted(per_file.items(), key=lambda x: -x[1])[:10]]
    out += ["", f"**FAIL**: PR exceeds {args.threshold} effective lines; please split it." if over
            else "**PASS**: within limit."]
    report = "\n".join(out)
    print(report)
    if over:
        print(f"::error::PR has {total} effective added lines, above the limit of {args.threshold}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report + "\n")
    return 1 if over and not args.no_fail else 0


if __name__ == "__main__":
    sys.exit(main())
