import os
import sys
from getpass import getpass

from anthropic import AuthenticationError
from dotenv import find_dotenv, load_dotenv, set_key

from cellar.agents.console_agent import ConsoleAgent
from cellar.config import ModelProvider, Settings, load_settings
from cellar.prompts.matchmaker import MATCHMAKER_SYSTEM_PROMPT
from cellar.services.llm import LlmClient, build_client
from cellar.tools.registry import build_matchmaker_tools, build_server_tools


def _prompt_for_api_key() -> str | None:
    print("No ANTHROPIC_API_KEY found in the environment.")
    try:
        entered = getpass("Paste your Anthropic API key (hidden), or press Enter to cancel: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    return entered or None


def _store_api_key(api_key: str) -> str:
    dotenv_path = find_dotenv(usecwd=True) or os.path.join(os.getcwd(), ".env")
    set_key(dotenv_path, "ANTHROPIC_API_KEY", api_key)
    return dotenv_path


def _build_direct_client(settings: Settings) -> LlmClient | None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return build_client(settings)
    api_key = _prompt_for_api_key()
    if api_key is None:
        print("\nNo key provided — exiting. Set ANTHROPIC_API_KEY or paste a key next time.\n")
        return None
    dotenv_path = _store_api_key(api_key)
    print(f"Saved key to {dotenv_path} (gitignored) — you won't be asked again.\n")
    return build_client(settings, api_key=api_key)


def _build_selected_client(settings: Settings) -> LlmClient | None:
    if settings.provider is ModelProvider.BEDROCK:
        return build_client(settings)
    return _build_direct_client(settings)


def _verbose_requested() -> bool:
    return "-v" in sys.argv or "--verbose" in sys.argv or bool(os.environ.get("CELLAR_VERBOSE"))


def main() -> None:
    load_dotenv()
    settings = load_settings()
    verbose = _verbose_requested()
    client = _build_selected_client(settings)
    if client is None:
        return

    agent = ConsoleAgent(
        client=client,
        settings=settings,
        tools=build_matchmaker_tools(),
        server_tools=build_server_tools(settings),
        system=MATCHMAKER_SYSTEM_PROMPT,
        verbose=verbose,
    )

    print(f"cellar console agent — provider {settings.provider}, model {settings.model_name}")
    if verbose:
        print("(verbose: tool calls will be shown)")
    print("Type a message, or 'exit' to quit.\n")

    while True:
        try:
            user_message = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if user_message.lower() in {"exit", "quit"}:
            return
        if not user_message:
            continue
        try:
            reply = agent.send(user_message)
        except AuthenticationError:
            print("\nAuthentication failed — check your API key or Bedrock credentials.\n")
            return
        print(f"\ncellar > {reply}\n")
