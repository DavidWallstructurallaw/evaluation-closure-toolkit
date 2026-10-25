"""Deterministic, shared graph-work limits, independent of the host clock."""

from dataclasses import dataclass, field


class WorkLimit(RuntimeError):
    """No next edge may be examined under the remaining work allowance."""

    def __init__(self, *, run_exhausted: bool) -> None:
        self.run_exhausted = run_exhausted
        super().__init__("resource_limit")


@dataclass
class RunBudget:
    limit: int = 2_000_000
    used: int = 0
    path_limit: int = 100_000
    path_used: int = 0


@dataclass
class RequestBudget:
    run: RunBudget | None = field(default=None)
    limit: int = 1_000_000
    used: int = 0
    partial_result: dict | None = field(default=None, init=False)
    partial_findings: list = field(default_factory=list, init=False)
    profile_progress: dict | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.run is None:
            self.run = RunBudget()

    def charge(self, n: int = 1) -> None:
        """Reserve work before processing or retaining its edge references."""
        if n < 0:
            raise ValueError("negative_work")
        run_exhausted = self.run.used + n > self.run.limit
        if run_exhausted or self.used + n > self.limit:
            raise WorkLimit(run_exhausted=run_exhausted)
        self.used += n
        self.run.used += n

    def retain_paths(self, n: int) -> None:
        """Reserve finite path references before publishing a witness atomically."""
        if n < 0:
            raise ValueError("negative_work")
        if self.run.path_used + n > self.run.path_limit:
            raise WorkLimit(run_exhausted=True)
        self.charge(n)
        self.run.path_used += n
