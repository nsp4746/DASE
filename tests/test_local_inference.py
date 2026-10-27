"""Offline contract tests. Never load MLX, download weights, or call cloud APIs."""
from dataclasses import replace
import ast
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Thread, get_ident
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from queue import Queue
import queue
import threading

import httpx

from dase.providers.mlx import InferenceError, MLXConfig, MLXProvider
from dase.simulation import SimulationSession
from dase import utils


def session(provider=None, company="AeroPay"):
    profile = Path(utils.COMPANY_MAP[company]).read_text()
    return SimulationSession("Apple MLX (local)", profile, company, "medium", 3,
                             local_provider=provider or MLXProvider(MLXConfig(max_history_chars=100000)))


class LocalInferenceTests(unittest.TestCase):
    def test_multiturn_context_export_and_isolation(self):
        requests = []

        def respond(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={"choices": [{"message": {"content": "A suspicious payout is blocked. What do you do?"},
                                                         "finish_reason": "stop"}],
                                             "usage": {"prompt_tokens": 100, "completion_tokens": 12}})

        exercise = session(MLXProvider(MLXConfig(max_history_chars=100000), httpx.MockTransport(respond)))
        exercise.send("Simulate compromised partner webhooks")
        exercise.send("Disable the partner webhook and preserve logs")
        self.assertEqual([m["role"] for m in requests[1]["messages"]],
                         ["system", "user", "assistant", "user"])
        context = requests[0]["messages"][0]["content"]
        self.assertIn("AeroPay Financial Services", context)
        self.assertIn("difficulty=medium; reactions=3", context)
        self.assertNotIn("{company}", context)
        self.assertEqual(session(company="Well Connect").history, [])
        self.assertEqual(len(exercise.log.turns), 4)
        self.assertIn("elapsed_seconds", exercise.log.turns[-1].raw_chunks[0])
        with TemporaryDirectory() as directory:
            first = utils.save_session(exercise.log, directory)
            second = utils.save_session(exercise.log, directory)
            self.assertNotEqual(first, second)
            exported = json.loads(Path(first).read_text())
            self.assertEqual(exported["metadata"]["provider"], "Apple MLX (local)")
            self.assertEqual(len(exported["turns"]), 4)

    def test_failure_does_not_commit_or_fallback(self):
        cases = [httpx.Response(503), httpx.Response(302, headers={"Location": "https://example.com"}),
                 httpx.Response(200, text="not JSON"), httpx.Response(200, json={}),
                 httpx.Response(200, json={"choices": [{"message": {"content": ""}}]}),
                 httpx.Response(200, json={"choices": [{"message": {"content": "partial"}, "finish_reason": "length"}]})]
        for response in cases:
            with self.subTest(status=response.status_code, body=response.text):
                exercise = session(MLXProvider(MLXConfig(max_history_chars=100000), httpx.MockTransport(lambda req: response)))
                with self.assertRaises(InferenceError):
                    exercise.send("Start")
                self.assertEqual(exercise.history, [])
                self.assertEqual(exercise.log.turns, [])

    def test_timeout_and_connection_error(self):
        for error in [httpx.ReadTimeout("slow"), httpx.ConnectError("offline")]:
            def fail(request):
                raise error
            exercise = session(MLXProvider(MLXConfig(max_history_chars=100000), httpx.MockTransport(fail)))
            with self.assertRaises(InferenceError):
                exercise.send("Start")
            self.assertEqual(exercise.history, [])

    def test_history_limit_rejects_without_discarding_context(self):
        provider = MLXProvider(replace(MLXConfig(max_history_chars=100000), max_history_chars=10))
        with self.assertRaisesRegex(InferenceError, "No history was discarded"):
            session(provider).send("Start")

    def test_loopback_only_configuration(self):
        for url in ["https://example.com/v1", "http://192.168.1.2/v1", "http://user:secret@localhost/v1",
                    "http://localhost/v1?redirect=1", "http://localhost:99999/v1"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                MLXConfig(base_url=url)
        with patch.dict("os.environ", {"MLX_MODEL": "local-model", "MLX_MAX_TOKENS": "256"}):
            config = MLXConfig.from_env()
            self.assertEqual(config.model, "local-model")
            self.assertEqual(config.max_tokens, 256)
            self.assertEqual(MLXConfig.from_env("another-model").model, "another-model")

    def test_concurrent_send_rejected(self):
        entered, release = Event(), Event()
        def respond(request):
            entered.set()
            release.wait(2)
            return httpx.Response(200, json={"choices": [{"message": {"content": "Scenario"}}]})
        exercise = session(MLXProvider(MLXConfig(max_history_chars=100000), httpx.MockTransport(respond)))
        worker = Thread(target=exercise.send, args=("Start",))
        worker.start()
        try:
            self.assertTrue(entered.wait(2))
            with self.assertRaisesRegex(RuntimeError, "already"):
                exercise.send("Another action")
        finally:
            release.set()
            worker.join(2)
        self.assertEqual(len(exercise.history), 2)


class CloudCompatibilityTests(unittest.TestCase):
    def test_gemini_sdk_request_and_independent_sessions(self):
        from dase.providers import gemini
        with patch.object(gemini.genai, "Client") as factory:
            stream = factory.return_value.models.generate_content_stream
            stream.side_effect = lambda **kwargs: iter([SimpleNamespace(text="A fictional alert appears.")])
            a = SimulationSession("Google Gemini", "{}", "Company A", "low", 2)
            b = SimulationSession("Google Gemini", "{}", "Company B", "high", 3)
            a.send("Scenario A")
            a.send("Contain the host")
            self.assertEqual(len(stream.call_args.kwargs["contents"]), 3)
            b.send("Scenario B")
            self.assertEqual(len(stream.call_args.kwargs["contents"]), 1)
            self.assertIn("Company B", stream.call_args.kwargs["config"].system_instruction[0].text)
            self.assertIsNone(stream.call_args.kwargs["config"].tools)
            self.assertEqual(gemini.conversation_history, [])
            stream.side_effect = RuntimeError("unavailable")
            before = list(a.history)
            with self.assertRaises(RuntimeError):
                a.send("Failed action")
            self.assertEqual(a.history, before)

    def test_openai_retains_hosted_prompt_and_rejects_failed_turn(self):
        from dase.providers import openai_cli
        with patch.object(openai_cli, "OpenAI") as factory:
            create = factory.return_value.responses.create
            create.return_value = SimpleNamespace(output_text="A fictional incident starts.")
            exercise = SimulationSession("OpenAI ChatGPT", "{}", "Company A", "medium", 3)
            exercise.send("Start a scenario")
            exercise.send("Isolate the endpoint")
            self.assertIn("Start a scenario", create.call_args.kwargs["input"])
            self.assertIn("prompt", create.call_args.kwargs)
            self.assertEqual(create.call_args.kwargs["prompt"]["variables"]["reactions"], "3")
            create.side_effect = RuntimeError("offline")
            with self.assertRaises(RuntimeError):
                exercise.send("Failed action")
            self.assertEqual(len(exercise.history), 4)
            self.assertEqual(len(exercise._client.history), 4)
            create.side_effect = None
            create.return_value = SimpleNamespace(output_text=" ")
            with self.assertRaisesRegex(RuntimeError, "no text"):
                exercise.send("Empty response")
            self.assertEqual(len(exercise._client.history), 4)

    def test_openai_cli_export(self):
        from dase.providers import openai_cli
        client = SimpleNamespace(history=[{"role": "user", "text": "Start"},
                                          {"role": "dase", "text": "Scenario"}])
        with patch("builtins.input", return_value="yes"), patch.object(utils, "save_session") as save:
            openai_cli.save_history_and_exit(client)
            self.assertEqual([t.role for t in save.call_args.args[0].turns], ["user", "model"])


class GUIThreadTests(unittest.TestCase):
    def test_worker_returns_results_without_touching_gui(self):
        # Exercise the real callback functions without opening a display in CI.
        tree = ast.parse((Path(__file__).resolve().parents[1] / "dase" / "gui.py").read_text())
        names = {"send_message_callback", "set_busy", "process_results"}
        functions = ast.Module(body=[node for node in tree.body
                                    if isinstance(node, ast.FunctionDef) and node.name in names],
                               type_ignores=[])
        main_thread = get_ident()
        touched_threads = []
        entered, release, finished = Event(), Event(), Event()
        dpg = MagicMock()
        dpg.get_value.return_value = "Contain the endpoint"
        for method in ["configure_item", "add_text", "set_value", "does_item_exist", "get_value"]:
            getattr(dpg, method).side_effect = lambda *args, **kwargs: touched_threads.append(get_ident())
        dpg.get_value.side_effect = lambda *args: "Contain the endpoint"
        dpg.does_item_exist.side_effect = lambda *args: True

        class ResultQueue(Queue):
            def put(self, value):
                super().put(value)
                finished.set()

        def generate(user_input):
            self.assertNotEqual(main_thread, get_ident())
            entered.set()
            release.wait(2)
            return "The endpoint is isolated."

        exercise = SimpleNamespace(send=MagicMock(side_effect=generate))
        namespace = {"dpg": dpg, "threading": threading, "results": ResultQueue(),
                     "Empty": queue.Empty, "busy": False, "step": 0,
                     "active_session": exercise, "USER_COLOR": (), "MODEL_COLOR": (),
                     "wrap_width": lambda tag: 500, "_decode_unicode": lambda value: value}
        exec(compile(functions, "gui.py", "exec"), namespace)
        try:
            namespace["send_message_callback"]()
            self.assertTrue(entered.wait(2))
            self.assertTrue(namespace["busy"])
            namespace["send_message_callback"]()
            exercise.send.assert_called_once()
        finally:
            release.set()
        self.assertTrue(finished.wait(2))
        self.assertTrue(namespace["busy"])
        namespace["process_results"]()
        self.assertFalse(namespace["busy"])
        dpg.set_value.assert_any_call("model_response_1", "DASE: The endpoint is isolated.")
        self.assertEqual(set(touched_threads), {main_thread})


if __name__ == "__main__":
    unittest.main()
