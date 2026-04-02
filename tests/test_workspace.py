from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from src.registry.commands import PORTED_COMMANDS
from src.parity_audit import run_parity_audit
from src.port_manifest import build_port_manifest
from src.engine.query_engine import QueryEnginePort
from src.registry.tools import PORTED_TOOLS
from src.agent.settings import Settings


class PortingWorkspaceTests(unittest.TestCase):
    def test_manifest_counts_python_files(self) -> None:
        manifest = build_port_manifest()
        self.assertGreaterEqual(manifest.total_python_files, 20)
        self.assertTrue(manifest.top_level_modules)

    def test_query_engine_summary_mentions_workspace(self) -> None:
        summary = QueryEnginePort.from_workspace().render_summary()
        self.assertIn('Python Porting Workspace Summary', summary)
        self.assertIn('Command surface:', summary)
        self.assertIn('Tool surface:', summary)

    def test_cli_summary_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'summary'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Python Porting Workspace Summary', result.stdout)

    def test_parity_audit_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'parity-audit'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Parity Audit', result.stdout)

    def test_root_file_coverage_is_complete_when_local_archive_exists(self) -> None:
        audit = run_parity_audit()
        if audit.archive_present:
            self.assertEqual(audit.root_file_coverage[0], audit.root_file_coverage[1])
            self.assertGreaterEqual(audit.directory_coverage[0], 28)
            self.assertGreaterEqual(audit.command_entry_ratio[0], 150)
            self.assertGreaterEqual(audit.tool_entry_ratio[0], 100)

    def test_command_and_tool_snapshots_are_nontrivial(self) -> None:
        self.assertGreaterEqual(len(PORTED_COMMANDS), 150)
        self.assertGreaterEqual(len(PORTED_TOOLS), 100)

    def test_commands_and_tools_cli_run(self) -> None:
        commands_result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'commands', '--limit', '5', '--query', 'review'],
            check=True,
            capture_output=True,
            text=True,
        )
        tools_result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'tools', '--limit', '5', '--query', 'MCP'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Command entries:', commands_result.stdout)
        self.assertIn('Tool entries:', tools_result.stdout)

    def test_route_and_show_entry_cli_run(self) -> None:
        route_result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'route', 'review MCP tool', '--limit', '5'],
            check=True,
            capture_output=True,
            text=True,
        )
        show_command = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'show-command', 'review'],
            check=True,
            capture_output=True,
            text=True,
        )
        show_tool = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'show-tool', 'MCPTool'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('review', route_result.stdout.lower())
        self.assertIn('review', show_command.stdout.lower())
        self.assertIn('mcptool', show_tool.stdout.lower())

    def test_bootstrap_cli_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'bootstrap', 'review MCP tool', '--limit', '5'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Runtime Session', result.stdout)
        self.assertIn('Startup Steps', result.stdout)
        self.assertIn('Routed Matches', result.stdout)

    def test_bootstrap_session_tracks_turn_state(self) -> None:
        from src.engine.runtime import PortRuntime

        session = PortRuntime().bootstrap_session('review MCP tool', limit=5)
        self.assertGreaterEqual(len(session.turn_result.matched_tools), 1)
        self.assertIn('Prompt:', session.turn_result.output)
        self.assertGreaterEqual(session.turn_result.usage.input_tokens, 1)

    def test_exec_command_and_tool_cli_run(self) -> None:
        command_result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'exec-command', 'review', 'inspect security review'],
            check=True,
            capture_output=True,
            text=True,
        )
        tool_result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'exec-tool', 'MCPTool', 'fetch resource list'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("Mirrored command 'review'", command_result.stdout)
        self.assertIn("Mirrored tool 'MCPTool'", tool_result.stdout)

    def test_setup_report_and_registry_filters_run(self) -> None:
        setup_result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'setup-report'],
            check=True,
            capture_output=True,
            text=True,
        )
        command_result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'commands', '--limit', '5', '--no-plugin-commands'],
            check=True,
            capture_output=True,
            text=True,
        )
        tool_result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'tools', '--limit', '5', '--simple-mode', '--no-mcp'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Setup Report', setup_result.stdout)
        self.assertIn('Command entries:', command_result.stdout)
        self.assertIn('Tool entries:', tool_result.stdout)

    def test_load_session_cli_runs(self) -> None:
        from src.engine.runtime import PortRuntime

        session = PortRuntime().bootstrap_session('review MCP tool', limit=5)
        session_id = Path(session.persisted_session_path).stem
        result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'load-session', session_id],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn(session_id, result.stdout)
        self.assertIn('messages', result.stdout)

    def test_tool_permission_filtering_cli_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'tools', '--limit', '10', '--deny-prefix', 'mcp'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Tool entries:', result.stdout)
        self.assertNotIn('MCPTool', result.stdout)

    def test_turn_loop_cli_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'turn-loop', 'review MCP tool', '--max-turns', '2', '--structured-output'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('## Turn 1', result.stdout)
        self.assertIn('stop_reason=', result.stdout)

    def test_remote_mode_clis_run(self) -> None:
        remote_result = subprocess.run([sys.executable, '-m', 'src.cli.main', 'remote-mode', 'workspace'], check=True, capture_output=True, text=True)
        ssh_result = subprocess.run([sys.executable, '-m', 'src.cli.main', 'ssh-mode', 'workspace'], check=True, capture_output=True, text=True)
        teleport_result = subprocess.run([sys.executable, '-m', 'src.cli.main', 'teleport-mode', 'workspace'], check=True, capture_output=True, text=True)
        self.assertIn('mode=remote', remote_result.stdout)
        self.assertIn('mode=ssh', ssh_result.stdout)
        self.assertIn('mode=teleport', teleport_result.stdout)

    def test_flush_transcript_cli_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'flush-transcript', 'review MCP tool'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('flushed=True', result.stdout)

    def test_command_graph_and_tool_pool_cli_run(self) -> None:
        command_graph = subprocess.run([sys.executable, '-m', 'src.cli.main', 'command-graph'], check=True, capture_output=True, text=True)
        tool_pool = subprocess.run([sys.executable, '-m', 'src.cli.main', 'tool-pool'], check=True, capture_output=True, text=True)
        self.assertIn('Command Graph', command_graph.stdout)
        self.assertIn('Tool Pool', tool_pool.stdout)

    def test_setup_report_mentions_deferred_init(self) -> None:
        result = subprocess.run(
            [sys.executable, '-m', 'src.cli.main', 'setup-report'],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('Deferred init:', result.stdout)
        self.assertIn('plugin_init=True', result.stdout)

    def test_execution_registry_runs(self) -> None:
        from src.registry.execution_registry import build_execution_registry

        registry = build_execution_registry()
        self.assertGreaterEqual(len(registry.commands), 150)
        self.assertGreaterEqual(len(registry.tools), 100)
        self.assertIn('Mirrored command', registry.command('review').execute('review security'))
        self.assertIn('Mirrored tool', registry.tool('MCPTool').execute('fetch mcp resources'))

    def test_bootstrap_graph_and_direct_modes_run(self) -> None:
        graph_result = subprocess.run([sys.executable, '-m', 'src.cli.main', 'bootstrap-graph'], check=True, capture_output=True, text=True)
        direct_result = subprocess.run([sys.executable, '-m', 'src.cli.main', 'direct-connect-mode', 'workspace'], check=True, capture_output=True, text=True)
        deep_link_result = subprocess.run([sys.executable, '-m', 'src.cli.main', 'deep-link-mode', 'workspace'], check=True, capture_output=True, text=True)
        self.assertIn('Bootstrap Graph', graph_result.stdout)
        self.assertIn('mode=direct-connect', direct_result.stdout)
        self.assertIn('mode=deep-link', deep_link_result.stdout)


class AgentEnvAndSdkTests(unittest.TestCase):
    def test_get_api_key_reads_local_env_with_fallback(self) -> None:
        from src.agent import settings as settings_module

        blank_settings = Settings(env={"NANO_CLAUDE_API_KEY": "", "ANTHROPIC_AUTH_TOKEN": ""})
        with patch.object(settings_module, "load_settings", return_value=blank_settings):
            with patch.dict(
                "os.environ",
                {
                    "NANO_CLAUDE_API_KEY": " local-key ",
                    "ANTHROPIC_API_KEY": "cloud-key",
                },
                clear=True,
            ):
                self.assertEqual(settings_module.get_api_key(), "local-key")

    def test_get_base_url_and_model_read_local_env(self) -> None:
        from src.agent import settings as settings_module

        blank_settings = Settings(env={"NANO_CLAUDE_BASE_URL": "", "NANO_CLAUDE_MODEL": ""})
        with patch.object(settings_module, "load_settings", return_value=blank_settings):
            with patch.dict(
                "os.environ",
                {
                    "NANO_CLAUDE_BASE_URL": " https://gateway.local ",
                    "NANO_CLAUDE_MODEL": " glm-5-air ",
                },
                clear=True,
            ):
                self.assertEqual(settings_module.get_base_url(), "https://gateway.local")
                self.assertEqual(settings_module.get_model(), "glm-5-air")

    def test_get_model_defaults_when_empty(self) -> None:
        from src.agent import settings as settings_module

        blank_settings = Settings(env={"NANO_CLAUDE_MODEL": "   "})
        with patch.object(settings_module, "load_settings", return_value=blank_settings):
            with patch.dict("os.environ", {}, clear=True):
                self.assertEqual(settings_module.get_model(), "glm-5")

    def test_create_async_client_uses_settings_values(self) -> None:
        from src.agent import agent as agent_module

        with patch.object(agent_module, "get_api_key", return_value="sdk-key"):
            with patch.object(agent_module, "get_base_url", return_value="https://api.local"):
                with patch.object(agent_module, "AsyncAnthropic") as mock_client:
                    agent_module.create_async_client()
                    mock_client.assert_called_once_with(api_key="sdk-key", base_url="https://api.local")


if __name__ == '__main__':
    unittest.main()
