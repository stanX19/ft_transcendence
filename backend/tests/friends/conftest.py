"""Shared fixtures for friendship tests."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import pytest


@pytest.fixture
def registered_friend(register_user, client_factory) -> Callable[..., tuple[object, dict]]:
    def make_user(display_name: str):
        client = client_factory()
        response = register_user(client, display_name=display_name)
        assert response.status_code == 201, response.text
        return client, response.json()["user"]

    return make_user
