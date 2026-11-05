from api import orchestrator

TRACK = {"is_playing": True, "track_name": "Taxi Lunar", "artist_name": "Geraldo Azevedo",
         "album_name": "x", "album_art_url": "https://i.scdn.co/image/abc", "track_url": "https://open.spotify.com/track/1"}


class Fake:
    def __init__(self, result=None, exc=None):
        self.result, self.exc = result, exc

    def get_now_playing(self):
        if self.exc:
            raise self.exc
        return self.result


def client(monkeypatch, service):
    monkeypatch.setattr(orchestrator, "get_active_service", lambda: ("spotify", service))
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
