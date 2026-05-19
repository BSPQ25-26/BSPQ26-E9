from app.models.rating import Rating
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.test_cleanup_service import cleanup_test_users


def test_cleanup_test_users_removes_matching_users_but_keeps_seed_users(client, db):
    auth_service = AuthService()
    auth_service.register(db, "alice@example.com", "alice123")
    auth_service.register(db, "seller-purchase_a1b2c3d4@example.com", "StrongPass123!")
    auth_service.register(db, "perf-deadbeef-seller-1@example.com", "PerfSeller!123")

    result = cleanup_test_users(
        db,
        emails=["seller-purchase_a1b2c3d4@example.com"],
        run_id="deadbeef",
        purge_test_patterns=True,
    )

    assert result["deleted_users"] == 2
    assert db.query(User).filter(User.email == "alice@example.com").count() == 1
    assert db.query(User).filter(User.email.like("perf-%")).count() == 0
    assert (
        db.query(User)
        .filter(User.email == "seller-purchase_a1b2c3d4@example.com")
        .count()
        == 0
    )
    assert db.query(Rating).count() == 0
