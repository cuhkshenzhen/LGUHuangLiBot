import hashlib
import re
from random import Random
from urllib.parse import urlencode


def get_word_bank(file='wordbank.txt') -> dict:
    with open(file) as fle:
        return eval(fle.readlines()[0])


def get_templates(file='templates.txt') -> list:
    ret = []
    with open(file) as fle:
        for line in fle.readlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            ret.append(line)
    return ret


def get_noref_words(file='noref.txt') -> set:
    with open(file) as fle:
        return eval(fle.readlines()[0])


def calculate(data, noref_words: list=None, templates: list=None, words: dict=None):
    if not noref_words:
        noref_words = get_noref_words()
    if not templates:
        templates = get_templates()
    if not words:
        words = get_word_bank()
    random = Random(hashlib.md5(bytes(str(data), 'utf-8')).digest())
    def replacer(match):
        s = match.group(0)[1:-1]
        split = s.split(',')
        topic = random.choice(split)
        topic_words = words[topic]
        word = random.choice(topic_words)
        if word not in noref_words:
            return '[{}](https://www.google.com/search?{})'.format(word, urlencode({'q': '"{}" site:cuhk.edu.cn'.format(word)}))
        else:
            return word

    template = random.choice(templates)
    return re.sub(r'<\w+(,\w+)*>', replacer, template)
