import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GeneratedAssetsTests(unittest.TestCase):
    def test_index_contains_packaged_banks(self):
        index = json.loads((ROOT / "data" / "banks-index.json").read_text(encoding="utf-8"))
        ids = [item["id"] for item in index]
        self.assertEqual(["interchange-full", "fluid-mechanics-full"], ids)

    def test_counts_match_payloads(self):
        index = json.loads((ROOT / "data" / "banks-index.json").read_text(encoding="utf-8"))
        for item in index:
            payload = json.loads((ROOT / item["file"]).read_text(encoding="utf-8"))
            self.assertEqual(item["count"], len(payload["questions"]), item["id"])
        self.assertEqual(2, len(index))

    def test_questions_are_valid(self):
        index = json.loads((ROOT / "data" / "banks-index.json").read_text(encoding="utf-8"))
        seen = set()
        for item in index:
            payload = json.loads((ROOT / item["file"]).read_text(encoding="utf-8"))
            for question in payload["questions"]:
                self.assertNotIn(question["id"], seen)
                seen.add(question["id"])
                self.assertIn(question["type"], {"single", "multiple", "judge", "blank", "short", "material", "essay"})
                self.assertTrue(question["question"].strip())
                if question["type"] in {"single", "multiple", "judge"}:
                    keys = {option["key"] for option in question["options"]}
                    if question.get("answerPending"):
                        self.assertFalse(question["answerKeys"], question["id"])
                    else:
                        self.assertTrue(question["answerKeys"], question["id"])
                        self.assertTrue(set(question["answerKeys"]).issubset(keys), question["id"])
                if question["type"] in {"material", "essay"}:
                    self.assertTrue(question["answerKeys"], question["id"])
                    self.assertFalse(question.get("score"), question["id"])

    def test_preload_and_backup_match_index(self):
        index = json.loads((ROOT / "data" / "banks-index.json").read_text(encoding="utf-8"))
        qb = (ROOT / "question-bank.js").read_text(encoding="utf-8")
        match = re.search(r"window\.shirohaPreloadedBanks\s*=\s*(\[.*\]);", qb, re.S)
        self.assertIsNotNone(match)
        preloaded = json.loads(match.group(1))
        backup = json.loads((ROOT / "shiroha-all-banks-backup.json").read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in index], [item["id"] for item in preloaded])
        self.assertEqual([item["id"] for item in index], [item["id"] for item in backup["banks"]])

    def test_c1_data_removed(self):
        self.assertFalse((ROOT / "data" / "c1-full.json").exists())
        self.assertNotIn("C1", (ROOT / "question-bank.js").read_text(encoding="utf-8"))

    def test_interchange_bank_imported_from_latest_docx(self):
        index = json.loads((ROOT / "data" / "banks-index.json").read_text(encoding="utf-8"))
        item = next(entry for entry in index if entry["id"] == "interchange-full")
        self.assertEqual(49, item["count"])
        payload = json.loads((ROOT / item["file"]).read_text(encoding="utf-8"))
        self.assertEqual(49, payload["meta"]["questionCount"])
        singles = [question for question in payload["questions"] if question["type"] == "single"]
        blanks = [question for question in payload["questions"] if question["type"] == "blank"]
        self.assertEqual(19, len(singles))
        self.assertEqual(30, len(blanks))
        self.assertEqual(["A"], singles[0]["answerKeys"])
        self.assertIn("基础", singles[0]["question"])
        for question in singles:
            self.assertFalse(question.get("answerPending"))
            self.assertTrue(question["answerKeys"])
            self.assertEqual(4, len(question["options"]))
        for question in blanks:
            self.assertFalse(question.get("answerPending"))
            self.assertTrue(question["answerKeys"])

    def test_fluid_mechanics_bank_imported_from_docx(self):
        index = json.loads((ROOT / "data" / "banks-index.json").read_text(encoding="utf-8"))
        item = next(entry for entry in index if entry["id"] == "fluid-mechanics-full")
        self.assertEqual(35, item["count"])
        payload = json.loads((ROOT / item["file"]).read_text(encoding="utf-8"))
        self.assertEqual(35, payload["meta"]["questionCount"])
        singles = [question for question in payload["questions"] if question["type"] == "single"]
        blanks = [question for question in payload["questions"] if question["type"] == "blank"]
        self.assertEqual(22, len(singles))
        self.assertEqual(13, len(blanks))
        self.assertEqual(["A"], singles[0]["answerKeys"])
        self.assertEqual(["A"], singles[-1]["answerKeys"])
        self.assertEqual(4, len(singles[0]["options"]))
        for question in blanks:
            self.assertTrue(question["answerPending"])
            self.assertEqual([], question["answerKeys"])

    def test_packaged_bank_replaces_old_local_banks(self):
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        sw = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        self.assertIn("PACKAGED_BANK_REPLACE_MODE=true", app)
        self.assertIn("state.banks=next", app)
        self.assertIn("state.banks = banks.map", index)
        self.assertIn("quiz-20260707-edit-answer-fix", index)
        self.assertIn("quiz-20260707-edit-answer-fix", sw)

    def test_editor_saves_blank_answers_as_text(self):
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("splitAnswerByType($('#edit-answer').value,type)", app)
        self.assertIn("q.answer||q.answerKeys||q.answerText", app)


if __name__ == "__main__":
    unittest.main()
