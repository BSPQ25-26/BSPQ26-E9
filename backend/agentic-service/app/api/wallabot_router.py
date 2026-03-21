from fastapi import APIRouter

router = APIRouter(prefix="/wallabot", tags=["wallabot"])


@router.post("/category")
def suggest_category_stub() -> dict[str, object]:
    return {
        "suggested_category": "Electronics",
        "confidence": 0.9,
        "source": "mock",
        "message": "Sprint 1 stub response. Real AI integration arrives in Sprint 2.",
    }
