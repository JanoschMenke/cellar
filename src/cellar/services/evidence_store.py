from contextvars import ContextVar

from cellar.schemas.evidence import EvidenceRecord


class EvidenceStore:
    def __init__(self) -> None:
        self._records: list[EvidenceRecord] = []

    def record(
        self,
        tool: str,
        tool_input: dict[str, object],
        data: object | None,
        is_error: bool = False,
    ) -> None:
        self._records.append(
            EvidenceRecord(tool=tool, input=dict(tool_input), data=data, is_error=is_error)
        )

    def by_tool(self, tool: str) -> list[EvidenceRecord]:
        return [r for r in self._records if r.tool == tool and not r.is_error]

    def latest(self, tool: str) -> EvidenceRecord | None:
        matches = self.by_tool(tool)
        return matches[-1] if matches else None

    def records(self) -> list[EvidenceRecord]:
        return list(self._records)

    def clear(self) -> None:
        self._records.clear()


_current_store: ContextVar[EvidenceStore | None] = ContextVar(
    "cellar_evidence_store", default=None
)


def bind_store(store: EvidenceStore) -> None:
    _current_store.set(store)


def current_store() -> EvidenceStore | None:
    return _current_store.get()
