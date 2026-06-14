from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from collections import OrderedDict
from pathlib import Path
from typing import Iterable


OPTION_KEYS = "ABCDEFG"
CHAPTER_RE = re.compile(r"^(导论|第[一二三四五六七八九十百0-9]+章(?:\s+.*)?)$")
NUMBERED_RE = re.compile(r"^\s*(\d{1,3})\s*[.．、]\s*(.+)$")
SUBQUESTION_RE = re.compile(r"^\s*[（(](\d{1,2})[）)]\s*(.+)$")
ANSWER_LINE_RE = re.compile(r"^\s*(?:正确答案|参考答案|答案)\s*[:：;；]?\s*([A-G]+|[√✓✔×XxVvFf]|正确|错误|对|错)?\s*$")
REFERENCE_RE = re.compile(r"^\s*参考答案(?:要点)?\s*[:：]?\s*(.*)$")
OPTION_MARK_RE = re.compile(r"(?<![A-Za-z])([A-G])(?:\s*[.．、]\s*|\s+(?=\S)|(?=[\u3400-\u9fff]))")
EMBEDDED_ANSWER_RE = re.compile(r"[（(]\s*([A-G]{1,7}|[√✓✔×XxVvFf]|正确|错误|对|错)\s*[.。]?\s*[）)]")
ANSWER_POINT_RE = re.compile(r"^(?:[①②③④⑤⑥⑦⑧⑨⑩]|第[一二三四五六七八九十]+[，、.]|[一二三四五六七八九十]+是)")
SOURCE_ANSWER_OVERRIDES = {
    "“十四个坚持”的基本方略": ["A", "B", "C", "D"],
    "生态文明建设战略地位更加凸显": ["A", "B", "C"],
}


def clean(value: str) -> str:
    value = value.replace("\u00a0", " ").replace("\u3000", " ")
    return re.sub(r"[ \t]+", " ", value).strip()


def normalized_lines(text: str) -> list[str]:
    return [clean(line) for line in text.replace("\x0b", "\n").splitlines() if clean(line)]


def section_type(line: str) -> str | None:
    compact = re.sub(r"\s+", "", line)
    if len(compact) > 24:
        return None
    if "材料分析题" in compact:
        return "material"
    if "论述题" in compact:
        return "essay"
    if "判断题" in compact:
        return "judge"
    if "多项选择题" in compact or "多选题" in compact:
        return "multiple"
    if "单项选择题" in compact or "单选题" in compact:
        return "single"
    return None


def normalize_answer(value: str) -> list[str]:
    compact = re.sub(r"[^A-G√✓✔×XxVvFf正确错误对错]", "", value or "").upper()
    if compact in {"√", "✓", "✔", "V", "T", "正确", "对"}:
        return ["A"]
    if compact in {"×", "X", "F", "错误", "错"}:
        return ["B"]
    if re.fullmatch(r"[A-G]+", compact):
        return list(dict.fromkeys(compact))
    return []


def extract_embedded_answer(text: str) -> tuple[str, list[str]]:
    labeled = re.search(r"\s*(?:正确答案|参考答案|答案)\s*[:：;；]\s*([A-G]+|[√✓✔×XxVvFf])\s*$", text)
    if labeled:
        answer = normalize_answer(labeled.group(1))
        if answer:
            return clean(text[: labeled.start()]), answer
    matches = list(EMBEDDED_ANSWER_RE.finditer(text))
    for match in reversed(matches):
        answer = normalize_answer(match.group(1))
        if answer:
            stem = clean(text[: match.start()] + "（ ）" + text[match.end() :])
            return stem, answer
    trailing = re.search(r"[:：]\s*([A-G]{1,7})[.。]?\s*$", text)
    if trailing:
        answer = normalize_answer(trailing.group(1))
        if answer:
            return clean(text[: trailing.start()] + "。"), answer
    return text, []


def split_options(text: str) -> tuple[str, dict[str, str]]:
    matches = list(OPTION_MARK_RE.finditer(text))
    if not matches:
        return text, {}
    before = clean(text[: matches[0].start()])
    options: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        options[match.group(1).upper()] = clean(text[start:end])
    return before, options


def make_question(
    chapter: str,
    qtype: str,
    question: str,
    options: dict[str, str] | None,
    answer: list[str] | None,
    answer_text: str = "",
) -> dict:
    option_rows = [{"key": key, "text": clean(value)} for key, value in (options or {}).items() if clean(value)]
    option_map = {row["key"]: row["text"] for row in option_rows}
    answers = list(answer or [])
    if qtype == "judge":
        option_rows = [{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}]
        option_map = {"A": "正确", "B": "错误"}
    reference = clean(answer_text)
    if qtype in {"material", "essay"} and reference:
        answers = [reference]
    return {
        "type": qtype,
        "typeLabel": {
            "single": "单选题",
            "multiple": "多选题",
            "judge": "判断题",
            "material": "材料分析题",
            "essay": "论述题",
        }[qtype],
        "question": clean(question),
        "options": option_rows,
        "answerKeys": answers,
        "answerText": [reference] if reference else [option_map[key] for key in answers if key in option_map],
        "topic": chapter,
        "category": chapter,
        "score": 0 if qtype in {"material", "essay"} else 1,
        "analysis": "",
    }


