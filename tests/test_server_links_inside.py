"""The local server downloads no link that points into this computer or its network."""
import pytest

from tarjim.phone import links


@pytest.mark.parametrize("url", ["http://127.0.0.1:8080/x.mp4", "http://[::1]/x", "https://10.0.0.5/v",
                                 "http://localhost/v", "http://printer.lan/v", "ftp://example.com/v",
                                 "http://169.254.169.254/latest/meta-data"])
def test_a_link_inside_is_refused(url: str) -> None:
    assert not links.linkable(url)


def test_a_public_name_that_resolves_inside_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(links, "addresses", lambda _host: ["93.184.215.14", "192.168.0.2"])
    assert not links.linkable("https://looks-public.example/v")


def test_a_public_link_is_taken(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(links, "addresses", lambda _host: ["142.250.74.46"])
    assert links.linkable("https://www.youtube.com/watch?v=x")


def test_a_name_that_does_not_resolve_now_is_left_to_the_download(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(links, "addresses", lambda _host: [])
    assert links.linkable("https://www.youtube.com/watch?v=x")
