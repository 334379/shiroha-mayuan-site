import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.build_xi_bank import parse_text, write_site


SAMPLE = """导论
一、单选题
1.主题是（ ）。
A.甲 B.乙 C.丙 D.丁
答案：B
第一章 新时代坚持和发展中国特色社会主义
一、材料分析题
1.根据以下材料，请回答：
材料一：材料。
（1）怎么做？
参考答案要点：认真做。
第二章 以中国式现代化全面推进中华民族伟大复兴
二、论述题
1.如何理解？
第一，要理解。
第三章 坚持党的全面领导
三、判断题
党的领导重要。（√）
第四章 坚持以人民为中心
三、判断题
人民重要。（√）
第五章 全面深化改革
三、判断题
改革重要。（√）
第六章 推动高质量发展
三、判断题
发展重要。（√）
第七章 社会主义现代化建设的教育、科技、人才战略
三、判断题
教育重要。（√）
第八章 发展全过程人民民主
三、判断题
民主重要。（√）
第九章 全面依法治国
三、判断题
法治重要。（√）
第十章 建设社会主义文化强国
三、判断题
文化重要。（√）
第十一章 以保障和改善民生为重点加强社会建设
三、判断题
民生重要。（√）
第十二章 建设社会主义生态文明
三、判断题
生态重要。（√）
第十三章 维护和塑造国家安全
三、判断题
安全重要。（√）
第十四章 建设巩固国防和强大人民军队
三、判断题
国防重要。（√）
第十五章 坚持“一国两制”和推进祖国完全统一
三、判断题
统一重要。（√）
第十六章 中国特色大国外交和推动构建人类命运共同体
三、判断题
外交重要。（√）
第十七章 全面从严治党
三、判断题
治党重要。（√)
"""


class SiteGenerationTests(unittest.TestCase):
    def test_write_site_keeps_mayuan_and_removes_c1(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            data.mkdir()
            (data / "banks-index.json").write_text(
                json.dumps(
                    [
                        {"id": "c1-full", "name": "C1", "count": 1, "file": "data/c1-full.json"},
                        {"id": "mayuan-full", "name": "马原", "count": 1, "file": "data/mayuan-full.json"},
                        {"id": "xsd-full", "name": "旧习概", "count": 1, "file": "data/xsd-full.json"},
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (data / "c1-full.json").write_text('{"meta":{},"questions":[]}', encoding="utf-8")
            (data / "mayuan-full.json").write_text(
                json.dumps({"meta": {"title": "马原"}, "questions": [{"id": "m-1", "type": "single", "number": 1, "question": "q", "options": [], "answerKeys": ["A"], "category": "马原"}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (data / "xsd-full.json").write_text('{"meta":{},"questions":[]}', encoding="utf-8")
            (root / "question-bank.js").write_text(
                "window.questionBankIndex = [];\nwindow.questionBank = {\"meta\":{},\"questions\":[]};\nwindow.shirohaPreloadedBanks = [];\n",
                encoding="utf-8",
            )
            chapters, report = parse_text(SAMPLE)
            result = write_site(root, chapters, report)
            index = json.loads((data / "banks-index.json").read_text(encoding="utf-8"))
            ids = [item["id"] for item in index]
            self.assertNotIn("c1-full", ids)
            self.assertIn("mayuan-full", ids)
            self.assertIn("xsd-full", ids)
            self.assertEqual(20, result["indexCount"])
            self.assertFalse((data / "c1-full.json").exists())
            self.assertEqual(18, sum(1 for item in ids if item.startswith("xsd-chapter")))
            self.assertIn("window.shirohaPreloadedBanks", (root / "question-bank.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
