import pytest

from bcdl import api


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError("unexpected HTTP error in this test")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payload):
        self._payload = payload

    def get(self, url, **kwargs):
        return FakeResponse(self._payload)

    def post(self, url, **kwargs):
        return FakeResponse(self._payload)


def test_expired_cookie_raises_bandcamp_error_not_key_error():
    """Bandcamp returns HTTP 200 with an error body for a rejected cookie."""
    session = FakeSession({"error": True, "error_message": "must be logged in"})

    with pytest.raises(api.BandcampError) as excinfo:
        api.get_fan_id(session)

    assert "must be logged in" in str(excinfo.value)


def test_auth_error_message_points_at_reconfiguring():
    session = FakeSession({"error": True, "error_message": "must be logged in"})

    with pytest.raises(api.BandcampError) as excinfo:
        api.get_fan_id(session)

    assert "configure" in str(excinfo.value)


def test_missing_fan_id_raises_bandcamp_error():
    session = FakeSession({"something_else": 1})

    with pytest.raises(api.BandcampError):
        api.get_fan_id(session)


def test_valid_response_returns_fan_id():
    session = FakeSession({"fan_id": 601001})

    assert api.get_fan_id(session) == 601001


def test_collection_items_surfaces_api_error():
    session = FakeSession({"error": True, "error_message": "must be logged in"})

    with pytest.raises(api.BandcampError):
        api.get_collection_items(session, fan_id=601001)
