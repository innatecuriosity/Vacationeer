"""Tests for vacationeer.utils — shared utility functions."""
from vacationeer.utils import slugify


class TestSlugify:
    def test_simple_name(self):
        assert slugify("Mercado Central") == "mercado-central"

    def test_special_characters(self):
        # Accented chars are kept (they match \w), punctuation is stripped
        assert slugify("L'Hemisfèric & Príncipe") == "lhemisfèric-príncipe"

    def test_leading_trailing_whitespace(self):
        assert slugify("  Hello World  ") == "hello-world"

    def test_underscores_replaced(self):
        assert slugify("some_thing") == "some-thing"

    def test_multiple_hyphens_collapsed(self):
        assert slugify("foo---bar") == "foo-bar"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_already_slug(self):
        assert slugify("valencia-cathedral") == "valencia-cathedral"
