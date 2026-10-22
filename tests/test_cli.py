"""Exercise the terminal interface with the real session and a fake MLX transport."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import httpx

from dase import utils
from dase.providers.mlx import MLXConfig, MLXProvider
from dase.simulation import SimulationSession
import run_dase_cli


class CLITests(TestCase):
    def test_failed_turn_retry_and_exit_export(self):
        requests = []
        def respond(request):
            requests.append(request)
            if len(requests) == 1:
                return httpx.Response(500, text="Model allocation failed")
            return httpx.Response(200, json={"choices": [{"message": {"content": "A fictional alert appears."},
                                                         "finish_reason": "stop"}]})
        session = SimulationSession(
            "Apple MLX (local)", Path(utils.COMPANY_MAP["Well Connect"]).read_text(),
            "Well Connect", "low", 3,
            local_provider=MLXProvider(MLXConfig(max_history_chars=100000), httpx.MockTransport(respond)))
        out, err = StringIO(), StringIO()
        with patch("builtins.input", side_effect=["Start a phishing scenario", "/retry", "/quit"]), \
                patch.object(utils, "save_session", return_value="test-session.json") as save, \
                redirect_stdout(out), redirect_stderr(err):
            run_dase_cli.chat(session, debug=True)
        self.assertEqual(len(requests), 2)
        self.assertEqual(len(session.history), 2)
        self.assertEqual(len(session.log.turns), 2)
        self.assertIn("HTTP 500", err.getvalue())
        self.assertIn("Model allocation failed", err.getvalue())
        self.assertIn("A fictional alert appears.", out.getvalue())
        save.assert_called_once_with(session.log)

    def test_empty_session_exit_never_calls_provider_or_exports(self):
        with patch("builtins.input", side_effect=["/retry", "/quit"]), \
                patch.object(utils, "save_session") as save, redirect_stdout(StringIO()):
            session = SimulationSession("Apple MLX (local)", "{}", "Test", "low", 3)
            with patch.object(session, "send") as send:
                run_dase_cli.chat(session)
        send.assert_not_called()
        save.assert_not_called()

    def test_diagnostic_options(self):
        args = run_dase_cli.parse_args(["--connect-only", "--debug", "--company", "AeroPay",
                                        "--max-tokens", "1536", "--timeout", "240",
                                        "--max-history-chars", "32000"])
        self.assertTrue(args.connect_only)
        self.assertTrue(args.debug)
        self.assertEqual(args.company, "AeroPay")
        self.assertEqual(args.max_tokens, 1536)
        self.assertEqual(args.max_history_chars, 32000)

    def test_connect_only_does_not_manage_server(self):
        with patch("sys.argv", ["run_dase_cli.py", "--connect-only", "--max-history-chars", "100000"]), \
                patch.object(run_dase_cli, "local_server") as server, \
                patch.object(run_dase_cli, "chat") as chat, redirect_stdout(StringIO()):
            self.assertEqual(run_dase_cli.main(), 0)
        server.assert_not_called()
        chat.assert_called_once()

    def test_oversized_initial_context_exits_before_starting_server(self):
        out = StringIO()
        with patch("sys.argv", ["run_dase_cli.py", "--max-history-chars", "10"]), \
                patch.object(run_dase_cli, "local_server") as server, \
                redirect_stdout(StringIO()), redirect_stderr(out):
            self.assertEqual(run_dase_cli.main(), 1)
        server.assert_not_called()
        self.assertIn("initial context already exceeds", out.getvalue())
