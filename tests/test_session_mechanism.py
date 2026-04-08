"""Test session save/list/resume/clear mechanism (no API key needed)."""

import asyncio
import os
import sys
import tempfile
import shutil
import json
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.agent import AgentSession


def _with_tmpdir(fn):
    """Run fn with a temp session dir, cleanup after."""
    tmpdir = tempfile.mkdtemp()
    try:
        with patch.object(AgentSession, "_session_dir", staticmethod(lambda: tmpdir)):
            fn(tmpdir)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_save_and_list():
    """Save a session, list it, verify preview."""
    def body(tmpdir):
        session = AgentSession()
        session.messages = [
            {"role": "user", "content": "Hello, this is a test message"},
            {"role": "assistant", "content": "Hi there! How can I help?"},
            {"role": "user", "content": "Tell me about Python"},
            {"role": "assistant", "content": "Python is a great language."},
        ]

        path = session.save()
        assert path is not None, "save() should return a path"
        assert os.path.exists(path), "Session file should exist"

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["session_id"] == session.session_id
        assert len(data["messages"]) == 4

        sessions = AgentSession.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == session.session_id
        assert "Hello" in sessions[0]["preview"]
        assert sessions[0]["messages"] == "4"

        print("PASS: save_and_list")
    _with_tmpdir(body)


def test_load_and_resume():
    """Save a session, load it, verify state restored."""
    def body(tmpdir):
        session = AgentSession()
        session.messages = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"},
        ]
        session._token_usage = {"input": 100, "output": 50}
        sid = session.session_id
        session.save()

        restored = AgentSession.load(sid)
        assert restored is not None
        assert restored.session_id == sid
        assert len(restored.messages) == 2
        assert restored.messages[0]["content"] == "First message"
        assert restored._token_usage == {"input": 100, "output": 50}

        assert AgentSession.load("nonexistent") is None

        print("PASS: load_and_resume")
    _with_tmpdir(body)


def test_multiple_sessions():
    """Create multiple sessions, verify ordering."""
    def body(tmpdir):
        for i in range(3):
            s = AgentSession()
            s.messages = [{"role": "user", "content": f"Session {i}"}]
            s.save()

        sessions = AgentSession.list_sessions()
        assert len(sessions) == 3
        assert sessions[0]["preview"] == "Session 2"
        assert sessions[2]["preview"] == "Session 0"

        latest = AgentSession.latest_session_id()
        assert latest == sessions[0]["session_id"]

        print("PASS: multiple_sessions")
    _with_tmpdir(body)


def test_preview_with_context_block():
    """Preview should show user message content."""
    def body(tmpdir):
        session = AgentSession()
        session.messages = [
            {"role": "user", "content": "[context] Platform: win32 | Shell: bash\n\nHello world"},
            {"role": "assistant", "content": "Hi!"},
        ]
        session.save()

        sessions = AgentSession.list_sessions()
        assert len(sessions) == 1
        assert "Hello world" in sessions[0]["preview"]

        print("PASS: preview_with_context_block")
    _with_tmpdir(body)


def test_save_empty_session():
    """Save with no messages should return None."""
    def body(tmpdir):
        session = AgentSession()
        path = session.save()
        assert path is None
        assert len(os.listdir(tmpdir)) == 0

        print("PASS: save_empty_session")
    _with_tmpdir(body)


def test_list_empty_dir():
    """list_sessions with no sessions dir returns empty list."""
    def body(tmpdir):
        sessions = AgentSession.list_sessions()
        assert sessions == []

        print("PASS: list_empty_dir")
    _with_tmpdir(body)


if __name__ == "__main__":
    test_save_and_list()
    test_load_and_resume()
    test_multiple_sessions()
    test_preview_with_context_block()
    test_save_empty_session()
    test_list_empty_dir()
    print("\nAll session tests passed!")
