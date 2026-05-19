import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.test_cleanup import TestCleanupRequest
from app.services.test_cleanup_service import cleanup_test_users, is_test_cleanup_enabled

router = APIRouter(prefix="/internal/test", tags=["test-cleanup"])


def _verify_secret(x_test_cleanup_secret: str | None = Header(default=None)) -> None:
    if not is_test_cleanup_enabled():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test cleanup is disabled",
        )
    expected = os.getenv("TEST_CLEANUP_SECRET", "dev-test-cleanup")
    if not x_test_cleanup_secret or x_test_cleanup_secret != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid test cleanup secret",
        )


@router.post("/cleanup")
def cleanup_test_data(
    payload: TestCleanupRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_secret),
):
    return cleanup_test_users(
        db,
        emails=payload.emails,
        run_id=payload.run_id,
        purge_test_patterns=payload.purge_test_patterns,
    )
