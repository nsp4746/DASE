"""Check launcher ownership and failure cleanup without starting MLX or a GUI."""
from unittest import TestCase
from unittest.mock import MagicMock, patch

import httpx

from dase.providers.mlx import MLXConfig
import run_dase


class LauncherTests(TestCase):
    def test_starts_server_then_gui_and_stops_owned_server(self):
        server, gui = MagicMock(), MagicMock()
        server.poll.return_value = None
        gui.poll.return_value = 0
        gui.wait.return_value = 0
        with patch.object(run_dase, "server_ready", return_value=False), \
                patch.object(run_dase.socket, "create_connection", side_effect=ConnectionRefusedError), \
                patch.object(run_dase, "find_spec", return_value=object()), \
                patch.object(run_dase, "wait_for_server") as ready, \
                patch.object(run_dase.subprocess, "Popen", side_effect=[server, gui]) as spawn:
            self.assertEqual(run_dase.run_local(MLXConfig()), 0)
        ready.assert_called_once()
        self.assertIn("mlx_lm.server", spawn.call_args_list[0].args[0])
        self.assertEqual(spawn.call_args_list[1].args[0][-2:], ["-m", "dase"])
        self.assertEqual(spawn.call_args_list[1].kwargs["env"]["DASE_DEFAULT_PROVIDER"],
                         "Apple MLX (local)")
        server.terminate.assert_called_once()

    def test_reuses_existing_server_without_stopping_it(self):
        gui = MagicMock()
        gui.wait.return_value = 0
        gui.poll.return_value = 0
        with patch.object(run_dase, "server_ready", return_value=True), \
                patch.object(run_dase.subprocess, "Popen", return_value=gui) as spawn:
            self.assertEqual(run_dase.run_local(MLXConfig()), 0)
        spawn.assert_called_once()
        self.assertEqual(spawn.call_args.args[0][-1], "dase")
        gui.terminate.assert_not_called()

    def test_failed_startup_cleans_up_without_opening_gui(self):
        server = MagicMock()
        server.poll.return_value = None
        with patch.object(run_dase, "server_ready", return_value=False), \
                patch.object(run_dase.socket, "create_connection", side_effect=ConnectionRefusedError), \
                patch.object(run_dase, "find_spec", return_value=object()), \
                patch.object(run_dase, "wait_for_server", side_effect=RuntimeError("startup failed")), \
                patch.object(run_dase.subprocess, "Popen", return_value=server) as spawn:
            with self.assertRaisesRegex(RuntimeError, "startup failed"):
                run_dase.run_local(MLXConfig())
        spawn.assert_called_once()
        server.terminate.assert_called_once()

    def test_occupied_port_is_not_replaced(self):
        with patch.object(run_dase, "server_ready", return_value=False), \
                patch.object(run_dase.socket, "create_connection"), \
                patch.object(run_dase.subprocess, "Popen") as spawn:
            with self.assertRaisesRegex(RuntimeError, "occupied"):
                run_dase.run_local(MLXConfig())
        spawn.assert_not_called()

    def test_health_probe_handles_unavailable_server(self):
        client = MagicMock()
        client.get.side_effect = httpx.ConnectError("offline")
        self.assertFalse(run_dase.server_ready(client, "http://127.0.0.1:8080/health"))

    def test_server_exit_is_reported_before_gui_launch(self):
        server = MagicMock()
        server.poll.return_value = 1
        with self.assertRaisesRegex(RuntimeError, "exited"):
            run_dase.wait_for_server(server, MagicMock(), "http://127.0.0.1:8080/health")
