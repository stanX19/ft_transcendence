"""PostgreSQL full-text search schema contracts for catalog RAG."""

from __future__ import annotations

from sqlalchemy import text


CATALOG_SEARCH_FIELDS = ("title", "author", "description", "category")


def _search_definitions(connection) -> tuple[list[dict], list[str]]:
    """Return tsvector column definitions and PostgreSQL index definitions."""

    columns = list(
        connection.execute(
            text(
                """
                SELECT
                    a.attname AS name,
                    a.attgenerated AS generated,
                    pg_get_expr(ad.adbin, ad.adrelid) AS expression
                FROM pg_attribute AS a
                LEFT JOIN pg_attrdef AS ad
                    ON ad.adrelid = a.attrelid
                   AND ad.adnum = a.attnum
                WHERE a.attrelid = 'public.books'::regclass
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                  AND a.atttypid = 'tsvector'::regtype
                """
            )
        ).mappings()
    )
    indexes = list(
        connection.execute(
            text(
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'books'
                """
            )
        ).scalars()
    )
    return columns, indexes


def test_books_have_a_postgresql_fts_document_and_gin_index() -> None:
    from app.core.database import engine

    with engine.connect() as connection:
        columns, indexes = _search_definitions(connection)

    assert columns or any("to_tsvector" in definition.lower() for definition in indexes), (
        "books must expose a generated/expression PostgreSQL full-text search document"
    )

    gin_indexes = [
        definition
        for definition in indexes
        if "using gin" in definition.lower()
    ]
    assert gin_indexes, "books must have a GIN index for catalog full-text retrieval"


def test_catalog_fts_definition_includes_all_useful_text_fields() -> None:
    from app.core.database import engine

    with engine.connect() as connection:
        columns, indexes = _search_definitions(connection)

    generated_expressions = [
        str(column["expression"] or "") for column in columns
    ]
    gin_index_definitions = [
        definition
        for definition in indexes
        if "using gin" in definition.lower()
    ]
    searchable_sql = " ".join(
        generated_expressions + gin_index_definitions
    ).lower()

    for field in CATALOG_SEARCH_FIELDS:
        assert field in searchable_sql, (
            f"catalog FTS definition must index the {field} field"
        )


def test_catalog_fts_does_not_add_vector_or_embedding_storage() -> None:
    from app.core.database import engine

    with engine.connect() as connection:
        table_names = {
            str(name).lower()
            for name in connection.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    """
                )
            ).scalars()
        }
        vector_extensions = {
            str(name).lower()
            for name in connection.execute(
                text("SELECT extname FROM pg_extension")
            ).scalars()
        }

    assert not any(
        "embedding" in name or name == "vectors" or name.endswith("_vector")
        for name in table_names
    )
    assert "vector" not in vector_extensions
