"""Deterministic local catalog seed entry point.

The seed deliberately uses only checked-in text and deterministic generation.
It is suitable for local startup and never calls Gemini or a remote catalog.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.features.books.models import Book
from app.features.users.models import User, UserRole


SEED_SLUG_PREFIX = "libraryos-seed-"
SEED_BOOK_COUNT = 600

# These accounts are intentionally reserved for local/evaluation use. They
# use the reserved example.test domain and are only created by the checked-in
# deterministic seed; never reuse these credentials in a shared deployment.
DEMO_ACCOUNTS: tuple[dict[str, str], ...] = (
    {
        "email": "member.demo@example.test",
        "password": "LibraryOS-member-demo-2026!",
        "display_name": "Demo Member",
        "role": "MEMBER",
    },
    {
        "email": "librarian.demo@example.test",
        "password": "LibraryOS-librarian-demo-2026!",
        "display_name": "Demo Librarian",
        "role": "LIBRARIAN",
    },
    {
        "email": "admin.demo@example.test",
        "password": "LibraryOS-admin-demo-2026!",
        "display_name": "Demo Administrator",
        "role": "ADMIN",
    },
)

_TITLES = (
    "The Atlas of Quiet Rivers",
    "Field Notes from the Night Garden",
    "A Practical Guide to Small Spaces",
    "The Long View of Climate",
    "Stories from the Edge of the Map",
    "Designing Better Questions",
    "The Everyday Mathematics Handbook",
    "Letters from a Shared Planet",
    "The Craft of Patient Attention",
    "An Introduction to Local History",
    "The Curious Cook's Notebook",
    "Making Sense of Modern Cities",
    "The Workshop of Useful Ideas",
    "A Reader's Guide to the Stars",
    "The Language of Good Neighbours",
    "Walking Through Deep Time",
    "The Small Museum of Ordinary Things",
    "A Field Guide to Digital Life",
    "The Ethics of Everyday Choices",
    "Learning in Public",
)

_AUTHORS = (
    "Maya Chen",
    "Jonah Williams",
    "Leila Haddad",
    "Samuel Okafor",
    "Priya Nair",
    "Elena Petrova",
    "Daniel Brooks",
    "Aisha Rahman",
    "Tomas Rivera",
    "Nora Svensson",
    "Hana Kim",
    "Mateo Silva",
    "Grace Mensah",
    "Arjun Mehta",
    "Sofia Laurent",
)

_CATEGORIES = (
    "Science",
    "History",
    "Technology",
    "Arts",
    "Nature",
    "Cooking",
    "Travel",
    "Society",
    "Mathematics",
    "Literature",
)

_DESCRIPTION_TOPICS = (
    "observations, practical examples, and questions for further reading",
    "clear explanations that connect everyday experience with wider ideas",
    "short essays and field notes designed for curious independent readers",
    "context, primary sources, and approachable guidance for a first study",
    "projects and reflections that reward careful attention and experimentation",
)


def _seed_demo_accounts(db: Session) -> bool:
    """Create or normalize the deterministic local evaluator accounts."""

    emails = [account["email"] for account in DEMO_ACCOUNTS]
    existing = {
        user.email: user
        for user in db.scalars(select(User).where(User.email.in_(emails))).all()
    }
    changed = False
    for account in DEMO_ACCOUNTS:
        expected_role = UserRole(account["role"])
        user = existing.get(account["email"])
        if user is None:
            db.add(
                User(
                    email=account["email"],
                    password_hash=hash_password(account["password"]),
                    display_name=account["display_name"],
                    role=expected_role,
                )
            )
            changed = True
            continue
        if user.display_name != account["display_name"]:
            user.display_name = account["display_name"]
            changed = True
        if user.role != expected_role:
            user.role = expected_role
            changed = True
    return changed


def seed() -> None:
    """Insert the deterministic local catalog, leaving existing rows intact."""

    if not get_settings().seed_demo_data:
        return
    with SessionLocal() as db:
        changed = _seed_demo_accounts(db)
        existing_slugs = set(
            db.scalars(
                select(Book.slug).where(Book.slug.like(f"{SEED_SLUG_PREFIX}%"))
            ).all()
        )
        books: list[Book] = []
        for index in range(1, SEED_BOOK_COUNT + 1):
            slug = f"{SEED_SLUG_PREFIX}{index:04d}"
            if slug in existing_slugs:
                continue
            title_base = _TITLES[(index - 1) % len(_TITLES)]
            author = _AUTHORS[(index - 1) % len(_AUTHORS)]
            category = _CATEGORIES[(index - 1) % len(_CATEGORIES)]
            topic = _DESCRIPTION_TOPICS[(index - 1) % len(_DESCRIPTION_TOPICS)]
            title = f"{title_base} — Library Edition {index:03d}"
            copies = 1 + (index % 5)
            books.append(
                Book(
                    isbn=f"978100{index:07d}",
                    slug=slug,
                    title=title,
                    author=author,
                    description=(
                        f"{title} by {author} explores {topic}. "
                        f"Filed in {category} for local catalog search and reading."
                    ),
                    category=category,
                    publication_year=1950 + (index % 76),
                    total_copies=copies,
                    available_copies=copies,
                )
            )
        if books:
            db.add_all(books)
            changed = True
        if changed:
            db.commit()


if __name__ == "__main__":
    seed()
