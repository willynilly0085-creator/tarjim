"""A small picture is enlarged before the subtitles are drawn, so the letters are sharp."""
from tarjim.models import Cue
from tarjim.render import burn
from tarjim.render.ass import Canvas, render_ass
from tarjim.render.mark import Mark
from tarjim.render.sharp import Enlarged, drawn_size, enlarged, grown


def test_a_464_line_download_is_drawn_at_1080p() -> None:
    by = enlarged((848, 464))
    assert by is not None and (by.width, by.height) == (1920, 1050)


def test_a_portrait_phone_video_fits_1080_wide() -> None:
    by = enlarged((480, 854))
    assert by is not None and by.width == 1080 and by.height == 1922 - 2


def test_a_picture_already_1080p_or_larger_is_left_as_it_is() -> None:
    assert enlarged((1920, 1080)) is None
    assert enlarged((3840, 2160)) is None
    assert enlarged((1080, 1920)) is None
    assert enlarged((0, 0)) is None


def test_the_size_comes_from_the_subtitle_files_own_layout() -> None:
    ass = render_ass([Cue(0.0, 1.0, text="مرحبا")], Canvas(848, 464))
    assert drawn_size(ass) == (848, 464)


def test_the_picture_is_enlarged_before_the_letters_are_drawn() -> None:
    by = Enlarged(1920, 1080, 1.5)
    plain = burn.drawing(None, by)
    assert plain[1] == f"scale=1920:1080:flags=lanczos,ass={burn.PLAIN}{burn.PLAYABLE}"
    graph = burn.drawing(Mark(20, 674, 32), by)[-1]
    assert graph.index("scale=1920:1080") < graph.index("ass=")
    assert "overlay=30:1011" in graph and "scale=48:48" in graph  # the logo grows with it


def test_the_logo_stays_put_when_nothing_is_enlarged() -> None:
    placed = Mark(20, 674, 32)
    assert grown(placed, None) is placed
    assert burn.drawing(None)[1] == f"ass={burn.PLAIN}{burn.PLAYABLE}"
