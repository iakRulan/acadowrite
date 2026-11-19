---
name: acadowrite
description: "Produce an editable, source-mapped academic manuscript: read the fact sheet and format constraints, generate/rewrite/structure the required sections, map every number and claim back to the fact sheet, and emit Markdown + DOCX plus a fact map, a revision/confirmation list and a consistency check. Trigger on: '学术写作', '论文写作', '改稿', '校对', '润色结构', 'academic writing', 'manuscript draft', 'rewrite this paper', 'write the results section'. Not for: literature review, figure drawing, or journal submission typesetting."
---

# acadowrite — Source-mapped Academic Manuscript Writing

Produce a manuscript that is **editable and fact-true**: every number, unit and claim traces to the supplied fact sheet, missing material becomes an explicit placeholder instead of an invention, and the output is both Markdown and Word. The failure mode this skill exists to prevent: a polished draft with numbers the model made up, citations that don't support their sentence, missing sections, and no way to keep editing.

**Method in one line:** extract facts from the 底稿 → fill/rewrite the required sections → map each fact to its source sentence → emit Markdown + DOCX → run a consistency check that rejects any number not in the fact sheet.

## When to use

- Input: a case file (default `/input/case.json`) with the fact sheet (底稿), task type (`generate`/`rewrite`/`proofread`/`structure`), audience/style/format constraints, required sections, references and an optional draft.
- Output: under `/app/output` — `manuscript.md`, `manuscript.docx`, `fact_map.json`, `revisions.json`, `fact_check.json`, `result.json`.

## Pipeline (run in order)

### Phase 1 — Draft

```bash
python3 scripts/write.py --case /input/case.json --work /app/work
```

- **Extract facts**: one fact per sentence, carrying every number+unit in it, with the source sentence. No fact without a number/unit is treated as a "fact" (prose goes to the model).
- **Generate or rewrite**: `generate` fills the required sections from the fact sheet (facts distributed by keyword; unplaced facts go to Results); `rewrite`/`proofread` keep the draft's prose and apply style/format.
- **Missing material → placeholder**: a section with no supporting material gets `本节内容需依据底稿补充…` plus a confirmation item. Never invented content.
- **References** are rendered under the References section when present.
- Writes `manuscript.md` and an editable `manuscript.docx` (headings + bullets preserved).

### Phase 2 — Fact consistency check

```bash
python3 scripts/check_facts.py --case /input/case.json --work /app/work
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
python3 scripts/check_facts.py --case /input/case.json --work /app/work
python3 -c "import json;r=json.load(open('/app/work/result.json'));print(r['case_id'], r['status'], r['counts'])"
```

`valid: true` from the fact check is required for a `complete` status.
