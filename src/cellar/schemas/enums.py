from enum import StrEnum


class AgentRole(StrEnum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    EXPERIMENTER = "experimenter"
    CRITIC = "critic"
    REPORTER = "reporter"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class HypothesisState(StrEnum):
    PROPOSED = "proposed"
    TESTING = "testing"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"


class ToolKind(StrEnum):
    LITERATURE_SEARCH = "literature_search"
    CODE_EXECUTION = "code_execution"
    DATA_QUERY = "data_query"
    SIMULATION = "simulation"
