import logging
import aiohttp
import asyncio

from .token import Token
from .lang import tts_langs
from .utils import _minimize, _clean_tokens
from .tokenizer import pre_processors, Tokenizer, tokenizer_cases

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class aiogTTS(object):
    """gTTS -- Google Text-to-Speech.

    An interface to Google Translate's Text-to-Speech API.
    :param pre_processor_funcs: A list of zero or more functions that are
        called to transform (pre-process) text before tokenizing. Those
        functions must take a string and return a string
    :type pre_processor_funcs: list

    :param tokenizer_func: A function that takes in a string and returns a list of string (tokens)
    :type tokenizer_func: callable

    :raises: ValueError, RuntimeError
    """

    GOOGLE_TTS_MAX_CHARS = 100

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
        headers = {'User-Agent': 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0'}
        self.session = aiohttp.ClientSession(headers=headers)
        self.pre_processor_funcs = pre_processor_funcs
        self.tokenizer_func = tokenizer_func
        self.token = Token(self.session)

    def __del__(self):
        return asyncio.get_event_loop().create_task(self.session.close())

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
        return min_tokens

    async def write_to_fp(self, text, fp, lang='en', slow=False, lang_check=True):
        """Do the TTS API request and write bytes to a file-like object.

        :param text: Text to speak
        :type text: str

        :param fp: Any file-like object to write the mp3 to
        :type fp: file-like

        :param lang: Language
        :type lang: str

        :param slow: If slow, speed == 0.3
        :type slow: bool

        :param lang_check: Check if :param:`lang` in list of TTS languages
        :type lang_check: bool

        :raises: :class:`aiogTTSError`:, TypeError
        """

        if not text:
            raise ValueError('No text to speak')

        lang = lang.lower()
        if lang_check:
            try:
                langs = await tts_langs(self.session)
                if lang not in langs:
                    raise ValueError(f'Language not supported: {lang}')
            except RuntimeError as e:
                log.debug(str(e), exc_info=True)
                log.warning(str(e))

        text_parts = self._tokenize(text)
        log.debug(f'text_parts: {len(text_parts)}')
        if not text_parts:
            raise ValueError('No text to send to TTS API')

        for idx, part in enumerate(text_parts):
            try:
                part_tk = await self.token.calculate_token(part)
            except aiohttp.client_exceptions.ClientError as e:
                log.debug(str(e), exc_info=True)
                raise aiogTTSError(f'Connection error during token calculation: {str(e)}')

            payload = {'ie': 'UTF-8',
                       'q': part,
                       'tl': lang,
                       'ttsspeed': '0.3' if slow else '1',
                       'total': len(text_parts),
                       'idx': idx,
                       'client': 'tw-ob',
                       'textlen': len(part),
                       'tk': part_tk}

            log.debug(f'payload-{idx}: {payload}')

            try:
                async with self.session.get('https://translate.google.com/translate_tts', params=payload) as r:
                    log.debug(f'headers-{idx}: {r.headers}')
                    log.debug(f'url-{idx}: {r.real_url}')
                    log.debug(f'status-{idx}: {r.status}')
                    r.raise_for_status()

                    async for chunk in r.content.iter_chunked(1024):
                        fp.write(chunk)

                    log.debug(f'part-{idx} written to {fp}')
            except aiohttp.client_exceptions.ClientResponseError:
                # Request successful, bad response
                raise aiogTTSError(lang=lang, lang_check=lang_check, response=r)
            except aiohttp.client_exceptions.ClientConnectionError as e:
                # Request failed
                raise aiogTTSError(str(e))
            except (AttributeError, TypeError) as e:
                raise TypeError(f"'fp' is not a file-like object or it does not take bytes: {str(e)}")

    async def save(self, text, savefile, lang='en', slow=False, lang_check=True):
        """Do the TTS API request and write bytes to a file-like object.

        :param text: Text to speak
        :type text: str

        :param savefile: Name of file to write the mp3 to
        :type fp: str

        :param lang: Language
        :type lang: str

        :param slow: If slow, speed == 0.3
        :type slow: bool

        :param lang_check: Check if :param:`lang` in list of TTS languages
        :type lang_check: bool

        :raises: :class:`aiogTTSError`:, TypeError
        """

        with open(str(savefile), 'wb') as f:
            await self.write_to_fp(text, f, lang, slow, lang_check)
            log.debug(f'Saved to {savefile}')


class aiogTTSError(Exception):
    """Exception that uses context to present a meaningful error message"""

    def __init__(self, msg=None, **kwargs):
        self.lang_check = kwargs.pop('lang_check', None)
        self.lang = kwargs.pop('lang', None)
        self.rsp = kwargs.pop('response', None)
        if msg:
            self.msg = msg
        elif self.lang is not None and self.lang_check is not None and self.rsp is not None:
            self.msg = self.infer_msg()
        else:
            self.msg = None
        super(aiogTTSError, self).__init__(self.msg)

    def infer_msg(self):
        """Attempt to guess what went wrong by using known
        information (e.g. http response) and observed behaviour
        """

        status = self.rsp.status
        reason = self.rsp.reason

        cause = 'Unknown'
        if status == 403:
            cause = 'Bad token or upstream API changes'
        elif status == 404 and not self.lang_check:
            cause = f"Unsupported language '{self.lang}'"
        elif status >= 500:
            cause = 'Uptream API error. Try again later'

        return f'{status} ({reason}) from TTS API. Probable cause: {cause}'
