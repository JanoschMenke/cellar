import json
import urllib.error
import urllib.request
from typing import Any, cast


class HttpError(RuntimeError):
    def __init__(self, status: int, url: str, body: str) -> None:
        super().__init__(f"HTTP {status} for {url}: {body}")
        self.status = status
        self.url = url
        self.body = body


def _send(request: urllib.request.Request, timeout: int) -> bytes:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return cast(bytes, response.read())
    except urllib.error.HTTPError as error:
        body = error.read().decode(errors="replace")
        raise HttpError(error.code, request.full_url, body) from error


def get_bytes(url: str, *, headers: dict[str, str] | None = None, timeout: int = 60) -> bytes:
    return _send(urllib.request.Request(url, headers=headers or {}), timeout)


def get_json(url: str, *, headers: dict[str, str] | None = None, timeout: int = 60) -> Any:
    return json.loads(get_bytes(url, headers=headers, timeout=timeout).decode())


def post_json(
    url: str,
    payload: dict[str, object],
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 60,
) -> Any:
    merged = {"Content-Type": "application/json", **(headers or {})}
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=merged)
    return json.loads(_send(request, timeout).decode())
