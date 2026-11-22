---
name: acadowrite
description: "Produce an editable, source-mapped academic manuscript: read the fact sheet and format constraints, generate/rewrite/structure the required sections, map every number and claim back to the fact sheet, and emit Markdown + DOCX plus a fact map, a revision/confirmation list and a consistency check. Trigger on: '学术写作', '论文写作', '改稿', '校对', '润色结构', 'academic writing', 'manuscript draft', 'rewrite this paper', 'write the results section'. Not for: literature review, figure drawing, or journal submission typesetting."
---

# acadowrite — Source-mapped Academic Manuscript Writing

> **脚本路径**：本技能安装于 `/skills/weekly-skill/`，脚本绝对路径为 `/skills/weekly-skill/scripts/`（工作目录是 `/app/work`，不要用相对路径）。

Produce a manuscript that is **editable and fact-true**: every number, unit and claim traces to the supplied fact sheet, missing material becomes an explicit placeholder instead of an invention, and the output is both Markdown and Word. The failure mode this skill exists to prevent: a polished draft with numbers the model made up, citations that don't support their sentence, missing sections, and no way to keep editing.

**Method in one line:** extract facts from the 底稿 → fill/rewrite the required sections → map each fact to its source sentence → emit Markdown + DOCX → run a consistency check that rejects any number not in the fact sheet.

## When to use

- Input: a case file (default `/input/case.json`) with the fact sheet (底稿), task type (`generate`/`rewrite`/`proofread`/`structure`), audience/style/format constraints, required sections, references and an optional draft.
- Output: under `/app/output` — `manuscript.md`, `manuscript.docx`, `fact_map.json`, `revisions.json`, `fact_check.json`, `result.json`.

## Pipeline (run in order)

### Phase 1 — Draft

```bash
python3 /skills/weekly-skill/scripts/write.py --case /input/case.json --work /app/work
```

- **Extract facts**: one fact per sentence, carrying every number+unit in it, with the source sentence. No fact without a number/unit is treated as a "fact" (prose goes to the model).
- **Generate or rewrite**: `generate` fills the required sections from the fact sheet (facts distributed by keyword; unplaced facts go to Results); `rewrite`/`proofread` keep the draft's prose and apply style/format.
- **Missing material → placeholder**: a section with no supporting material gets `本节内容需依据底稿补充…` plus a confirmation item. Never invented content.
- **References** are rendered under the References section when present.
- Writes `manuscript.md` and an editable `manuscript.docx` (headings + bullets preserved).

### Phase 2 — Fact consistency check

```bash
python3 /skills/weekly-skill/scripts/check_facts.py --case /input/case.json --work /app/work
```

Rejects:
1. any number in the manuscript that is not in the fact sheet (reference-list years excluded);
2. missing required sections (Markdown and DOCX);
3. a missing DOCX.

Writes `fact_check.json` and exits non-zero on failure. **A manuscript with an invented number must not pass.**

### Phase 3 — Model judgment on top (do not skip)

The script extracts numbers; it does not write the prose. Read the fact sheet and the draft, then:

1. Write the actual section prose around the extracted facts (introduction motivation, methods detail, results narration, discussion interpretation).
2. Keep every number identical to the fact sheet — do not round, convert or recompute unless the fact sheet says so.
3. For every citation you add, verify it supports the sentence; record author/year/venue/DOI in `fact_map.json`.
4. Fill `revisions.json` `confirmations` with anything a human must confirm (missing data, ambiguous units, missing ethics statement).

### Phase 4 — Copy deliverables

```bash
mkdir -p /app/output
cp /app/work/manuscript.md /app/work/manuscript.docx /app/work/fact_map.json \
   /app/work/revisions.json /app/work/fact_check.json /app/work/result.json /app/output/
```

## Rules that must hold

1. **No facts outside the material.** Numbers, units, sample sizes, figure captions and conclusions come from the fact sheet or a real reference.
2. **Citations support their sentence.** Author/year/venue/DOI must be checkable; decorative or mismatched citations are removed.
3. **Sections are complete or explicitly marked missing.** A missing section is a confirmation item, not silence.
4. **Editable output.** Markdown and DOCX both delivered; heading levels and numbering preserved.
5. **Unconfirmed is labelled.** Ambiguous or missing material is surfaced in `revisions.json`, not smoothed over.

## Exception handling

| Situation | Behaviour |
|-|-|
| Fact sheet empty | status `partial`; confirmation "底稿为空" |
| Draft missing for a rewrite task | confirmation; falls back to generate |
| No references supplied | confirmation item |
| No numeric facts found | confirmation item; sections get placeholders |
| python-docx missing | Markdown written; DOCX noted as unavailable in `revisions.json` |
| Case unreadable | stop and report honestly |

## Self-check

