"""Client compatibility and failure handling without external network calls."""
import unittest
from unittest.mock import patch
import requests

from integrations.triad_hooks import MemoriaClient


class ClientRefreshTests(unittest.TestCase):
    def response(self, status, body):
        response=requests.Response()
        response.status_code=status
        response.url="http://127.0.0.1:8765/memoria/recall"
        response._content=body.encode()
        return response

    def test_success_and_local_transport(self):
        client=MemoriaClient(token="fixture-token")
        with patch("requests.Session.request",return_value=self.response(200,'{"items":[]}')) as call:
            self.assertEqual(client.recall("invented"),{"items":[]})
            args, kwargs=call.call_args
            self.assertEqual(args,("POST","http://127.0.0.1:8765/memoria/recall"))
            self.assertFalse(kwargs["allow_redirects"])
            self.assertEqual(kwargs["headers"],{"Authorization":"Bearer fixture-token"})

    def test_rejections_and_redirects_raise(self):
        client=MemoriaClient(token="fixture-token")
        for status in (302,401,403,422,503):
            with self.subTest(status=status), patch("requests.Session.request",
                    return_value=self.response(status,'{"detail":"held"}')):
                with self.assertRaises(requests.HTTPError):
                    client.recall("invented")

    def test_nonlocal_credential_target_refused(self):
        for url in ("https://example.invalid", "http://127.0.0.1.evil.invalid",
                    "http://user@127.0.0.1:8765", "http://127.0.0.1:8765/path"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                MemoriaClient(url,token="fixture-token")


if __name__=="__main__":
    unittest.main()
