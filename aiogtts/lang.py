import re
import logging
from bs4 import BeautifulSoup

EXTRA_LANGS = {
    'zh-cn': 'Chinese (Mandarin/China)',
    'zh-tw': 'Chinese (Mandarin/Taiwan)',

    'en-us': 'English (US)',
    'en-ca': 'English (Canada)',
    'en-uk': 'English (UK)',
    'en-gb': 'English (UK)',
    'en-au': 'English (Australia)',
    'en-gh': 'English (Ghana)',
    'en-in': 'English (India)',
    'en-ie': 'English (Ireland)',
    'en-nz': 'English (New Zealand)',
    'en-ng': 'English (Nigeria)',
    'en-ph': 'English (Philippines)',
    'en-za': 'English (South Africa)',
    'en-tz': 'English (Tanzania)',

    'fr-ca': 'French (Canada)',
    'fr-fr': 'French (France)',

    'pt-br': 'Portuguese (Brazil)',
    'pt-pt': 'Portuguese (Portugal)',

    'es-es': 'Spanish (Spain)',
    'es-us': 'Spanish (United States)'
}

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


async def tts_langs(session):
    """Languages Google Text-to-Speech supports.

    :param session: Aiohttp session
    :type session: :class:`aiohttp.ClientSession`

    :returns: A dict of TTS supported langs
    :rtype: dict
    """

    try:
        langs = {}
        langs.update(await _fetch_langs(session))
        langs.update(EXTRA_LANGS)
        log.debug(f'langs: {langs}')
        return langs
    except Exception as e:
        raise RuntimeError(f'Unable to get language list: {str(e)}')


async def _fetch_langs(session):
    """Fetch (scrape) languages from Google Translate.

    Google Translate loads a JavaScript Array of 'languages codes' that can
    be spoken. We intersect this list with all the languages Google Translate
    provides to get the ones that support text-to-speech.

    :param session: Aiohttp session
    :type session: :class:`aiohttp.ClientSession`

    :returns: A dict of languages from Google Translate
    :rtype: dict
    """

    async with session.get('http://translate.google.com') as r:
        content = await r.read()
        text = await r.text()

    soup = BeautifulSoup(content, 'html.parser')

    js_path = soup.find(src=re.compile('translate_m.js'))['src']

    async with session.get(f'http://translate.google.com/{js_path}') as r:
        js_contents = await r.text()

    # Approximately extract TTS-enabled language codes
    # RegEx pattern search because minified variables can change.
    # Extra garbage will be dealt with later as we keep languages only.
    # In: "[...]Fv={af:1,ar:1,[...],zh:1,"zh-cn":1,"zh-tw":1}[...]"
    # Out: ['is', '12', [...], 'af', 'ar', [...], 'zh', 'zh-cn', 'zh-tw']
    pattern = r'[{,\"](\w{2}|\w{2}-\w{2,3})(?=:1|\":1)'
    tts_langs = re.findall(pattern, js_contents)

    # Build lang. dict. from main page (JavaScript object populating lang. menu)
    # Filtering with the TTS-enabled languages
    # In: "{code:'auto',name:'Detect language'},{code:'af',name:'Afrikaans'},[...]"
    # re.findall: [('auto', 'Detect language'), ('af', 'Afrikaans'), [...]]
    # Out: {'af': 'Afrikaans', [...]}
    trans_pattern = r"{code:'(?P<lang>.+?[^'])',name:'(?P<name>.+?[^'])'}"
    trans_langs = re.findall(trans_pattern, text)
    return {lang: name for lang, name in trans_langs if lang in tts_langs}
