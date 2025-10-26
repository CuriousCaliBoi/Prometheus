import asyncio
import os
from typing import Any, Dict

import orjson
import redis
import structlog
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from prometheus.conductor.policy import Policy
from prometheus.conductor.dispatch import Dispatcher

log = structlog.get_logger()

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM_TERMINAL = "events:terminal"
GROUP_NAME = "prometheus"
CONSUMER_NAME = f"worker-{os.getpid()}"

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

app = FastAPI(title="Prometheus Conductor", version="0.1.0")
policy = Policy()
dispatcher = Dispatcher(policy=policy, redis_client=r)


class TerminalEvent(BaseModel):
    id: str
    ts: str
    actor: str
    payload: Dict[str, Any]


@app.get("/health")
async def health():
    try:
        r.ping()
    except Exception as e:
        return {"status": "degraded", "redis": str(e)}
    return {"status": "ok"}


@app.post("/ingest/terminal")
async def ingest_terminal(evt: TerminalEvent):
    event = {
        "id": evt.id,
        "source": "terminal",
        "type": "term.cmd",
        "ts": evt.ts,
        "actor": evt.actor,
        "payload": evt.payload,
    }
    r.xadd(STREAM_TERMINAL, {"event": orjson.dumps(event).decode("utf-8")}, id="*")
    return {"status": "queued"}


@app.on_event("startup")
async def startup_event():
    try:
        r.xgroup_create(STREAM_TERMINAL, GROUP_NAME, id="0-0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
    asyncio.create_task(worker_loop())


@app.on_event("shutdown")
async def shutdown_event():
    log.info("shutting_down")


async def worker_loop():
    log.info("worker_loop.start", group=GROUP_NAME, consumer=CONSUMER_NAME)
    while True:
        try:
            resp = r.xreadgroup(GROUP_NAME, CONSUMER_NAME, {STREAM_TERMINAL: ">"}, count=10, block=2000)
            if not resp:
                await asyncio.sleep(0.1)
                continue
            for _stream, messages in resp:
                for msg_id, fields in messages:
                    try:
                        raw = fields.get("event")
                        event = orjson.loads(raw)
                        await dispatcher.handle(event)
                        r.xack(STREAM_TERMINAL, GROUP_NAME, msg_id)
                    except Exception:
                        log.exception("event_error", msg_id=msg_id)
        except Exception:
            log.exception("worker_loop_error")
            await asyncio.sleep(1)
