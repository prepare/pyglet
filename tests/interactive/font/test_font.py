import pytest

from .font_test_base import font_fixture

import pyglet
from tests.annotations import Platform


@pytest.mark.parametrize('question,color', [
    ('Default font should appear at 0.3 opacity (faint grey)', (0, 0, 0, 0.3)),
    ('Text should not be visible due to opacity 0.0', (0, 0, 0, 0)),
    ('Default font should appear at full opacity (black)', (0, 0, 0, 1)),
    ('Default font should appear blue', (0, 0, 1, 1)),
    ('Default font should appear red', (1, 0, 0, 1)),
    ])
def test_color(font_fixture, question, color):
    """Test that font colour is applied correctly."""
    font_fixture.test_font(question=question,
                           color=color)



def test_default_font(font_fixture):
    """Test that a font with no name given still renders using some sort
    of default system font.
    """
    font_fixture.test_font(
        question='Font should be rendered using a default system font',
        font_name=''
        )


def test_system_font(font_fixture):
    """Test that a font likely to be installed on the computer can be
    loaded and displayed correctly.

    One window will open, it should show "Quickly brown fox" at 24pt using:

    * "Helvetica" on Mac OS X
    * "Arial" on Windows
    * "Arial" on Linux
    """

    if pyglet.compat_platform in Platform.OSX:
        font_name = 'Helvetica'
    elif pyglet.compat_platform in Platform.WINDOWS:
        font_name = 'Arial'
    else:
        font_name = 'Arial'

    font_fixture.test_font(
        font_name=font_name,
        question='"Quickly brown fox" should be shown at 24pt using font ' + font_name
        )


def test_bullet_glyphs(font_fixture):
    """Test that rendering of unicode glyphs works."""

    font_fixture.test_font(
        font_size = 60,
        text = u'\u2022'*5,
        question = 'You should see 5 bullet glyphs.'
        )


def test_large_font(font_fixture):
    "Render a font using a very large size. Tests issue 684."

    font_fixture.test_font(
        font_name='Arial',
        font_size=292,
        text='trawant',
        width=1000,
        height=400,
        question='Is the word "trawant" rendered in a large font?'
        )

