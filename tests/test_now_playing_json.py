import pytest

from api import orchestrator

TRACK = {"is_playing": True, "track_name": "Taxi Lunar", "artist_name": "Geraldo Azevedo",
         "album_name": "x", "album_art_url": "https://i.scdn.co/image/abc", "track_url": "https://open.spotify.com/track/1"}


class Fake:
    def __init__(self, result=None, exc=None):
        self.result, self.exc = result, exc

    def get_now_playing(self, latest=False):
        self.latest = latest
        if self.exc:
            raise self.exc
        return self.result


def no_network(url, timeout):
    raise orchestrator.requests.RequestException("no network in tests")


def client(monkeypatch, service):
    monkeypatch.setattr(orchestrator, "get_active_service", lambda: ("spotify", service))
    if orchestrator.requests.get is orchestrator.requests.api.get:  # a test's own stub wins
        monkeypatch.setattr(orchestrator.requests, "get", no_network)
    return orchestrator.app.test_client()


def test_returns_track_as_json(monkeypatch):
    r = client(monkeypatch, Fake(TRACK)).get("/api/now-playing.json")
    assert r.status_code == 200 and r.is_json
    assert r.get_json() == {"playing": True, "title": "Taxi Lunar", "artist": "Geraldo Azevedo",
                            "cover": "https://i.scdn.co/image/abc", "url": "https://open.spotify.com/track/1"}
    assert r.headers["Access-Control-Allow-Origin"] == "https://jvitorcosta.github.io"
    assert r.headers["Cache-Control"] == "s-maxage=10"


def test_service_error_is_503_json_with_cors(monkeypatch):
    r = client(monkeypatch, Fake(exc=RuntimeError("boom"))).get("/api/now-playing.json")
    assert r.status_code == 503
    assert r.get_json() == {"error": "now playing unavailable"}  # never the internal error text
    assert r.headers["Access-Control-Allow-Origin"] == "https://jvitorcosta.github.io"


def test_svg_route_unchanged(monkeypatch):
    monkeypatch.setattr(orchestrator, "make_svg", lambda *a, **k: "<svg/>")
    r = client(monkeypatch, Fake(TRACK)).get("/api/orchestrator")
    assert r.mimetype == "image/svg+xml"


def test_json_asks_for_the_latest_track(monkeypatch):
    fake = Fake(TRACK)
    client(monkeypatch, fake).get("/api/now-playing.json")
    assert fake.latest is True


def test_spotify_latest_picks_the_most_recent_track(monkeypatch):
    from api import spotify

    def api_get(url, retry_on_auth_error=True):
        if url == spotify.spotify_config.now_playing_url:
            raise spotify.NoTracksError("Spotify")
        return {"items": [{"track": {"name": f"song {i}"}} for i in range(10)]}

    monkeypatch.setattr(spotify, "_api_get", api_get)
    picked = []

    def stop(item, is_playing):
        picked.append(item["name"])
        raise LookupError  # stop before the audio-features call

    monkeypatch.setattr(spotify, "_extract_track_info", stop)
    for _ in range(20):  # the default picks at random; latest must not
        with pytest.raises(LookupError):
            spotify.get_now_playing(latest=True)
    assert set(picked) == {"song 0"}


class Img:
    def __init__(self, body, ctype):
        self.content, self.headers = body, {"Content-Type": ctype}

    def raise_for_status(self):
        pass


def test_cover_is_also_sent_inline(monkeypatch):
    # The site shows the cover from this data URI, so visitors' browsers never call Spotify's CDN.
    calls = []

    def get(url, timeout):
        calls.append((url, timeout))
        return Img(b"\xff\xd8jpeg", "image/jpeg")

    monkeypatch.setattr(orchestrator.requests, "get", get)
    body = client(monkeypatch, Fake(TRACK)).get("/api/now-playing.json").get_json()
    assert body["cover_data"] == "data:image/jpeg;base64,/9hqcGVn"
    assert calls == [("https://i.scdn.co/image/abc", 2)]


def test_cover_data_left_out_when_the_image_fails(monkeypatch):
    def get(url, timeout):
        raise orchestrator.requests.RequestException("timeout")

    monkeypatch.setattr(orchestrator.requests, "get", get)
    r = client(monkeypatch, Fake(TRACK)).get("/api/now-playing.json")
    assert r.status_code == 200 and "cover_data" not in r.get_json()


def test_cover_data_left_out_for_a_non_image(monkeypatch):
    monkeypatch.setattr(orchestrator.requests, "get", lambda url, timeout: Img(b"<html>", "text/html"))
    assert "cover_data" not in client(monkeypatch, Fake(TRACK)).get("/api/now-playing.json").get_json()
