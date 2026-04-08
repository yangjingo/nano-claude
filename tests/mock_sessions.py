"""Create mock session data for testing /sessions and /resume."""

import json
import os

sessions_dir = os.path.join(".nano_claude", "sessions")
os.makedirs(sessions_dir, exist_ok=True)

mock_sessions = [
    {
        "session_id": "a1b2c3d4",
        "created": "2026-04-07T14:30:00",
        "updated": "2026-04-07T15:45:00",
        "model": "glm-5",
        "system_prompt": "You are nano-claude...",
        "messages": [
            {"role": "user", "content": "Help me refactor auth module"},
            {"role": "assistant", "content": "Sure, let me check the existing code..."},
            {"role": "user", "content": "Use JWT instead of session"},
            {"role": "assistant", "content": "Decided to use JWT, starting implementation..."},
        ],
        "notes": {"decisions": ["Use JWT instead of session"], "files_touched": ["src/auth.py"]},
        "token_usage": {"input": 1234, "output": 567},
    },
    {
        "session_id": "e5f6g7h8",
        "created": "2026-04-08T09:00:00",
        "updated": "2026-04-08T10:30:00",
        "model": "glm-5",
        "system_prompt": "You are nano-claude...",
        "messages": [
            {"role": "user", "content": "Implement cross-platform Bash tool"},
            {"role": "assistant", "content": "Detect Git Bash / cmd.exe / Unix bash..."},
            {"role": "user", "content": "Add timeout handling"},
            {"role": "assistant", "content": "Using asyncio.wait_for..."},
            {"role": "user", "content": "Write tests"},
            {"role": "assistant", "content": "All 24 tests passed..."},
        ],
        "notes": {"decisions": ["Cache shell detection"], "files_touched": ["src/tools/bash.py", "tests/test_tools.py"]},
        "token_usage": {"input": 3456, "output": 890},
    },
    {
        "session_id": "i9j0k1l2",
        "created": "2026-04-08T10:00:00",
        "updated": "2026-04-08T10:50:00",
        "model": "glm-5",
        "system_prompt": "You are nano-claude...",
        "messages": [
            {"role": "user", "content": "Design context compression strategy"},
        ],
        "notes": {},
        "token_usage": {"input": 500, "output": 200},
    },
]

for s in mock_sessions:
    path = os.path.join(sessions_dir, f"{s['session_id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

print(f"Created {len(mock_sessions)} mock sessions in {sessions_dir}/")
