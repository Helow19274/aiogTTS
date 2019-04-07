import re
import pytest
from aiogtts.tokenizer.core import RegexBuilder, PreProcessorRegex, PreProcessorSub, Tokenizer


def test_regexbuilder():
    rb = RegexBuilder('abc', lambda x: str(x))
    assert rb.regex == re.compile('[abc]')


def test_preprocessorregex():
    pp = PreProcessorRegex('ab', lambda x: str(x), 'c')
    assert len(pp.regexes) == 2
    assert pp.regexes[0].pattern == 'a'
    assert pp.regexes[1].pattern == 'b'


def test_proprocessorsub():
    sub_pairs = [('Mac', 'PC'), ('Firefox', 'Chrome')]
    pp = PreProcessorSub(sub_pairs)
    _in = 'I use firefox on my mac'
    _out = 'I use Chrome on my PC'
    assert pp.run(_in) == _out


# tokenizer case 1
def case1():
    return re.compile(',')


# tokenizer case 2
def case2():
    return RegexBuilder('abc', lambda x: r'{}\.'.format(x)).regex


def test_tokenizer():
    t = Tokenizer([case1, case2])
    _in = "Hello, my name is Linda a. Call me Lin, b. I'm your friend"
    _out = [
        'Hello',
        ' my name is Linda ',
        ' Call me Lin',
        ' ',
        " I'm your friend"]
    assert t.run(_in) == _out


def test_bad_params_not_list():
    with pytest.raises(TypeError):
        Tokenizer(case1)


def test_bad_params_not_callable():
    with pytest.raises(TypeError):
        Tokenizer([100])


def test_bad_params_not_callable_returning_regex():
    def not_regex():
        return 1

    with pytest.raises(TypeError):
        Tokenizer([not_regex])


if __name__ == '__main__':
    pytest.main(['-x', __file__])
