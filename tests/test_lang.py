import pytest
from aiogtts.lang import _fallback_deprecated_lang
from aiogtts.langs import _main_langs


def test_main_langs():
    scraped_langs = _main_langs()
    assert 'en' in scraped_langs


def test_deprecated_lang():
    with pytest.deprecated_call():
        assert _fallback_deprecated_lang('en-gb') == 'en'


if __name__ == '__main__':
    pytest.main(['-x', __file__])
