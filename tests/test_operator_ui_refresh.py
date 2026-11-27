"""Opt-in operator UI smoke test with synthetic local SQLite only."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contextlib import closing

from db import storage


@unittest.skipUnless(os.getenv("MEMORIA_UI_FIXTURES")=="1","explicit UI fixture run required")
class OperatorUIRefreshTests(unittest.TestCase):
    def test_empty_and_populated_operator_view(self):
        from streamlit.testing.v1 import AppTest
        from streamlit import cache_resource
        script=Path(__file__).resolve().parents[1]/"streamlit_app.py"
        with tempfile.TemporaryDirectory() as root, patch.object(storage,"DB_PATH",Path(root)/"demo.db"), patch.dict(
                os.environ,{"MEMORIA_ENCRYPT_AT_REST":"0"}), patch("uvicorn.run"):
            cache_resource.clear()
            try:
                at=AppTest.from_file(str(script),default_timeout=30).run()
                self.assertFalse(at.exception)
                self.assertTrue(any(m.label=="Loaded Memories" and m.value=="0" for m in at.metric))
                with closing(storage.get_connection()) as db:
                    storage.store_memory(db,{"app_name":"fixture:new-app","content":"<b>Invented MiXeD</b>",
                                             "tags":["fixture"]})
                at.run()
                self.assertFalse(at.exception)
                self.assertTrue(any(m.label=="Loaded Memories" and m.value=="1" for m in at.metric))
                self.assertTrue(any(t.value=="<b>Invented MiXeD</b>" for t in at.text))
                self.assertFalse(any(b.label=="Recall in Agentora" for b in at.button))
                search=next(t for t in at.text_input if t.label=="Search memories")
                search.set_value("mixed").run()
                self.assertFalse(at.exception)
                self.assertTrue(any("#1 | fixture:new-app" in t.value for t in at.text))
                self.assertTrue(any(c.label=="fixture:new-app can read" for c in at.toggle))
            finally:
                cache_resource.clear()


if __name__=="__main__":
    unittest.main()
