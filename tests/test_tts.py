import pytest
from unittest.mock import Mock

from aiogtts import aiogTTS, aiogTTSError
from aiogtts.lang import EXTRA_LANGS

# Testing all languages takes some time.
# Set TEST_LANGS envvar to choose languages to test.
#  * 'fetch': Languages fetched from the Web
#  * 'extra': Languagee set in Languages.EXTRA_LANGS
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

langs = EXTRA_LANGS


@pytest.mark.asyncio
@pytest.mark.parametrize('lang', langs.keys(), ids=list(langs.values()))
async def test_TTS(tmp_path, lang):
    for slow in (False, True):
        filename = tmp_path / f'test_{lang}_.mp3'
        await aiogTTS().save(text='This is a test', savefile=filename, lang=lang, slow=slow)
        assert filename.stat().st_size > 2000


@pytest.mark.asyncio
async def test_unsupported_language_check():
    with pytest.raises(ValueError):
        await aiogTTS().write_to_fp(text='test', fp=None, lang='wrong', lang_check=True)


@pytest.mark.asyncio
async def test_empty_string():
    with pytest.raises(ValueError):
        await aiogTTS().write_to_fp(text='', fp=None)


@pytest.mark.asyncio
async def test_no_text_parts():
    text = "                                                             ..,\n"
    with pytest.raises(ValueError):
        await aiogTTS().write_to_fp(text=text, fp=None)


@pytest.mark.asyncio
async def test_bad_fp_type():
    with pytest.raises(TypeError):
        await aiogTTS().write_to_fp('text', fp='not-file-like')


@pytest.mark.asyncio
async def test_save(tmp_path):
    filename = tmp_path / 'save.mp3'
    await aiogTTS().save(text='test', savefile=filename)
    assert filename.stat().st_size > 2000


def test_msg():
    error1 = aiogTTSError('test')
    assert 'test' == error1.msg

    error2 = aiogTTSError()
    assert error2.msg is None


def test_infer_msg():
    response403 = Mock(status=403, reason='aaa')
    error403 = aiogTTSError(lang='en', lang_check=True, response=response403)
    assert error403.msg == "403 (aaa) from TTS API. Probable cause: Bad token or upstream API changes"

    response404 = Mock(status=404, reason='bbb')
    error404 = aiogTTSError(lang='wrong', lang_check=False, response=response404)
    assert error404.msg == "404 (bbb) from TTS API. Probable cause: Unsupported language 'wrong'"

    response500 = Mock(status=500, reason='ccc')
    error500 = aiogTTSError(lang='en', lang_check=True, response=response500)
    assert error500.msg == "500 (ccc) from TTS API. Probable cause: Upstream API error. Try again later"

    response100 = Mock(status=100, reason='ddd')
    error100 = aiogTTSError(lang='en', lang_check=True, response=response100)
    assert error100.msg == "100 (ddd) from TTS API. Probable cause: Unknown"


@pytest.mark.asyncio
async def test_no_lang_check(tmp_path):
    with pytest.raises(aiogTTSError):
        filename = tmp_path / 'xx.mp3'
        await aiogTTS().save(text='test', savefile=filename, lang='wrong', lang_check=False)


if __name__ == '__main__':
    pytest.main(['-x', __file__])
