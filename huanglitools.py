import hashlib
import re
from random import Random
from urllib.parse import urlencode


class HuangLi:

    @staticmethod
    def get_merged_data(file: str):
        with open(file) as fle:
            return eval(fle.readlines()[0])

    @staticmethod
    def get_word_bank(file: str) -> dict:
        with open(file) as fle:
            return eval(fle.readlines()[0])

    @staticmethod
    def get_templates(file: str) -> list:
        ret = []
        with open(file) as fle:
            for line in fle.readlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                ret.append(line)
        return ret

    @staticmethod
    def get_noref_words(file: str) -> set:
        with open(file) as fle:
            return eval(fle.readlines()[0])

    def __init__(self, use_merged_data_py=True, merged_data_file='merged.txt', words_file='wordbank.txt', templates_file='templates.txt',
                 noref_file='noref.txt'):
        self.words = {}
        self.templates = []
        self.noref_words = set()
        if use_merged_data_py:
            import merged_data
            self.words, self.noref_words, self.templates = merged_data.words, merged_data.noref_words, merged_data.templates
        elif merged_data_file:
            self.words, self.noref_words, self.templates = HuangLi.get_merged_data(merged_data_file)
        else:
            self.words = HuangLi.get_word_bank(words_file)
            self.templates = HuangLi.get_templates(templates_file)
            self.noref_words = HuangLi.get_noref_words(noref_file)

    def calculate(self, data) -> str:
        random = Random(hashlib.md5(bytes(str(data), 'utf-8')).digest())

        def replacer(match):
            s = match.group(0)[1:-1]
            split = s.split(',')
            topic = random.choice(split)
            topic_words = self.words[topic]
            word = random.choice(topic_words)
            if word not in self.noref_words:
                return '[{}](https://www.google.com/search?{})'.format(word, urlencode(
                    {'q': '"{}" site:cuhk.edu.cn'.format(word)}))
            else:
                return word

        template = random.choice(self.templates)
        return re.sub(r'<\w+(,\w+)*>', replacer, template)
