import os
import pytest
from unittest.mock import Mock

from aiogtts.tts import aiogTTS, aiogTTSError
from aiogtts.langs import _main_langs
from aiogtts.lang import _extra_langs

# Testing all languages takes some time.
# Set TEST_LANGS envvar to choose languages to test.
#  * 'main': Languages extracted from the Web
#  * 'extra': Language set in Languages.EXTRA_LANGS
#  * 'all': All of the above
#  * <csv>: Languages tags list to test
# Unset TEST_LANGS to test everything ('all')
# See: langs_dict()

"""Construct a dict of suites of languages to test.
{ '<suite name>' : <list or dict of language tags> }

ex.: { 'fetch' : {'en': 'English', 'fr': 'French'},
       'extra' : {'en': 'English', 'fr': 'French'} }
ex.: { 'environ' : ['en', 'fr'] }
"""
env = os.environ.get('TEST_LANGS')
if not env or env == 'all':
    langs = _main_langs()
    langs.update(_extra_langs())
elif env == 'main':
    langs = _main_langs()
elif env == 'extra':
    langs = _extra_langs()
else:
    env_langs = {lang: lang for lang in env.split(',') if lang}
    langs = env_langs


@pytest.mark.asyncio
@pytest.mark.parametrize('lang', langs.keys(), ids=list(langs.values()))
async def test_tts(tmp_path, lang):
    """Test all supported languages and file save"""

    text = 'This is a test'
    for slow in (False, True):
        filename = tmp_path / f'test_{lang}_.mp3'
        tts = aiogTTS()
        await tts.save(text, filename, lang=lang, slow=slow, lang_check=False)

        assert filename.stat().st_size > 1500


@pytest.mark.asyncio
async def test_unsupported_language_check(tmp_path):
    """Raise ValueError on unsupported language (with language check)"""
    lang = 'xx'
    text = 'Lorem ipsum'
    check = True
    with pytest.raises(ValueError):
        await aiogTTS().save(text, tmp_path / 'test.mp3', lang=lang, lang_check=check)


@pytest.mark.asyncio
async def test_empty_string(tmp_path):
    """Raise AssertionError on empty string"""
    text = ''
    with pytest.raises(AssertionError):
        await aiogTTS().save(text, tmp_path / 'test.mp3')


@pytest.mark.asyncio
async def test_no_text_parts(tmp_path):
    """Raises AssertionError on no content to send to API (no text_parts)"""
    text = '                                                                                                     ..,\n'
    with pytest.raises(AssertionError):
        filename = tmp_path / 'no_content.txt'
        tts = aiogTTS()
        await tts.save(text, filename)


@pytest.mark.asyncio
async def test_bad_fp_type():
    """Raise TypeError if fp is not a file-like object (no .write())"""
    with pytest.raises(TypeError):
        await aiogTTS().write_to_fp('test', 5)


@pytest.mark.asyncio
async def test_save(tmp_path):
    """Save .mp3 file successfully"""
    filename = tmp_path / 'save.mp3'
    await aiogTTS().save('test', filename)

    assert filename.stat().st_size > 2000


def test_msg():
    """Test aiogTTSError internal exception handling
    Set exception message successfully"""
    error1 = aiogTTSError('test')
    assert 'test' == error1.msg

    error2 = aiogTTSError()
    assert error2.msg is None


def test_infer_msg():
    """Infer message successfully based on context"""

    # Without response:

    # Bad TLD
    tts_tld = Mock(tld='invalid')
    error_tld = aiogTTSError(tts=tts_tld)
    assert error_tld.msg == "Failed to connect. Probable cause: Host 'https://translate.google.invalid/' is not reachable"

    # With response:

    # 403
    tts403 = Mock()
    response403 = Mock(status=403, reason='aaa')
    error403 = aiogTTSError(tts=tts403, response=response403)
    assert error403.msg == '403 (aaa) from TTS API. Probable cause: Bad token or upstream API changes'

    # 200 (and not lang_check)
    tts200 = Mock()
    response404 = Mock(status=200, reason='bbb')
    error200 = aiogTTSError(tts=tts200, response=response404)
    assert error200.msg == "200 (bbb) from TTS API. Probable cause: No audio stream in response. Most probably the problem is in an unsupported language"

    # >= 500
    tts500 = Mock()
    response500 = Mock(status=500, reason='ccc')
    error500 = aiogTTSError(tts=tts500, response=response500)
    assert error500.msg == '500 (ccc) from TTS API. Probable cause: Upstream API error. Try again later.'

    # Unknown (ex. 100)
    tts100 = Mock()
    response100 = Mock(status=100, reason='ddd')
    error100 = aiogTTSError(tts=tts100, response=response100)
    assert error100.msg == '100 (ddd) from TTS API. Probable cause: Unknown'


@pytest.mark.asyncio
async def test_web_request(tmp_path):
    """Test Web Requests"""

    text = 'Lorem ipsum'

    """Raise aiogTTSError on unsupported language (without language check)"""
    lang = 'xx'
    check = False

    with pytest.raises(aiogTTSError):
        filename = tmp_path / 'xx.txt'
        tts = aiogTTS()
        await tts.save(text, filename, lang=lang, lang_check=check)


if __name__ == '__main__':
    pytest.main(['-x', __file__])
