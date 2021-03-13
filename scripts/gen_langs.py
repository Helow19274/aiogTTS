from aiogtts.utils import _translate_url
from bs4 import BeautifulSoup
import asyncio
import aiohttp
import logging
import js2py
import json
import sys
import re

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

# This file is used to generate the language dict (as a module)
# Needs cleaning up, very much WIP
# Usage:
# * Install aiogTTS
# * $ python gen_langs.py <path to aiogtts>/langs.py


def _get_data_by_key(js_list):
    """JavaScript function to generate the languages.

    A payload with the languages is passed to a JavaScript function.
    Instead of parsing that payload (cumbersome), we 'overload' that
    function to return what we want.

    """

    js_function = """
        function AF_initDataCallback(args) {
            return { key: args['key'], data: args['data'] };
        };
    """

    data_by_key = {}
    for js in js_list:
        js_code = js_function + js
        py_eval = js2py.eval_js(js_code)
        data_by_key[py_eval['key']] = py_eval['data']

    return data_by_key


async def _fetch_langs(tld='com'):
    """Fetch (scrape) languages from Google Translate.

    Google Translate loads a JavaScript Array of 'languages codes' that can
    be spoken. We intersect this list with all the languages Google Translate
    provides to get the ones that support text-to-speech.

    Args:
        tld (string): Top-level domain for the Google Translate host
            to fetch languages from. i.e `https://translate.google.<tld>`.
            The language names obtained will be in a language locale of the TLD
            (e.g. ``tld=fr`` will retrieve the French names of the languages).
            Default is ``com``.

    Returns:
        dict: A dictionary of languages from Google Translate

    """

    headers = {
        'User-Agent':
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/605.1.15 (KHTML, like Gecko) '
            'Version/14.0 Safari/605.1.15'
    }

    async with aiohttp.ClientSession() as s:
        async with s.get(_translate_url(tld), headers=headers) as r:
            page = await r.content.read()

    soup = BeautifulSoup(page, 'html.parser')

    scripts = soup.find_all(name='script', string=re.compile(r'^AF_initDataCallback'))
    scripts = [s.next for s in scripts]

    data_by_key = _get_data_by_key(scripts)

    # Get all languages (ds:3)
    # data for 'ds:3' is
    #   [
    #       [['hi', 'Hindi'], ['ps', 'Pashto'], ... ]],
    #       [['hi', 'Hindi'], ['ps', 'Pashto'], ... ]]
    #   ]
    # (Note: list[0] and list[1] are identical)
    all_langs_raw = data_by_key['ds:3']

    # Get languages codes that have TTS (ds:6)
    # data for 'ds:6' is
    #   [
    #       [['af', 200], ['ar', 200], ...]
    #   ]
    tts_langs_raw = data_by_key['ds:6']
    tts_langs = [lang[0] for lang in tts_langs_raw[0]]

    # Create language dict (and filter only TTS-enabled langs)
    # langs = { lang[0], lang[1] for lang in all_langs_raw[0] }

    langs = {k: v for k, v in all_langs_raw[0] if k in tts_langs}
    return langs


if __name__ == '__main__':
    """Language list generation 'main'

    CLI to generate the language list as a dict in
    an importable python file/module

    Usage:
        python ./scripts/gen_langs.py ./aiogTTS/aiogtts/langs.py

    """
    async def main():
        lang_file_path = sys.argv[1]
        langs = await _fetch_langs()

        py_content = f"""_langs = {json.dumps(langs, indent=4, sort_keys=True)}


def _main_langs():
    return _langs
"""
        with open(lang_file_path, 'w') as f:
            f.write(py_content)

    asyncio.get_event_loop().run_until_complete(main())
