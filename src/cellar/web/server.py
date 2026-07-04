from collections.abc import Iterator
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from cellar.agents.streaming_agent import StreamingAgent
from cellar.config import load_settings
from cellar.prompts.matchmaker import MATCHMAKER_SYSTEM_PROMPT
from cellar.schemas.matchmaker import MatchmakerQuery, QuestionType
from cellar.schemas.recommendation import RecommendationReport
from cellar.services.llm import build_client
from cellar.services.matchmaker import UnsupportedTargetError, run_matchmaker
from cellar.tools.registry import build_matchmaker_tools

_STATIC_DIR = Path(__file__).parent / "static"
_DESIGN_DIR = Path(__file__).parent / "design_system"


def create_app() -> FastAPI:
    settings = load_settings()
    client = build_client(settings)
    agent = StreamingAgent(
        client=client,
        settings=settings,
        tools=build_matchmaker_tools(),
        system=MATCHMAKER_SYSTEM_PROMPT,
    )
    app = FastAPI(title="cellar")
    app.mount("/assets", StaticFiles(directory=_DESIGN_DIR), name="assets")

    @app.get("/")
    def index() -> HTMLResponse:
        return HTMLResponse((_STATIC_DIR / "index.html").read_text())

    @app.get("/config")
    def config() -> dict[str, str]:
        return {"provider": settings.provider, "model": settings.model_name}

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
            raise HTTPException(status_code=422, detail=str(error))

    @app.get("/chat")
    def chat(message: str) -> StreamingResponse:
        def event_stream() -> Iterator[str]:
            for event in agent.send(message):
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
                return candidate
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        return probe.getsockname()[1]


def main() -> None:
    import os

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
