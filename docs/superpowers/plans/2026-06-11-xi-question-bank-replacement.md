# Xi Question Bank Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bundled C1 and old Xi Jinping Thought banks with the supplied 2025-2026 Xi bank while retaining Marxism banks and adding correctly handled material-analysis and essay questions.

**Architecture:** A standalone Python builder parses normalized Word text into one combined bank and 18 chapter banks, validates every generated artifact, then rebuilds the index and preload bundles. The web app adds `material` and `essay` as subjective text types and excludes all subjective questions from automatic exam scoring.

**Tech Stack:** Python 3 standard library, `unittest`, vanilla JavaScript, JSON.

---

### Task 1: Parser and validator

**Files:**
- Create: `tools/build_xi_bank.py`
- Create: `tests/test_build_xi_bank.py`

- [ ] Write tests for section detection, inline answers, multiline options, judgments, material subquestions, essays, and validation errors.
- [ ] Run `python -m unittest tests.test_build_xi_bank -v` and confirm failures because the builder is absent.
- [ ] Implement parsing and validation with no site writes.
- [ ] Run the parser tests and confirm they pass.

### Task 2: Site subjective question behavior

**Files:**
- Modify: `app.js`
- Modify: `index.html`
- Create: `tests/test_subjective_exam_behavior.py`

- [ ] Write source-level behavior tests requiring `material` and `essay` labels, text-input handling, and exclusion from automatic exam scoring.
- [ ] Run the tests and confirm failures against the current app.
- [ ] Add the two types to normalization, filtering, editing, practice self-assessment, and exam result rendering.
- [ ] Make exam scoring use objective questions only while reporting pending subjective questions separately.
- [ ] Run the behavior tests and confirm they pass.

### Task 3: Generate replacement banks

**Files:**
- Modify: `data/banks-index.json`
- Replace: `data/xsd-full.json`
- Replace: `data/xsd-chapter1.json` through `data/xsd-chapter18.json`
- Delete: `data/c1-full.json`
- Modify: `question-bank.js`
- Modify: `shiroha-all-banks-backup.json`
- Create: `xi-import-report.json`

- [ ] Run the builder against `25-26-2习概题库(1).txt`.
- [ ] Review unresolved and suspicious records; improve parser rules instead of silently dropping valid questions.
- [ ] Require zero blocking errors before writing generated files.
- [ ] Confirm the index contains only `mayuan-*` and new `xsd-*` entries.

### Task 4: End-to-end verification

**Files:**
- Modify: `README.md`

- [ ] Document the bundled bank set and subjective scoring behavior.
- [ ] Run all Python tests.
- [ ] Run `node --check app.js` and `node --check question-bank.js`.
- [ ] Run the builder in `--check` mode against generated files.
- [ ] Verify JSON parsing, unique IDs, answer/option consistency, chapter sums, index counts, preload counts, and absence of C1 data.
- [ ] Inspect the final Git diff and confirm no Marxism question content changed.
