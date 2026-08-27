"""OpenAPI documentation contracts for the integration surface."""

from __future__ import annotations


def test_public_api_openapi_documents_key_scheme_and_all_crud_operations(client) -> None:
    response = client.get("/api/openapi.json")

    assert response.status_code == 200, response.text
    schema = response.json()
    schemes = schema["components"]["securitySchemes"]
    assert any(
        scheme.get("type") == "apiKey" and scheme.get("name") == "X-API-Key"
        for scheme in schemes.values()
    )
    api_key_scheme_names = {
        name
        for name, scheme in schemes.items()
        if scheme.get("type") == "apiKey" and scheme.get("name") == "X-API-Key"
    }

    paths = schema["paths"]
    expected_operations = {
        ("/public-api/v1/books", "get"),
        ("/public-api/v1/books", "post"),
        ("/public-api/v1/books/{book_id}", "get"),
        ("/public-api/v1/books/{book_id}", "put"),
        ("/public-api/v1/books/{book_id}", "patch"),
        ("/public-api/v1/books/{book_id}", "delete"),
    }
    for path, method in expected_operations:
        assert method in paths[path]
        assert any(
            scheme_name in api_key_scheme_names
            for operation_security in paths[path][method].get("security", [])
            for scheme_name in operation_security
        )
