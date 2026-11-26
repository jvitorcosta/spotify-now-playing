from xml.etree import ElementTree

import pytest

from api import orchestrator

from .test_now_playing_json import TRACK, Fake, client


def get(monkeypatch, service, query=""):
    return client(monkeypatch, service).get(f"/api/card.svg{query}")


def test_playing_card_says_listening_and_shows_the_moving_on_badge(monkeypatch):
    r = get(monkeypatch, Fake(TRACK))
    svg = r.get_data(as_text=True)
    assert r.status_code == 200 and r.mimetype == "image/svg+xml"
    assert r.headers["Cache-Control"] == "max-age=0, s-maxage=1"
    assert "<title>Listening: Taxi Lunar</title>" in svg and "Geraldo Azevedo" in svg
    assert 'class="on"' in svg and "@keyframes bars0" in svg
    ElementTree.fromstring(svg)  # well formed, or GitHub shows a broken image


def test_idle_card_says_last_played_without_the_badge(monkeypatch):
    svg = get(monkeypatch, Fake(TRACK | {"is_playing": False})).get_data(as_text=True)
    assert "<title>Last played: Taxi Lunar</title>" in svg
    assert 'class="on"' not in svg


def test_asks_for_the_latest_track(monkeypatch):
    service = Fake(TRACK)
    get(monkeypatch, service)
    assert service.latest is True


@pytest.mark.parametrize(("query", "width", "colour"), [
    ("", 420, "#150d24"), ("?theme=light", 420, "#f1e8ff"), ("?wide=1", 840, "#150d24"),
    ("?theme=<script>", 420, "#150d24"),
])
def test_theme_and_width(monkeypatch, query, width, colour):
    svg = get(monkeypatch, Fake(TRACK), query).get_data(as_text=True)
    assert f'width="{width}"' in svg and colour in svg and "<script>" not in svg


def test_song_text_is_escaped_and_clipped(monkeypatch):
    long = "<b>&" + "x" * 200
    svg = get(monkeypatch, Fake(TRACK | {"track_name": long, "artist_name": long})).get_data(as_text=True)
    assert "<b>" not in svg and "…" in svg
    ElementTree.fromstring(svg)


def test_service_error_still_returns_a_card(monkeypatch):
    r = get(monkeypatch, Fake(exc=RuntimeError("secret detail")))
    svg = r.get_data(as_text=True)
    assert r.status_code == 200 and "secret detail" not in svg
    assert "Spotify is not answering" in svg
    ElementTree.fromstring(svg)


def test_route_is_registered():
    assert any(rule.rule == "/api/card.svg" for rule in orchestrator.app.url_map.iter_rules())


def test_clicking_the_card_opens_the_song_it_shows(monkeypatch):
    service = Fake(TRACK)
    r = client(monkeypatch, service).get("/redirect")
    assert service.latest is True  # idle: the latest song, as on the card, not a random recent one
    assert r.status_code == 302 and r.headers["Location"] == TRACK["track_url"]
