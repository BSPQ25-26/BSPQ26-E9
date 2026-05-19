from pydantic import BaseModel, Field


class TestCleanupRequest(BaseModel):
    emails: list[str] = Field(default_factory=list)
    run_id: str | None = None
    purge_test_patterns: bool = True
