import re
import json
import base64
import aiohttp
import asyncio
import logging

from urllib.parse import quote
from .lang import tts_langs, _fallback_deprecated_lang
from .utils import _minimize, _clean_tokens, _translate_url
from .tokenizer import pre_processors, Tokenizer, tokenizer_cases

__all__ = ['aiogTTS', 'aiogTTSError']

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Speed:
    """Read Speed

    The Google TTS Translate API supports two speeds:
        Slow: True
        Normal: None
    """

    SLOW = True
    NORMAL = None


class aiogTTS:
    """aiogTTS -- Google Text-to-Speech.

    An interface to Google Translate's Text-to-Speech API.

    Args:
        pre_processor_funcs (list): A list of zero or more functions that are
            called to transform (pre-process) text before tokenizing. Those
            functions must take a string and return a string. Defaults to::

                [
                    pre_processors.tone_marks,
                    pre_processors.end_of_line,
                    pre_processors.abbreviations,
                    pre_processors.word_sub
                ]

        tokenizer_func (callable): A function that takes in a string and
            returns a list of string (tokens). Defaults to::

                Tokenizer([
                    tokenizer_cases.tone_marks,
                    tokenizer_cases.period_comma,
                    tokenizer_cases.colon,
                    tokenizer_cases.other_punctuation
                ]).run

    See Also:
        :doc:`Pre-processing and tokenizing <tokenizer>`

    Raises:
        AssertionError: When ``text`` is ``None`` or empty; when there's nothing
            left to speak after pre-precessing, tokenizing and cleaning.
        ValueError: When ``lang_check`` is ``True`` and ``lang`` is not supported.
        RuntimeError: When ``lang_check`` is ``True`` but there's an error loading
            the languages dictionary.
    """

    GOOGLE_TTS_MAX_CHARS = 100  # Max characters the Google TTS API takes at a time
    GOOGLE_TTS_HEADERS = {
        'Referer': 'http://translate.google.com/',
        'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; WOW64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/47.0.2526.106 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'
    }
    GOOGLE_TTS_RPC = 'jQ1olc'

    def __init__(
            self,
            pre_processor_funcs=[
                pre_processors.tone_marks,
                pre_processors.end_of_line,
                pre_processors.abbreviations,
                pre_processors.word_sub
            ],
            tokenizer_func=Tokenizer([
                tokenizer_cases.tone_marks,
                tokenizer_cases.period_comma,
                tokenizer_cases.colon,
                tokenizer_cases.other_punctuation
            ]).run
    ):

        self.session = aiohttp.ClientSession()

        self.pre_processor_funcs = pre_processor_funcs
        self.tokenizer_func = tokenizer_func

    def __del__(self):
        asyncio.get_event_loop().create_task(self.session.close())

    def _tokenize(self, text):
        text = text.strip()

        for pp in self.pre_processor_funcs:
            log.debug(f'pre-processing: {pp}')
            text = pp(text)

        if len(text) <= self.GOOGLE_TTS_MAX_CHARS:
            return _clean_tokens([text])

        log.debug(f'tokenizing: {self.tokenizer_func}')
        tokens = self.tokenizer_func(text)

        tokens = _clean_tokens(tokens)

        min_tokens = []
        for t in tokens:
            min_tokens += _minimize(t, ' ', self.GOOGLE_TTS_MAX_CHARS)

        min_tokens = [t for t in min_tokens if t]

        return min_tokens

    def _prepare_requests(self, text, lang, tld, slow, lang_check):
        """Created the TTS API the request(s) without sending them.

        Returns:
            list: ``requests.PreparedRequests_``. <https://2.python-requests.org/en/master/api/#requests.PreparedRequest>`_``.
        """

        if lang_check:
            lang = _fallback_deprecated_lang(lang)

            try:
                if lang not in tts_langs():
                    raise ValueError(f'Language not supported: {lang}')
            except RuntimeError as e:
                log.debug(str(e), exc_info=True)
                log.warning(str(e))

        translate_url = _translate_url(tld=tld, path='_/TranslateWebserverUi/data/batchexecute')

        text_parts = self._tokenize(text)
        log.debug(f'text_parts: {text_parts}')
        assert text_parts, 'No text to send to TTS API'

        prepared_requests = []
        for idx, part in enumerate(text_parts):
            data = self._package_rpc(part, lang, slow)

            log.debug(f'data-{idx}: {data}')

            r = self.session.post(translate_url, data=data, headers=self.GOOGLE_TTS_HEADERS)

            prepared_requests.append(r)

        return prepared_requests

    def _package_rpc(self, text, lang, slow):
        parameter = [text, lang, Speed.SLOW if slow else Speed.NORMAL, 'null']
        escaped_parameter = json.dumps(parameter, separators=(',', ':'))

        rpc = [[[self.GOOGLE_TTS_RPC, escaped_parameter, None, 'generic']]]
        escaped_rpc = json.dumps(rpc, separators=(',', ':'))
        return f'f.req={quote(escaped_rpc)}&'

    async def write_to_fp(self, text, fp, lang='en', tld='com', slow=False, lang_check=True):
        """Do the TTS API request(s) and write bytes to a file-like object.

        Args:
            text (string): The text to be read
            fp (file object): The path and file name to save the ``mp3`` to.
            lang (string, optional): The language (IETF language tag) to
                read the text in. Default is ``en``.
            tld (string, optional): Top-level domain for the Google Translate host,
                i.e `https://translate.google.<tld>`. Different Google domains
                can produce different localized 'accents' for a given
                language. This is also useful when ``google.com`` might be blocked
                within a network but a local or different Google host
                (e.g. ``google.cn``) is not. Default is ``com``.
            slow (bool, optional): Reads text more slowly. Defaults to ``False``.
            lang_check (bool, optional): Strictly enforce an existing ``lang``,
                to catch a language error early. If set to ``True``,
                a ``ValueError`` is raised if ``lang`` doesn't exist.
                Setting ``lang_check`` to ``False`` skips Web requests
                (to validate language) and therefore speeds up instantiation.
                Default is ``True``.

        Raises:
            :class:`aiogTTSError`: When there's an error with the API request.
            TypeError: When ``fp`` is not a file-like object that takes bytes.
        """

        prepared_requests = self._prepare_requests(text, lang, tld, slow, lang_check)
        for idx, pr in enumerate(prepared_requests):
            try:
                async with pr as r:
                    log.debug(f'headers-{idx}: {r.headers}')
                    log.debug(f'url-{idx}: {r.real_url}')
                    log.debug(f'status-{idx}: {r.status}')

                    r.raise_for_status()
                    decoded_line = await r.text()
                    if 'jQ1olc' in decoded_line:
                        audio_search = re.search(r'jQ1olc","\[\\"(.*)\\"]', decoded_line)
                        if audio_search:
                            as_bytes = audio_search.group(1).encode('ascii')
                            decoded = base64.b64decode(as_bytes)
                            fp.write(decoded)
                        else:
                            raise aiogTTSError(tts=self, response=r)
                log.debug(f'part-{idx} written to {fp}')
            except (AttributeError, TypeError) as e:
                raise TypeError(f"'fp' is not a file-like object or it does not take bytes: {e}")

            except aiohttp.ClientResponseError as e:
                log.debug(e.message)
                raise aiogTTSError(tts=self, response=r)
            except aiohttp.ClientConnectionError as e:
                log.debug(str(e))
                raise aiogTTSError(tts=self)

    async def save(self, text, filename, lang='en', tld='com', slow=False, lang_check=True):
        """Do the TTS API request and write result to file.

        Args:
            text (string): The text to be read
            filename (string): The path and file name to save the ``mp3`` to.
            lang (string, optional): The language (IETF language tag) to
                read the text in. Default is ``en``.
            tld (string, optional): Top-level domain for the Google Translate host,
                i.e `https://translate.google.<tld>`. Different Google domains
                can produce different localized 'accents' for a given
                language. This is also useful when ``google.com`` might be blocked
                within a network but a local or different Google host
                (e.g. ``google.cn``) is not. Default is ``com``.
            slow (bool, optional): Reads text more slowly. Defaults to ``False``.
            lang_check (bool, optional): Strictly enforce an existing ``lang``,
                to catch a language error early. If set to ``True``,
                a ``ValueError`` is raised if ``lang`` doesn't exist.
                Setting ``lang_check`` to ``False`` skips Web requests
                (to validate language) and therefore speeds up instantiation.
                Default is ``True``.

        Raises:
            :class:`aiogTTSError`: When there's an error with the API request.
        """

        with open(str(filename), 'wb') as f:
            await self.write_to_fp(text, f, lang, tld, slow, lang_check)
            log.debug(f'Saved to {filename}')


class aiogTTSError(Exception):
    """Exception that uses context to present a meaningful error message"""

    def __init__(self, msg=None, **kwargs):
        self.tts = kwargs.pop('tts', None)
        self.rsp = kwargs.pop('response', None)
        if msg:
            self.msg = msg
        elif self.tts is not None:
            self.msg = self.infer_msg(self.tts, self.rsp)
        else:
            self.msg = None
        super(aiogTTSError, self).__init__(self.msg)

    def infer_msg(self, tts, rsp=None):
        """Attempt to guess what went wrong by using known
        information (e.g. http response) and observed behaviour
        """

        cause = 'Unknown'

        if rsp is None:
            premise = 'Failed to connect'

            if tts.tld != 'com':
                host = _translate_url(tld=tts.tld)
                cause = f"Host '{host}' is not reachable"

        else:
            status = rsp.status
            reason = rsp.reason

            premise = f'{status} ({reason}) from TTS API'

            if status == 403:
                cause = 'Bad token or upstream API changes'
            elif status == 200:
                cause = f"No audio stream in response. Most probably the problem is in an unsupported language"
            elif status >= 500:
                cause = 'Upstream API error. Try again later.'

        return f'{premise}. Probable cause: {cause}'
