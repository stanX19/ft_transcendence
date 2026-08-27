"""Deterministic local catalog seed entry point.

The seed deliberately uses only checked-in text and deterministic generation.
It is suitable for local startup and never calls Gemini or a remote catalog.
"""

from __future__ import annotations

from sqlalchemy import select

from app.core.database import SessionLocal
from app.features.books.models import Book


SEED_SLUG_PREFIX = "libraryos-seed-"
SEED_BOOK_COUNT = 600

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


def seed() -> None:
    """Insert the deterministic local catalog, leaving existing rows intact."""

    with SessionLocal() as db:
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
            db.commit()


if __name__ == "__main__":
    seed()
