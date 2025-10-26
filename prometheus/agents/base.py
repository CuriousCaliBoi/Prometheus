from typing import Any, Dict


class Agent:
    name: str = "base"

    def wants(self, event: Dict[str, Any]) -> bool:
        raise NotImplementedError

    async def run(self, event: Dict[str, Any], decision) -> Dict[str, Any]:
        raise NotImplementedError
