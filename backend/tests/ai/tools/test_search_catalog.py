"""Safe catalog search tool contracts."""

from __future__ import annotations


def test_search_catalog_delegates_catalog_service_and_bounds_results(
    db_session,
    create_ai_book,
) -> None:
    from app.features.ai.tools import search_catalog

    marker = "AI tool search marker"
    expected = create_ai_book(title=marker)
    for index in range(8):
        create_ai_book(title=f"{marker} {index}")

    results = search_catalog(db_session, query=marker, limit=99)

    assert len(results) <= 5
    assert any(item["book_id"] == expected.id for item in results)
