import os
import time
from dataclasses import dataclass
from typing import Dict, Tuple

MODE = os.getenv("TERMINAL_COACH_MODE", "SUGGEST").upper()
COOLDOWN_MIN = int(os.getenv("TERMINAL_COACH_COOLDOWN_MIN", "30"))


@dataclass
class PolicyDecision:
    mode: str
    action: str
    cooldown_min: int


class Policy:
    def __init__(self):
        self.last_seen: Dict[Tuple[str, str], float] = {}

    def _fingerprint(self, event) -> str:
        p = event.get("payload", {})
        cmd = (p.get("cmd") or "").strip()
        head = cmd.split(" ")[0]
        flags = " ".join([tok for tok in cmd.split(" ")[1:] if tok.startswith("-")])
        return f"{head} {flags}".strip()

    def evaluate(self, event, agent_name: str) -> PolicyDecision:
        fp = self._fingerprint(event)
        key = (agent_name, fp)
        now = time.time()
        last = self.last_seen.get(key, 0)
        if now - last < COOLDOWN_MIN * 60:
            return PolicyDecision(mode=MODE, action="DROP", cooldown_min=COOLDOWN_MIN)
        self.last_seen[key] = now
        return PolicyDecision(mode=MODE, action="RUN", cooldown_min=COOLDOWN_MIN)
