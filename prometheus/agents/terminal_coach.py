import re
from typing import Any, Dict, Optional

import structlog
from openai import OpenAI

from prometheus.agents.base import Agent

log = structlog.get_logger()

SYSTEM_PROMPT = (
    "You are Prometheus, the legendary mentor and watcher from the heavens. "
    "Observe the user's terminal behavior and offer concise, wise, actionable guidance. "
    "Input: last command, cwd, exit code, hint. Output: one suggestion or none, 1–2 sentences."
)

client = OpenAI()


class TerminalCoach(Agent):
    name = "terminal_coach"

    def __init__(self, policy, episodic):
        self.policy = policy
        self.episodic = episodic

    def wants(self, event: Dict[str, Any]) -> bool:
        return event.get("source") == "terminal" and event.get("type") == "term.cmd"

    async def run(self, event: Dict[str, Any], decision) -> Optional[Dict[str, Any]]:
        p = event.get("payload", {})
        cmd = (p.get("cmd") or "").strip()
        cwd = p.get("cwd")
        exit_code = p.get("exit_code")

        if not cmd or cmd in {"ls", "pwd", "cd"}:
            return None
        hint = self._classify(cmd, exit_code)
        if not hint:
            return None

        user = event.get("actor", "user")
        prompt = f"cmd: `{cmd}`\ncwd: {cwd}\nexit_code: {exit_code}\nhint: {hint}\nRespond with one suggestion."

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            content = resp.choices[0].message.content
        except Exception:
            log.exception("llm_error")
            return None

        return {
            "agent": self.name,
            "mode": decision.mode,
            "ts": event["ts"],
            "user": user,
            "input": {"cmd": cmd, "cwd": cwd, "exit_code": exit_code, "hint": hint},
            "message": content,
        }

    def _classify(self, cmd: str, exit_code: int) -> Optional[str]:
        if exit_code not in (0, None):
            return "recent failure"
        if re.search(r"pytest", cmd) and "-q" not in cmd:
            return "pytest optimization"
        if re.search(r"git (commit|push|pull)", cmd) and "-v" not in cmd:
            return "git workflow hint"
        if re.search(r"pip install", cmd) and "-U" not in cmd:
            return "pip versioning hint"
        return None