def parse_objective(lines: list[str], start: int, chapter: str, qtype: str) -> tuple[list[dict], int]:
    questions: list[dict] = []
    current: dict | None = None
    index = start

    def finish() -> None:
        nonlocal current
        if current:
            questions.append(
                make_question(
                    chapter,
                    qtype,
                    current["question"],
                    current["options"],
                    current["answer"],
                )
            )
        current = None

    while index < len(lines):
        line = lines[index]
        if CHAPTER_RE.match(line) or section_type(line):
            break
        answer_match = ANSWER_LINE_RE.match(line)
        numbered = NUMBERED_RE.match(line)
        is_unnumbered_judge = qtype == "judge" and not numbered and EMBEDDED_ANSWER_RE.search(line)
        if numbered or is_unnumbered_judge:
            finish()
            stem = numbered.group(2) if numbered else line
            stem, embedded = extract_embedded_answer(stem)
            stem, inline = split_options(stem)
            current = {"question": stem, "options": inline, "answer": embedded}
            index += 1
            continue
        if answer_match and current:
            parsed_answer = normalize_answer(answer_match.group(1) or "")
            if parsed_answer:
                current["answer"] = parsed_answer
            index += 1
            continue
        if not current:
            index += 1
            continue
        before, options = split_options(line)
        if options:
            if before:
                if not current["options"] and "A" not in options and min(options) > "A":
                    current["options"]["A"] = before
                else:
                    current["question"] = clean(current["question"] + " " + before)
            current["options"].update(options)
        elif qtype != "judge":
            current["question"] = clean(current["question"] + " " + line)
        else:
            stem, embedded = extract_embedded_answer(line)
            current["question"] = clean(current["question"] + " " + stem)
            if embedded:
                current["answer"] = embedded
        index += 1
    finish()
    return questions, index


def parse_material(lines: list[str], start: int, chapter: str) -> tuple[list[dict], int]:
    questions: list[dict] = []
    index = start
    shared: list[str] = []
    prompt = ""
    answer: list[str] = []
    reading_answer = False

    def finish_subquestion() -> None:
        nonlocal prompt, answer, reading_answer
        if prompt:
            full_prompt = "\n".join([*shared, prompt]) if shared else prompt
            questions.append(make_question(chapter, "material", full_prompt, {}, [], "\n".join(answer)))
        prompt = ""
        answer = []
        reading_answer = False

    while index < len(lines):
        line = lines[index]
        if CHAPTER_RE.match(line) or section_type(line) == "essay":
            break
        sub = SUBQUESTION_RE.match(line)
        ref = REFERENCE_RE.match(line)
        numbered = NUMBERED_RE.match(line)
        if numbered and re.search(r"根据以下材料|根据材料|阅读材料", numbered.group(2)):
            finish_subquestion()
            shared = [numbered.group(2)]
        elif sub:
            finish_subquestion()
            prompt = sub.group(2)
        elif ref and prompt:
            reading_answer = True
            if ref.group(1):
                answer.append(ref.group(1))
        elif prompt and not reading_answer and ANSWER_POINT_RE.match(line):
            reading_answer = True
            answer.append(line)
        elif prompt and reading_answer:
            answer.append(line)
        elif prompt:
            prompt = clean(prompt + " " + line)
        else:
            shared.append(line)
        index += 1
    finish_subquestion()
    return questions, index


def parse_essays(lines: list[str], start: int, chapter: str) -> tuple[list[dict], int]:
    questions: list[dict] = []
    index = start
    prompt = ""
    answer: list[str] = []

    def finish() -> None:
        nonlocal prompt, answer
        if prompt:
            questions.append(make_question(chapter, "essay", prompt, {}, [], "\n".join(answer)))
        prompt = ""
        answer = []

    while index < len(lines):
        line = lines[index]
        if CHAPTER_RE.match(line) or (section_type(line) and section_type(line) != "essay"):
            break
        numbered = NUMBERED_RE.match(line)
        if numbered:
            finish()
            prompt = numbered.group(2)
        elif prompt:
            answer.append(line)
        index += 1
    finish()
    return questions, index


