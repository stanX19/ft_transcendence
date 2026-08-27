"""Deterministic local evaluator-account and role smoke contracts."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import func, select


def test_seed_creates_reproducible_local_demo_accounts(db_session) -> None:
    from app.features.users.models import User
    from app.seed import DEMO_ACCOUNTS, seed

    seed()
    first_count = db_session.scalar(
        select(func.count()).select_from(User).where(User.email.like("%.demo@example.test"))
    ) or 0
    accounts = {
        user.email: user
        for user in db_session.scalars(
            select(User).where(User.email.like("%.demo@example.test"))
        ).all()
    }

    assert first_count == len(DEMO_ACCOUNTS) == 3
    assert set(accounts) == {account["email"] for account in DEMO_ACCOUNTS}
    assert {user.role.value for user in accounts.values()} == {
        "MEMBER",
        "LIBRARIAN",
        "ADMIN",
    }
    assert all(user.display_name for user in accounts.values())

    seed()
    second_count = db_session.scalar(
        select(func.count()).select_from(User).where(User.email.like("%.demo@example.test"))
    ) or 0
    assert second_count == first_count


def test_seeded_demo_accounts_exercise_core_role_boundaries(
    client_factory,
    login_user,
) -> None:
    from app.seed import DEMO_ACCOUNTS, seed

    seed()
    clients = {account["role"]: client_factory() for account in DEMO_ACCOUNTS}
    for account in DEMO_ACCOUNTS:
        login = login_user(
            clients[account["role"]],
            email=account["email"],
            password=account["password"],
        )
        assert login.status_code == 200, login.text
        assert login.json()["user"]["role"] == account["role"]

    book_payload = {
        "title": f"Demo role smoke book {uuid4().hex}",
        "author": "Evaluation Fixture",
        "description": "A local role smoke-test record.",
        "category": "Testing",
        "total_copies": 1,
    }
    assert clients["MEMBER"].post("/api/books", json=book_payload).status_code == 403
    assert clients["LIBRARIAN"].post("/api/books", json=book_payload).status_code == 201
    assert clients["ADMIN"].get("/api/admin/users").status_code == 200
