from typing import Any, Dict

import structlog

from prometheus.conductor.policy import PolicyDecision
from prometheus.agents.terminal_coach import TerminalCoach
from prometheus.memory.episodic_client import Episodic

log = structlog.get_logger()


class Dispatcher:
    def __init__(self, policy, redis_client):
        self.policy = policy
        self.redis = redis_client
        self.episodic = Episodic()
        self.agents = [TerminalCoach(policy=self.policy, episodic=self.episodic)]

    async def handle(self, event: Dict[str, Any]):
        for agent in self.agents:
            if agent.wants(event):
                decision: PolicyDecision = self.policy.evaluate(event, agent.name)
                if decision.action == "DROP":
                    log.info("policy_drop", agent=agent.name)
                    return
                suggestion = await agent.run(event, decision)
                if suggestion:
                    await self._emit_suggestion(suggestion)

    async def _emit_suggestion(self, suggestion: Dict[str, Any]):
        try:
            await self.episodic.save_decision(suggestion)
        except Exception:
            log.exception("episodic_write_failed")
        log.info("PROMETHEUS_GUIDANCE", **suggestion)
