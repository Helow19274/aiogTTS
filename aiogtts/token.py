import re
import math
import time
import calendar


class Token(object):
    """ Token (Google Translate Token)
    Generate the current token key and allows generation of tokens (tk) with it
    Python version of `token-script.js` itself from translate.google.com

    :param session: Aiohttp session
    :type session: :class:`aiohttp.ClientSession`
    """

    __slots__ = ('token_key', 'session')

    def __init__(self, session):
        self.token_key = None
        self.session = session

    async def calculate_token(self, text, seed=None):
        """ Calculate the request token (`tk`) of a string

        :param text: The text to calculate a token for
        :type text: str

        :param seed: The seed to use. By default this is the number of hours since epoch
        :type seed: str
        """

        if seed is None:
            seed = await self._get_token_key()

        [first_seed, second_seed] = seed.split('.')

        try:
            d = bytearray(text.encode('UTF-8'))
        except UnicodeDecodeError:
            d = bytearray(text)

        a = int(first_seed)
        for value in d:
            a += value
            a = self._work_token(a, '+-a^+6')
        a = self._work_token(a, '+-3^+b+-f')
        a ^= int(second_seed)
        if 0 > a:
            a = (a & 2147483647) + 2147483648
        a %= 1E6
        a = int(a)
        return str(a) + '.' + str(a ^ int(first_seed))

    async def _get_token_key(self):
        if self.token_key:
            return self.token_key

        async with self.session.get('https://translate.google.com/') as r:
            tkk_expr = re.search('(tkk:.*?),', await r.text())

        if not tkk_expr:
            raise ValueError('Unable to find token seed! Did https://translate.google.com change?')

        tkk_expr = tkk_expr.group(1)
        try:
            result = re.search(r'\d{6}\.[0-9]+', tkk_expr).group(0)
        except AttributeError:
            timestamp = calendar.timegm(time.gmtime())
            hours = int(math.floor(timestamp / 3600))
            a = re.search(r'a\\\\x3d(-?\d+);', tkk_expr).group(1)
            b = re.search(r'b\\\\x3d(-?\d+);', tkk_expr).group(1)

            result = f'{hours}.{int(a) + int(b)}'

        self.token_key = result
        return result

    def _rshift(self, val, n):
        return val >> n if val >= 0 else (val + 0x100000000) >> n

    def _work_token(self, a, seed):
        for i in range(0, len(seed) - 2, 3):
            char = seed[i + 2]
            d = ord(char[0]) - 87 if char >= 'a' else int(char)
            d = self._rshift(a, d) if seed[i + 1] == '+' else a << d
            a = a + d & 4294967295 if seed[i] == '+' else a ^ d
        return a
