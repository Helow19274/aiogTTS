import pytest
import aiohttp
from aiogtts.token import Token
headers = {'User-Agent': 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0'}


@pytest.mark.asyncio
async def test_token():
    tokenizer = Token(aiohttp.ClientSession(headers=headers))
    text = 'test'
    assert '278125.134055' == await tokenizer.calculate_token(text, seed='406986.2817744745')


@pytest.mark.asyncio
async def test_real():
    tokenizer = Token(aiohttp.ClientSession(headers=headers))
    text = 'Hello'
    token = await tokenizer.calculate_token(text)
    payload = {'q': text, 'tl': 'en', 'client': 't', 'tk': token}

    async with tokenizer.session.get('https://translate.google.com/translate_tts', params=payload) as r:
        assert r.status == 200


if __name__ == '__main__':
    pytest.main(['-x', __file__])