def build_report(chapters: OrderedDict[str, list[dict]]) -> dict:
    issues: list[dict] = []
    corrections: list[dict] = []
    seen: dict[str, str] = {}
    for chapter, questions in chapters.items():
        for question in questions:
            stem = question["question"]
            qtype = question["type"]
            for marker, answer in SOURCE_ANSWER_OVERRIDES.items():
                if marker in stem and question["answerKeys"] != answer:
                    corrections.append(
                        {
                            "chapter": chapter,
                            "question": stem,
                            "originalAnswer": question["answerKeys"],
                            "correctedAnswer": answer,
                        }
                    )
                    question["answerKeys"] = answer
                    option_map = {option["key"]: option["text"] for option in question["options"]}
                    question["answerText"] = [option_map[key] for key in answer if key in option_map]
                    break
            if not stem:
                issues.append({"severity": "error", "chapter": chapter, "question": stem, "message": "题干为空"})
            if qtype in {"single", "multiple", "judge"}:
                keys = {option["key"] for option in question["options"]}
                if not question["answerKeys"]:
                    issues.append({"severity": "error", "chapter": chapter, "question": stem, "message": "客观题缺少答案"})
                elif any(key not in keys for key in question["answerKeys"]):
                    issues.append({"severity": "error", "chapter": chapter, "question": stem, "message": "答案引用了不存在的选项"})
                if qtype != "judge" and len(keys) < 2:
                    issues.append({"severity": "error", "chapter": chapter, "question": stem, "message": "选择题选项不足"})
            elif not question["answerText"] or not question["answerText"][0]:
                issues.append({"severity": "error", "chapter": chapter, "question": stem, "message": "主观题缺少参考答案"})
            duplicate_key = re.sub(r"\s+", "", stem)
            if duplicate_key in seen:
                issues.append(
                    {
                        "severity": "warning",
                        "chapter": chapter,
                        "question": stem,
                        "message": f"疑似重复题，首次出现于{seen[duplicate_key]}",
                    }
                )
            else:
                seen[duplicate_key] = chapter
    return {
        "blockingErrors": sum(item["severity"] == "error" for item in issues),
        "warnings": sum(item["severity"] == "warning" for item in issues),
        "issues": issues,
        "sourceCorrections": corrections,
        "chapters": {chapter: len(questions) for chapter, questions in chapters.items()},
        "totalQuestions": sum(len(questions) for questions in chapters.values()),
    }


def parse_text(text: str) -> tuple[OrderedDict[str, list[dict]], dict]:
    lines = normalized_lines(text)
    chapters: OrderedDict[str, list[dict]] = OrderedDict()
    chapter = "导论"
    chapters[chapter] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        chapter_match = CHAPTER_RE.match(line)
        if chapter_match:
            chapter = clean(chapter_match.group(1))
            chapters.setdefault(chapter, [])
            index += 1
            continue
        qtype = section_type(line)
        if not qtype:
            index += 1
            continue
        index += 1
        if qtype in {"single", "multiple", "judge"}:
            parsed, index = parse_objective(lines, index, chapter, qtype)
        elif qtype == "material":
            parsed, index = parse_material(lines, index, chapter)
        else:
            parsed, index = parse_essays(lines, index, chapter)
        chapters[chapter].extend(parsed)
    report = build_report(chapters)
    return chapters, report


def validate_chapters(chapters: OrderedDict[str, list[dict]], report: dict) -> None:
    if report["blockingErrors"]:
        raise ValueError(f"题库存在 {report['blockingErrors']} 个阻断错误")
    if len(chapters) != 18:
        raise ValueError(f"应识别 18 个章节，实际为 {len(chapters)}")
    if not all(chapters.values()):
        raise ValueError("存在空章节")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def clone_question(question: dict, bank_id: str, number: int) -> dict:
    q = json.loads(json.dumps(question, ensure_ascii=False))
    q["id"] = f"{bank_id}-{number:04d}"
    q["number"] = number
    q["volume"] = 1
    return q


def bank_entry(bank_id: str, name: str, filename: str, questions: list[dict]) -> dict:
    return {
        "id": bank_id,
        "name": name,
        "count": len(questions),
        "file": f"data/{filename}",
        "description": "由 25-26-2 习概题库 Word 文档转换导入，含客观题、材料分析题和论述题。",
    }


def bank_payload(title: str, questions: list[dict]) -> dict:
    return {
        "meta": {
            "title": title,
            "questionCount": len(questions),
            "volumes": 1,
            "sourceNote": "由 25-26-2 习概题库 Word 文档转换导入，主观题供自评。",
        },
        "questions": questions,
    }


