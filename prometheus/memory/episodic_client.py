import os

import httpx

BASE = os.getenv("EPISODIC_BASE_URL", "http://localhost:8000")


class Episodic:
    async def save_decision(self, payload: dict):
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{BASE}/prometheus/decision", json=payload)
