import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class SubjectiveExamBehaviorTests(unittest.TestCase):
    def test_material_and_essay_have_labels(self):
        self.assertIn("material:'材料分析题'", APP)
        self.assertIn("essay:'论述题'", APP)

    def test_material_and_essay_are_text_types(self):
        match = re.search(r"function isTextType\(t\)\{([^}]+)\}", APP)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("material", body)
        self.assertIn("essay", body)

    def test_question_type_normalization_preserves_subjective_types(self):
        self.assertRegex(APP, r"value==='material'.+return'material'")
        self.assertRegex(APP, r"value==='essay'.+return'essay'")

    def test_exam_scoring_excludes_subjective_questions(self):
        self.assertIn("isSubjectiveType(q.type)", APP)
        self.assertIn("pendingSubjective", APP)
        self.assertIn("待自评主观题", APP)

    def test_filters_and_editor_expose_new_types(self):
        self.assertIn('<option value="material">材料分析</option>', INDEX)
        self.assertIn('<option value="essay">论述</option>', INDEX)


if __name__ == "__main__":
    unittest.main()