def backup_question(question: dict) -> dict:
    return {
        "id": question["id"],
        "type": question["type"].upper(),
        "number": question["number"],
        "volume": question.get("volume", ""),
        "question": question["question"],
        "options": question.get("options", []),
        "answer": question.get("answerKeys", []),
        "analysis": question.get("analysis", ""),
        "category": question.get("category", ""),
        "score": question.get("score"),
    }


def write_site(root: Path, chapters: OrderedDict[str, list[dict]], report: dict) -> dict:
    validate_chapters(chapters, report)
    data_dir = root / "data"
    index_path = data_dir / "banks-index.json"
    old_index = json.loads(index_path.read_text(encoding="utf-8"))
    kept = [item for item in old_index if str(item["id"]).startswith("mayuan")]
    entries = list(kept)
    full_questions: list[dict] = []
    chapter_payloads: list[tuple[dict, list[dict]]] = []
    title = "习近平新时代中国特色社会主义思想概论"

    for _, questions in chapters.items():
        full_questions.extend(questions)
    full_questions = [clone_question(q, "xsd-full", i + 1) for i, q in enumerate(full_questions)]
    entries.append(bank_entry("xsd-full", title, "xsd-full.json", full_questions))
    (data_dir / "xsd-full.json").write_text(
        json.dumps(bank_payload(title, full_questions), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for idx, (chapter, questions) in enumerate(chapters.items(), 1):
        bank_id = f"xsd-chapter{idx}"
        chapter_questions = [clone_question(q, bank_id, i + 1) for i, q in enumerate(questions)]
        short = "导论" if chapter == "导论" else chapter.split()[0]
        name = f"{title}-{short}"
        filename = f"{bank_id}.json"
        entries.append(bank_entry(bank_id, name, filename, chapter_questions))
        chapter_payloads.append((entries[-1], chapter_questions))
        (data_dir / filename).write_text(
            json.dumps(bank_payload(name, chapter_questions), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    for path in data_dir.glob("c1-*.json"):
        path.unlink()
    index_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")

    preloaded = []
    for item in entries:
        payload = json.loads((root / item["file"]).read_text(encoding="utf-8"))
        group = "马原" if item["id"].startswith("mayuan") else "习概"
        preloaded.append(
            {
                "id": item["id"],
                "name": item["name"],
                "groupName": group,
                "createdAt": "2026-06-11T00:00:00.000Z",
                "updatedAt": "2026-06-11T00:00:00.000Z",
                "questions": [backup_question(q) for q in payload["questions"]],
            }
        )

    qb_path = root / "question-bank.js"
    qb_text = qb_path.read_text(encoding="utf-8")
    qb_text = re.sub(
        r"window\.questionBankIndex\s*=\s*\[[\s\S]*?\];",
        "window.questionBankIndex = " + json.dumps(entries, ensure_ascii=False, separators=(",", ":")) + ";",
        qb_text,
        count=1,
    )
    qb_text = re.sub(
        r"window\.questionBank\s*=\s*\{[\s\S]*?\};\s*\nwindow\.shirohaPreloadedBanks",
        "window.questionBank = {\"meta\":{\"title\":\"内置题库（按需加载）\",\"questionCount\":0,\"volumes\":1},\"questions\":[]};\nwindow.shirohaPreloadedBanks",
        qb_text,
        count=1,
    )
    marker = "\nwindow.shirohaPreloadedBanks = "
    if marker in qb_text:
        qb_text = qb_text.split(marker)[0]
    qb_text += marker + json.dumps(preloaded, ensure_ascii=False, separators=(",", ":")) + ";\n"
    qb_text = qb_text.replace("内置 C1 题库作为默认初始题库", "内置马原与习概题库作为默认初始题库")
    qb_text = qb_text.replace("保留 data/c1-full.json 作为独立数据源", "移除 C1 题库数据源")
    qb_path.write_text(qb_text, encoding="utf-8")

    backup = {
        "app": "Shiroha Quiz",
        "appVersion": "V33富文本导入优化版",
        "schemaVersion": 1,
        "richContentVersion": "shiroha-web-rich-v1",
        "richContentCapabilities": {},
        "exportType": "selected_banks",
        "exportedAt": now(),
        "banks": preloaded,
        "wrongBook": {},
        "favorites": {},
        "records": [],
        "settings": {},
        "activeBankId": preloaded[0]["id"] if preloaded else "",
    }
    (root / "shiroha-all-banks-backup.json").write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"indexCount": len(entries), "preloadedCount": len(preloaded), "fullCount": len(full_questions)}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-site", type=Path)
    args = parser.parse_args(argv)
    chapters, report = parse_text(args.source.read_text(encoding="utf-8"))
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.write_site:
        report["writeResult"] = write_site(args.write_site, chapters, report)
        if args.report:
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "issues"}, ensure_ascii=False, indent=2))
    if args.check:
        validate_chapters(chapters, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
