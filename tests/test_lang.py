import pytest
import aiohttp
from aiogtts.lang import tts_langs, _fetch_langs, EXTRA_LANGS


@pytest.mark.asyncio
async def test_fetch_langs():
    headers = {'User-Agent': 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0'}
    session = aiohttp.ClientSession(headers=headers)
    scraped_langs = await _fetch_langs(session)
    assert 'en' in scraped_langs

    assert 'Detect language' not in scraped_langs
    assert '—' not in scraped_langs
    all_langs = await tts_langs(session)
    assert len(all_langs) == len(scraped_langs) + len(EXTRA_LANGS)


@pytest.mark.asyncio
async def test_fetch_langs_exception():
    session = aiohttp.ClientSession(headers=None)
    with pytest.raises(RuntimeError):
        await tts_langs(session)


if __name__ == '__main__':
    pytest.main(['-x', __file__])
