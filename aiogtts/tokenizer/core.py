import re


class RegexBuilder(object):
    """Builds regex using arguments passed into a pattern template.

    Builds a regex object for which the pattern is made from an argument
    passed into a template. If more than one argument is passed (iterable),
    each pattern is joined by "|" (regex alternation 'or') to create a
    single pattern.

    :param pattern_args: String element(s) to be each passed to
        ``pattern_func`` to create a regex pattern. Each element is
        ``re.escape``'d before being passed.
    :type pattern_args: iterable

    :param pattern_func: A 'template' function that should take a
        string and return a string. It should take an element of
        ``pattern_args`` and return a valid regex pattern group string.
    :type pattern_func: callable

    :param flags: ``re`` flag(s) to compile with the regex.
    :type flags: re.*
    """

    def __init__(self, pattern_args, pattern_func, flags=0):
        self.pattern_args = pattern_args
        self.pattern_func = pattern_func
        self.flags = flags

        self.regex = self._compile()

    def _compile(self):
        alts = []
        for arg in self.pattern_args:
            arg = re.escape(arg)
            alt = self.pattern_func(arg)
            alts.append(alt)

        pattern = '|'.join(alts)
        return re.compile(pattern, self.flags)

    def __repr__(self):
        return str(self.regex)


class PreProcessorRegex(object):
    """Regex-based substitution text pre-processor.

    Runs a series of regex substitutions (``re.sub``) from each ``regex`` of a
    :class:`aigtts.tokenizer.core.RegexBuilder` with an extra ``repl``
    replacement parameter.

    :param search_args: String element(s) to be each passed to
        ``search_func`` to create a regex pattern. Each element is
        ``re.escape``'d before being passed
    :type search_args: iterable

    :param search_func: A 'template' function that should take a
        string and return a string. It should take an element of
        ``search_args`` and return a valid regex search pattern string
    :type search_func: callable

    :param repl: The common replacement passed to the ``sub`` method for
        each ``regex``. Can be a raw string (the case of a regex
        backreference, for example)
    :type repl: str

    :param flags: ``re`` flag(s) to compile with each `regex`.
    :type flags: re.*
    """

    def __init__(self, search_args, search_func, repl, flags=0):
        self.repl = repl

        self.regexes = []
        for arg in search_args:
            rb = RegexBuilder([arg], search_func, flags)
            self.regexes.append(rb.regex)

    def run(self, text):
        """Run each substitution on ``text``.

        :param text: The input text
        :type text: str

        :returns: Text after all substitutions have been sequentially applied
        :rtype: str
        """

        for regex in self.regexes:
            text = regex.sub(self.repl, text)
        return text

    def __repr__(self):
        subs_strs = []
        for r in self.regexes:
            subs_strs.append(f"({r}, repl='{self.repl}')")
        return ', '.join(subs_strs)


class PreProcessorSub(object):
    """Simple substitution text preprocessor.

    Performs string-for-string substitution from list a find/replace pairs.
    It abstracts :class:`gtts.tokenizer.core.PreProcessorRegex` with a default
    simple substitution regex.

    :param sub_pairs: list of tuples of the style (<search str>, <replace str>)
    :type sub_pairs: list

    :param ignore_case: Ignore case during search
    :type ignore_case: bool
    """

    def __init__(self, sub_pairs, ignore_case=True):
        def search_func(x):
            return str(x)

        flags = re.I if ignore_case else 0

        self.pre_processors = []
        for sub_pair in sub_pairs:
            pattern, repl = sub_pair
            pp = PreProcessorRegex([pattern], search_func, repl, flags)
            self.pre_processors.append(pp)

    def run(self, text):
        """Run each substitution on ``text``.

        :param text: The input text
        :type text: str

        :returns: Text after all substitutions have been sequentially applied
        :rtype: str
        """

        for pp in self.pre_processors:
            text = pp.run(text)
        return text

    def __repr__(self):
        return ', '.join([str(pp) for pp in self.pre_processors])


class Tokenizer(object):
    """An extensible but simple generic rule-based tokenizer.

    A generic and simple string tokenizer that takes a list of functions
    (called `tokenizer cases`) returning ``regex`` objects and joins them by
    "|" (regex alternation 'or') to create a single regex to use with the
    standard ``regex.split()`` function.

    ``regex_funcs`` is a list of any function that can return a ``regex``
    (from ``re.compile()``) object, such as a
    :class:`gtts.tokenizer.core.RegexBuilder` instance (and its ``regex``
    attribute).

    :param regex_funcs: List of compiled ``regex`` objects. Each
        functions's pattern will be joined into a single pattern and
        compiled.
    :type regex_funcs: list

    :param flags: ``re`` flag(s) to compile with the final regex.
    :type flags: re.*

    :raises: TypeError

    Note:
        When the ``regex`` objects obtained from ``regex_funcs`` are joined,
        their individual ``re`` flags are ignored in favour of ``flags``.

    Warning:
        Joined ``regex`` patterns can easily interfere with one another in
        unexpected ways. It is recommanded that each tokenizer case operate
        on distinct or non-overlapping chracters/sets of characters
        (For example, a tokenizer case for the period (".") should also
        handle not matching/cutting on decimals, instead of making that
        a seperate tokenizer case).
    """

    def __init__(self, regex_funcs, flags=re.IGNORECASE):
        self.regex_funcs = regex_funcs
        self.flags = flags

        try:
            self.total_regex = self._combine_regex()
        except (TypeError, AttributeError) as e:
            raise TypeError(f'Tokenizer() expects a list of functions returning regular expression objects (i.e. re.compile). {str(e)}')

    def _combine_regex(self):
        alts = []
        for func in self.regex_funcs:
            alts.append(func())

        pattern = '|'.join(alt.pattern for alt in alts)
        return re.compile(pattern, self.flags)

    def run(self, text):
        """Tokenize `text`.

        :param text: Text to tokenize
        :type text: str

        :returns: A list of strings (token) split according to the tokenizer cases
        :rtype: list
        """

        return self.total_regex.split(text)

    def __repr__(self):
        return f'{self.total_regex} from: {self.regex_funcs}'
