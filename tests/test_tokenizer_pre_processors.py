import pytest
from aiogtts.tokenizer.pre_processors import tone_marks, end_of_line, abbreviations, word_sub


def test_tone_marks():
    _in = 'lorem!ipsum?'
    _out = 'lorem! ipsum? '
    assert tone_marks(_in) == _out


def test_end_of_line():
    _in = '''test-
ing'''
    _out = 'testing'
    assert end_of_line(_in) == _out


def test_abbreviations():
    _in = 'jr. sr. dr.'
    _out = 'jr sr dr'
    assert abbreviations(_in) == _out


def test_word_sub():
    _in = 'Esq. Bacon'
    _out = 'Esquire Bacon'
    assert word_sub(_in) == _out


if __name__ == '__main__':
    pytest.main(['-x', __file__])
