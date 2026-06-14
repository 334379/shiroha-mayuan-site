import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PwaAssetsTests(unittest.TestCase):
    def test_manifest_is_installable(self):
        manifest = json.loads((ROOT / "manifest.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual("standalone", manifest["display"])
        self.assertEqual("./", manifest["start_url"])
        self.assertEqual("./", manifest["scope"])
        self.assertTrue(any(icon["sizes"] == "512x512" for icon in manifest["icons"]))

    def test_index_contains_ios_and_manifest_metadata(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('rel="manifest" href="./manifest.webmanifest"', html)
        self.assertIn('name="apple-mobile-web-app-capable" content="yes"', html)
        self.assertIn('name="apple-mobile-web-app-status-bar-style"', html)
        self.assertIn('name="apple-mobile-web-app-title" content="Shiroha Quiz"', html)

    def test_index_registers_service_worker(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertRegex(html, r"navigator\.serviceWorker\.register\(['\"]\./service-worker\.js")

    def test_service_worker_caches_all_bundled_banks(self):
        worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        index = json.loads((ROOT / "data" / "banks-index.json").read_text(encoding="utf-8"))
        for item in index:
            self.assertIn("./" + item["file"], worker)
        self.assertIn("./manifest.webmanifest", worker)
        self.assertIn("./question-bank.js", worker)

    def test_service_worker_uses_cache_first_for_local_assets(self):
        worker = (ROOT / "service-worker.js").read_text(encoding="utf-8")
        self.assertIn("caches.match(request)", worker)
        self.assertIn("self.skipWaiting()", worker)
        self.assertIn("self.clients.claim()", worker)


if __name__ == "__main__":
    unittest.main()
