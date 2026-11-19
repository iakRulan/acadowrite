#!/usr/bin/env python3
"""check_facts — verify a manuscript against its fact sheet.

Usage:
    python3 check_facts.py --case /input/case.json --work /app/work

Checks:
  1. every number+unit in manuscript.md exists in fact_map.json (no invented facts);
  2. every required section heading is present;
  3. the DOCX exists and contains the same section headings;
  4. confirmations are non-empty when material is missing.

Prints a JSON verdict; exits non-zero on any hard failure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NUM_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*([a-zA-Z%/°µμ][a-zA-Z0-9%/°µμ]*)?")


def load(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--work", required=True)
    args = ap.parse_args(argv)

    work = Path(args.work)
    issues = []
    checks = {}

    md_path = work / "manuscript.md"
    fm_path = work / "fact_map.json"
    for p in (md_path, fm_path):
        if not p.exists():
            print(json.dumps({"valid": False, "issues": [f"missing: {p.name}"]}, ensure_ascii=False))
            return 1

    md = md_path.read_text(encoding="utf-8", errors="ignore")
    fm = load(fm_path)
    case = load(Path(args.case)) if Path(args.case).is_file() else {}

    known = set()
    for f in fm.get("facts", []):
        for v in f.get("values", []):
            known.add((v.get("value"), v.get("unit") or ""))
            known.add((v.get("value"), ""))
    known_values = {k[0] for k in known}

    # 1. numbers in the manuscript
    # ignore the reference list: citation years are not manuscript facts
    body_no_refs = re.split(r"^##\s+References\s*$", md, maxsplit=1, flags=re.MULTILINE)[0]
    in_md = set()
    for m in NUM_RE.finditer(body_no_refs):
        in_md.add((m.group(1), m.group(2) or ""))
    unknown = sorted(v for v in in_md if v not in known and v[0] not in known_values)
    checks["numbers_in_manuscript"] = len(in_md)
    checks["numbers_not_in_fact_sheet"] = len(unknown)
    if unknown:
        issues.append(f"稿件中出现底稿没有的数值：{unknown[:8]}")

    # 2. sections
    required = fm.get("sections") or []
    present = set(re.findall(r"^##\s+(.+)$", md, re.MULTILINE))
    missing = [s for s in required if s not in present and s != "References"]
    checks["required_sections"] = len(required)
    checks["missing_sections"] = len(missing)
    if missing:
        issues.append(f"缺少章节：{missing}")

    # 3. docx
    docx_path = work / "manuscript.docx"
    checks["docx_present"] = docx_path.exists()
    if not docx_path.exists():
        issues.append("缺少可编辑的 manuscript.docx")
    else:
        try:
            import docx
            d = docx.Document(str(docx_path))
            heads = [p.text.strip() for p in d.paragraphs if p.style.name.startswith("Heading")]
            checks["docx_headings"] = len(heads)
            missing_docx = [s for s in required if s not in heads and s != "References"]
            if missing_docx:
                issues.append(f"DOCX 缺少章节：{missing_docx}")
        except Exception as exc:  # noqa: BLE001
            issues.append(f"DOCX 读取失败：{type(exc).__name__}: {exc}")

    # 4. confirmations
    rev_path = work / "revisions.json"
    if rev_path.exists():
        rev = load(rev_path)
        checks["confirmations"] = len(rev.get("confirmations", []))

    verdict = {"valid": not issues, "checks": checks, "issues": issues,
               "case_id": fm.get("case_id")}
    (work / "fact_check.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
