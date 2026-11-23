import pytest

from macave.app import create_app


@pytest.fixture
def app(tmp_path):
    # Base vierge par test ; CSRF coupé (testé dans test_csrf.py)
    return create_app({"TESTING": True, "SECRET_KEY": "cle-de-test", "CSRF_ACTIVE": False,
                       "DATABASE": str(tmp_path / "test.db")})


@pytest.fixture
def client(app):
    return app.test_client()
