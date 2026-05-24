import json
import tempfile
import unittest
from pathlib import Path

import repo_context_pruner as pruner


class RepoContextPrunerTests(unittest.TestCase):
    def test_redacts_and_scores_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# Demo\n")
            token = "github_pat_" + "A" * 40
            (root / "app.py").write_text(f"API_TOKEN={token}\nprint('ok')\n")

            scores, pack = pruner.collect(root, 10_000, [])

        by_path = {item.path: item for item in scores}
        self.assertIn("README.md", by_path)
        self.assertIn("README.md", pack)
        self.assertEqual(by_path["app.py"].redactions, 1)

    def test_sarif_serializes(self):
        score = pruner.FileScore("app.py", 1, 10, ["source code"], 2, True)
        data = pruner.sarif([score])
        self.assertEqual(data["version"], "2.1.0")
        self.assertEqual(len(data["runs"][0]["results"]), 1)
        json.dumps(data)


if __name__ == "__main__":
    unittest.main()
