import os

from pydantic import BaseModel


class Settings(BaseModel):
    model_name: str = "claude-opus-4-8"
    max_agent_steps: int = 20
    workspace_dir: str = ".cellar"


def load_settings() -> Settings:
    return Settings(
        model_name=os.environ.get("CELLAR_MODEL_NAME", "claude-opus-4-8"),
        workspace_dir=os.environ.get("CELLAR_WORKSPACE_DIR", ".cellar"),
    )
