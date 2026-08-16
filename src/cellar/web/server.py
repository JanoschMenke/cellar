import os
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import anthropic
from anthropic import Anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from cellar.agents.streaming_agent import StreamingAgent
from cellar.agents.verifier_agent import VerifierAgent
from cellar.config import ModelProvider, load_settings
from cellar.prompts.matchmaker import MATCHMAKER_SYSTEM_PROMPT
from cellar.prompts.verifier import VERIFIER_SYSTEM_PROMPT
from cellar.schemas.events import StreamEvent, StreamEventKind
from cellar.schemas.matchmaker import MatchmakerQuery, QuestionType
from cellar.schemas.recommendation import RecommendationReport
from cellar.schemas.services import LlmClient
from cellar.schemas.tool_names import ToolName
from cellar.services.derivation import reasoning
from cellar.services.derivation.matchmaker import UnsupportedTargetError, run_matchmaker
from cellar.services.llm import build_client, needs_api_key, write_api_key_to_env
from cellar.tools.registry import build_matchmaker_tools, build_server_tools

_STATIC_DIR = Path(__file__).parent / "static"
_DESIGN_DIR = Path(__file__).parent / "design_system"
_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"

_ANTHROPIC_API_KEY_PREFIX = "sk-ant-"


class ApiKeyBody(BaseModel):
    api_key: str


def create_app() -> FastAPI:
    settings = load_settings()
    clients: dict[str, LlmClient] = {"llm": build_client(settings)}
    agent = StreamingAgent(
        client=clients["llm"],
        settings=settings,
        tools=build_matchmaker_tools(),
        server_tools=build_server_tools(settings),
        system=MATCHMAKER_SYSTEM_PROMPT,
    )
    app = FastAPI(title="cellar")
    app.mount("/assets", StaticFiles(directory=_DESIGN_DIR), name="assets")
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    @app.get("/")
    def index() -> HTMLResponse:
        return HTMLResponse((_STATIC_DIR / "index.html").read_text())

    @app.get("/config")
    def config() -> dict[str, str | bool]:
        return {
            "provider": settings.provider,
            "model": settings.model_name,
            "needs_api_key": needs_api_key(settings),
        }

    @app.post("/reset")
    def reset() -> dict[str, bool]:
        agent.reset()
        return {"ok": True}

    @app.post("/api-key")
    def set_api_key(body: ApiKeyBody) -> JSONResponse:
        key = body.api_key.strip()
        if not key or not key.startswith(_ANTHROPIC_API_KEY_PREFIX):
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "That doesn't look like an Anthropic API key."},
            )
        if settings.provider is not ModelProvider.DIRECT_API:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "API keys are not used with the Bedrock provider."},
            )
        candidate = cast(Anthropic, build_client(settings, api_key=key))
        try:
            candidate.models.list(limit=1)
        except anthropic.AuthenticationError:
            return JSONResponse(
                status_code=401,
                content={"ok": False, "error": "That key was rejected by Anthropic."},
            )
        except Exception:
            pass
        os.environ["ANTHROPIC_API_KEY"] = key
        clients["llm"] = candidate
        agent.set_client(candidate)
        reasoning._client_and_settings.cache_clear()
        write_api_key_to_env(key, _ENV_PATH)
        return JSONResponse(content={"ok": True})

    @app.get("/recommend")
    def recommend(
        target_symbol: str, disease: str, question_type: QuestionType
    ) -> RecommendationReport:
        query = MatchmakerQuery(
            target_symbol=target_symbol, disease=disease, question_type=question_type
        )
        try:
            return run_matchmaker(query)
        except UnsupportedTargetError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    def _run_verifier() -> Iterator[StreamEvent]:
        verifier = VerifierAgent(
            client=clients["llm"],
            settings=settings,
            tools=build_matchmaker_tools(),
            evidence_store=agent.evidence_store,
            system=VERIFIER_SYSTEM_PROMPT,
        )
        yield from verifier.verify()

    @app.get("/chat")
    def chat(message: str) -> StreamingResponse:
        def event_stream() -> Iterator[str]:
            recommendations_before = len(
                agent.evidence_store.by_tool(ToolName.BUILD_RECOMMENDATIONS)
            )
            for event in agent.send(message):
                if event.kind is StreamEventKind.DONE:
                    produced = (
                        len(agent.evidence_store.by_tool(ToolName.BUILD_RECOMMENDATIONS))
                        > recommendations_before
                    )
                    if produced:
                        yield f"data: {StreamEvent(kind=StreamEventKind.VERIFY_START).model_dump_json()}\n\n"
                        for verify_event in _run_verifier():
                            yield f"data: {verify_event.model_dump_json()}\n\n"
                        return
                    yield f"data: {event.model_dump_json()}\n\n"
                    return
                yield f"data: {event.model_dump_json()}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


def _find_free_port(host: str, preferred: int) -> int:
    import socket

    for candidate in [preferred, *range(preferred + 1, preferred + 25)]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((host, candidate))
                return int(candidate)
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        return int(probe.getsockname()[1])


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    import uvicorn

    settings = load_settings()
    host = os.environ.get("CELLAR_HOST", "127.0.0.1")
    preferred = int(os.environ.get("CELLAR_PORT", "1312"))
    port = _find_free_port(host, preferred)

    print(f"cellar web — provider {settings.provider}, model {settings.model_name}")
    if port != preferred:
        print(f"(port {preferred} was busy — using {port} instead)")
    print(f"Open http://{host}:{port}\n")
    uvicorn.run(create_app(), host=host, port=port, log_level="warning")
