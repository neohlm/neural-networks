import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import study_assistant


class StudyAssistantTests(unittest.TestCase):
    def test_chunks_overlap_and_keep_text(self):
        text = "word " * 500
        parts = study_assistant.chunks(text)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(parts))
        self.assertIn(parts[0][-30:], parts[1])

    def test_ingest_and_search_plain_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            document = root / "notes.txt"
            document.write_text("Gradient descent updates weights to reduce prediction error.", encoding="utf-8")
            with patch.object(study_assistant, "DB_PATH", root / "test.db"):
                count = study_assistant.ingest([document])
                results = study_assistant.search("gradient descent weights")
            self.assertEqual(count, 1)
            self.assertEqual(len(results), 1)
            self.assertEqual(Path(results[0][0]).name, "notes.txt")
            self.assertIn("[Gradient] [descent]", results[0][2])

    def test_search_empty_query_is_safe(self):
        self.assertEqual(study_assistant.search("!!!"), [])

    def test_unsupported_file_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "image.png"
            path.write_bytes(b"not actually an image")
            self.assertEqual(study_assistant.extract_text(path), [])


if __name__ == "__main__":
    unittest.main()