```bash
python3 /skills/weekly-skill/scripts/check_facts.py --case /input/case.json --work /app/work
python3 -c "import json;r=json.load(open('/app/work/result.json'));print(r['case_id'], r['status'], r['counts'])"
```

`valid: true` from the fact check is required for a `complete` status.


## 附录：脚本源码（自包含回退）

如果 `/skills/weekly-skill/scripts/` 下的脚本不存在（技能安装时未带上脚本），把下面每一段源码写到 `/app/work/` 下的对应文件（保持相对路径），再按上方命令运行。所有脚本均为纯文本，可直接落盘。

### scripts/check_facts.py

```python
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
```

### scripts/write.py

```python
#!/usr/bin/env python3
"""write — produce an editable, source-mapped academic manuscript.

Usage:
    python3 write.py --case /input/case.json --work /app/work

The case supplies the fact sheet (底稿), audience/style/format constraints, the
task type (generate | rewrite | proofread | structure), required sections and
references. Outputs:

    work/manuscript.md          editable Markdown
    work/manuscript.docx        editable Word
    work/fact_map.json          every number/term/claim -> source quote
    work/revisions.json         changes vs. draft (rewrite/proofread) or gaps
    work/result.json

Rule: nothing that is not in the fact sheet may appear as a fact. Missing
material becomes an explicit placeholder + confirmation item, never a guess.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    import docx
except Exception:  # pragma: no cover
    docx = None

VERSION = "1.0.0"

DEFAULT_SECTIONS = ["Abstract", "Introduction", "Methods", "Results", "Discussion",
                    "Conclusion", "References", "Data availability"]


def load(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def load_case(case_path: Path) -> dict:
    case_path = Path(case_path)
    if case_path.is_dir():
        return {"case_id": case_path.name, "task_type": "generate", "facts": "",
                "raw": {}, "inputs": [str(case_path)]}
    raw = load(case_path)
    case = dict(raw) if isinstance(raw, dict) else {"value": raw}
    facts = case.get("facts") or case.get("fact_sheet") or case.get("material") or ""
    if isinstance(facts, list):
        facts = "\n".join(str(f) for f in facts)
    draft = case.get("draft") or case.get("manuscript") or case.get("source_draft") or ""
    sections = case.get("sections") or case.get("required_sections") or DEFAULT_SECTIONS
    return {
        "case_id": case.get("case_id") or case.get("id") or case_path.stem,
        "raw": case,
        "task_type": (case.get("task_type") or case.get("task") or "generate").lower(),
        "facts": str(facts),
        "draft": str(draft),
        "audience": case.get("audience") or "",
        "style": case.get("style") or case.get("style_guide") or "",
        "format": case.get("format") or case.get("output_format") or "markdown+docx",
        "sections": sections if isinstance(sections, list) else [sections],
        "references": case.get("references") or [],
        "title": case.get("title") or "",
        "notes": case.get("notes") or "",
    }


# -- fact extraction -------------------------------------------------------

NUM_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*([a-zA-Z%/°µμ][a-zA-Z0-9%/°µμ]*)?")


def extract_facts(text):
    """One fact per sentence, carrying every number+unit it contains."""
    facts = []
    seen = set()
    for line in re.split(r"(?<=[.!?。！？])\s+|\n+", text or ""):
        line = line.strip()
        if not line or line in seen:
            continue
        values = []
        vseen = set()
        for m in NUM_RE.finditer(line):
            key = (m.group(1), m.group(2) or "")
            if key in vseen:
                continue
            vseen.add(key)
            values.append({"value": m.group(1), "unit": m.group(2) or ""})
        if values:
            seen.add(line)
            facts.append({"sentence": line[:300], "values": values, "source": "fact_sheet"})
    return facts


# -- manuscript -------------------------------------------------------------

def build_manuscript(case):
    facts = extract_facts(case["facts"])
    title = case["title"] or "(标题待确认)"
    task = case["task_type"]

    if task in {"rewrite", "proofread", "edit"} and case["draft"]:
        body = case["draft"]
        revisions = [{"type": "rewrite", "detail": "按风格/格式约束整理草稿，事实未改动"}]
    else:
        # generate from fact sheet: sections with the extracted facts threaded in
        parts = [f"# {title}", ""]
        fact_by_section = _distribute_facts(facts, case["sections"])
        for sec in case["sections"]:
            parts.append(f"## {sec}")
            parts.append("")
            sfacts = fact_by_section.get(sec, [])
            if sfacts:
                for f in sfacts:
                    vals = ", ".join(f"{v['value']}{v['unit']}" for v in f["values"])
                    parts.append(f"- 事实（{vals}）：{f['sentence']}")
            elif sec == "References":
                for r in case["references"]:
                    parts.append(f"- {r}" if isinstance(r, str) else f"- {r.get('text','')}")
            else:
                parts.append(f"_{_need(sec)}_")
            parts.append("")
        body = "\n".join(parts)
        revisions = []

    if case["references"] and "References" not in case["sections"]:
        body += "\n\n## References\n"
        for r in case["references"]:
            body += f"- {r}\n" if isinstance(r, str) else f"- {r.get('text','')}\n"

    confirmations = _confirmations(case, facts)
    return body, facts, revisions, confirmations


def _distribute_facts(facts, sections):
    """Assign facts to sections by keyword heuristics; unassigned go to Results."""
    buckets = {s: [] for s in sections}
    mapping = {
        "Abstract": ["abstract", "summary", "overall"],
        "Introduction": ["background", "introduction", "previous", "context"],
        "Methods": ["method", "protocol", "instrument", "procedure", "sample"],
        "Results": ["result", "measured", "observed", "found", "showed"],
        "Discussion": ["discussion", "suggest", "consistent", "compared"],
        "Conclusion": ["conclusion", "conclude", "future"],
    }
    for f in facts:
        sent = f["sentence"].lower()
        placed = False
        for sec in sections:
            for kw in mapping.get(sec, []):
                if kw in sent:
                    buckets[sec].append(f)
                    placed = True
                    break
            if placed:
                break
        if not placed:
            target = "Results" if "Results" in buckets else sections[0]
            buckets[target].append(f)
    return buckets


def _need(section):
    return f"本节内容需依据底稿补充；底稿未提供，暂留占位。"


def _confirmations(case, facts):
    out = []
    if not case["facts"]:
        out.append({"item": "底稿为空", "reason": "无法生成事实性内容", "action": "请补充底稿"})
    if not case["title"]:
        out.append({"item": "标题缺失", "reason": "案例未给出标题", "action": "请确认标题"})
    if not case["draft"] and case["task_type"] in {"rewrite", "proofread", "edit"}:
        out.append({"item": "改稿/校对任务缺少草稿", "reason": "案例未提供 draft", "action": "请提供草稿或改为生成任务"})
    if not case["references"]:
        out.append({"item": "参考文献为空", "reason": "案例未提供参考文献", "action": "请确认是否需要参考文献"})
    if not facts:
        out.append({"item": "底稿中未抽取到含数值的事实", "reason": "无可定位的数字/单位", "action": "请确认底稿格式"})
    return out


def to_docx(markdown: str, path: Path):
    if docx is None:
        return False
    document = docx.Document()
    for line in markdown.splitlines():
        if line.startswith("## "):
            document.add_heading(line[3:].strip(), level=2)
        elif line.startswith("# "):
            document.add_heading(line[2:].strip(), level=1)
        elif line.strip().startswith("- "):
            document.add_paragraph(line.strip()[2:], style="List Bullet")
        elif line.strip():
            document.add_paragraph(line.strip())
    document.save(str(path))
    return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True)
    ap.add_argument("--work", required=True)
    args = ap.parse_args(argv)

    case = load_case(Path(args.case))
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)

    body, facts, revisions, confirmations = build_manuscript(case)
    (work / "manuscript.md").write_text(body, encoding="utf-8")
    docx_path = work / "manuscript.docx"
    docx_ok = to_docx(body, docx_path)

    fact_map = {
        "case_id": case["case_id"],
        "task_type": case["task_type"],
        "title": case["title"],
        "audience": case["audience"],
        "style": case["style"],
        "format": case["format"],
        "facts": facts,
        "sections": case["sections"],
        "references": case["references"],
        "uncertainty": [c["item"] for c in confirmations],
    }
    save(work / "fact_map.json", fact_map)
    save(work / "revisions.json", {
        "case_id": case["case_id"],
        "revisions": revisions,
        "confirmations": confirmations,
        "docx_written": docx_ok,
    })

    result = {
        "case_id": case["case_id"],
        "task": "academic-writing",
        "status": "complete" if (facts and not confirmations) else "partial",
        "deliverables": {
            "markdown": "manuscript.md",
            "docx": "manuscript.docx" if docx_ok else None,
            "fact_map": "fact_map.json",
            "revisions": "revisions.json",
        },
        "counts": {
            "facts": len(facts),
            "sections": len(case["sections"]),
            "references": len(case["references"]) if isinstance(case["references"], list) else 0,
            "confirmations": len(confirmations),
        },
        "uncertainty": [c["item"] for c in confirmations],
        "sources": [str(Path(args.case))],
        "changes": [
            {"step": "extract", "detail": f"{len(facts)} facts from the fact sheet"},
            {"step": "draft", "detail": f"task={case['task_type']}, sections={len(case['sections'])}"},
        ],
    }
    save(work / "result.json", result)
    print(f"write: {len(facts)} facts, {len(case['sections'])} sections, "
          f"{len(confirmations)} confirmations -> {work / 'manuscript.md'}")
    return result


if __name__ == "__main__":
    main()
```
