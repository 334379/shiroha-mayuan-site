import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GeneratedAssetsTests(unittest.TestCase):
    def test_index_contains_only_mayuan_and_xsd(self):
        index = json.loads((ROOT / "data" / "banks-index.json").read_text(encoding="utf-8"))
        ids = [item["id"] for item in index]
        self.assertTrue(ids)
        self.assertTrue(all(item.startswith(("mayuan", "xsd")) for item in ids))
        self.assertFalse(any(item.startswith("c1") for item in ids))
        self.assertEqual(9, sum(item.startswith("mayuan") for item in ids))
        self.assertEqual(19, sum(item.startswith("xsd") for item in ids))

    def test_counts_and_chapter_sum_match(self):
        index = json.loads((ROOT / "data" / "banks-index.json").read_text(encoding="utf-8"))
        by_id = {item["id"]: item for item in index}
        chapter_sum = 0
        for item in index:
            payload = json.loads((ROOT / item["file"]).read_text(encoding="utf-8"))
            self.assertEqual(item["count"], len(payload["questions"]), item["id"])
            if item["id"].startswith("xsd-chapter"):
                chapter_sum += len(payload["questions"])
        self.assertEqual(by_id["xsd-full"]["count"], chapter_sum)
        self.assertEqual(751, by_id["xsd-full"]["count"])

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
        self.assertNotIn("C1驾照", (ROOT / "question-bank.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
