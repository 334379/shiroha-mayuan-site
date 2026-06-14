import unittest

from tools.build_xi_bank import parse_text, validate_chapters


SAMPLE = """导论
一、单选题
1.改革开放以来的鲜明主题是（ ）。
A.发展 B.坚持和发展中国特色社会主义 C.开放 D.创新
答案：B
二、多选题
1.主要内容包括（ ABCD ）。
A.十个明确
B.十四个坚持
C.十三个方面成就
D.六个必须坚持
2.缺少答案的题目（ ）。
A.甲
B.乙
三、判断题
1.这是正确表述。（ √ ）
第一章 新时代坚持和发展中国特色社会主义
一、单项选择题
1.中国特色社会主义道路是（ A）。
A.实现途径 B.行动指南 C.根本保障 D.精神力量
三、判断题
中华民族已经走出社会主义初级阶段。（×）
第十七章 全面从严治党
一、材料分析题
1.根据以下材料，请回答：
材料一：人民监督和自我革命共同构成重要保障。
（1）中国共产党给出了哪几个答案？
参考答案要点：
①人民监督。
②自我革命。
（2）二者是什么关系？
参考答案要点：二者辩证统一。
二、论述题
1.如何理解党的领导是最大优势？
（1）党是制度创建者。
（2）党的领导是根本保证。
"""


class XiParserTests(unittest.TestCase):
    def setUp(self):
        self.chapters, self.report = parse_text(SAMPLE)

    def test_parses_objective_formats(self):
        intro = self.chapters["导论"]
        self.assertEqual(["single", "multiple", "multiple", "judge"], [q["type"] for q in intro])
        self.assertEqual(["B"], intro[0]["answerKeys"])
        self.assertEqual(["A", "B", "C", "D"], intro[1]["answerKeys"])
        self.assertEqual(["A"], intro[3]["answerKeys"])
        self.assertEqual(4, len(intro[0]["options"]))

    def test_extracts_answers_embedded_in_stem(self):
        first = self.chapters["第一章 新时代坚持和发展中国特色社会主义"]
        self.assertEqual(["A"], first[0]["answerKeys"])
        self.assertNotIn(" A", first[0]["question"])
        self.assertEqual(["B"], first[1]["answerKeys"])

    def test_material_subquestions_keep_shared_material(self):
        chapter = self.chapters["第十七章 全面从严治党"]
        material = [q for q in chapter if q["type"] == "material"]
        self.assertEqual(2, len(material))
        self.assertIn("人民监督和自我革命", material[0]["question"])
        self.assertIn("哪几个答案", material[0]["question"])
        self.assertIn("人民监督", material[0]["answerText"][0])
        self.assertIn("二者辩证统一", material[1]["answerText"][0])

    def test_parses_essay_reference_answer(self):
        essay = [q for q in self.chapters["第十七章 全面从严治党"] if q["type"] == "essay"]
        self.assertEqual(1, len(essay))
        self.assertIn("最大优势", essay[0]["question"])
        self.assertIn("制度创建者", essay[0]["answerText"][0])

    def test_reports_unanswered_objective_question(self):
        self.assertEqual(1, self.report["blockingErrors"])
        self.assertTrue(any("缺少答案" in item["question"] for item in self.report["issues"]))

    def test_validator_rejects_blocking_errors(self):
        with self.assertRaises(ValueError):
            validate_chapters(self.chapters, self.report)

    def test_accepts_real_world_answer_and_option_variants(self):
        text = """导论
一、单选题
1.依法治国是基本方式。答案;C
A.甲 B.乙 C.丙 D.丁
二、多选题
1.基本原则包括（ABCD.）。
A坚持领导 B保障人权 C统筹安全 D预防为主
三、判断题
中国共产党是最高政治领导力量。（ V ）
"""
        chapters, report = parse_text(text)
        questions = chapters["导论"]
        self.assertEqual(["C"], questions[0]["answerKeys"])
        self.assertEqual(["A", "B", "C", "D"], questions[1]["answerKeys"])
        self.assertEqual(4, len(questions[1]["options"]))
        self.assertEqual(["A"], questions[2]["answerKeys"])
        self.assertEqual(0, report["blockingErrors"])

    def test_starts_a_new_shared_material_for_each_numbered_case(self):
        text = """导论
一、材料分析题
1.根据以下材料，请回答：
材料一：第一份材料。
（1）第一问？
参考答案要点：第一答。
2.根据以下材料，请回答：
材料一：第二份材料。
（1）第二问？
参考答案要点：第二答。
"""
        chapters, report = parse_text(text)
        questions = chapters["导论"]
        self.assertEqual(2, len(questions))
        self.assertIn("第一份材料", questions[0]["question"])
        self.assertNotIn("第二份材料", questions[0]["question"])
        self.assertIn("第二份材料", questions[1]["question"])
        self.assertEqual(0, report["blockingErrors"])

    def test_blank_answer_line_does_not_erase_embedded_answer(self):
        text = """导论
一、多选题
1.重大意义，这就是：ABC.
A.甲
B.乙
C.丙
D.丁
答案
"""
        chapters, report = parse_text(text)
        self.assertEqual(["A", "B", "C"], chapters["导论"][0]["answerKeys"])
        self.assertEqual(0, report["blockingErrors"])

    def test_direct_numbered_points_are_material_reference_answer(self):
        text = """导论
一、材料分析题
1.根据以下材料，请回答：
材料一：材料正文。
（1）为什么？
第一，原因一。
第二，原因二。
"""
        chapters, report = parse_text(text)
        question = chapters["导论"][0]
        self.assertEqual("为什么？", question["question"].splitlines()[-1])
        self.assertIn("原因一", question["answerText"][0])
        self.assertEqual(0, report["blockingErrors"])

    def test_question_mark_noise_around_inline_answers(self):
        text = """导论
一、单选题
1.（?B?）是实现民族复兴的必由之路。
A.改革开放
B.中国特色社会主义
C.社会主义现代化
D.中国式现代化
二、多选题
1.?中国式现代化是人口规模巨大的现代化，这意味着（?ABD?）
A.人口规模巨大的现代化
B.全体人民共同富裕的现代化
C.资本主义现代化
D.走和平发展道路的现代化
"""
        chapters, report = parse_text(text)
        questions = chapters["导论"]
        self.assertEqual(["B"], questions[0]["answerKeys"])
        self.assertEqual("（ ）是实现民族复兴的必由之路。", questions[0]["question"])
        self.assertEqual(["A", "B", "D"], questions[1]["answerKeys"])
        self.assertEqual("中国式现代化是人口规模巨大的现代化，这意味着（ ）", questions[1]["question"])
        self.assertEqual(0, report["blockingErrors"])


if __name__ == "__main__":
    unittest.main()
