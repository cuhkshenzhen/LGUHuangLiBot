import logging
import re
from collections import OrderedDict

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_default_words_dict():
    return {
        'time': OrderedDict(),  # OrderedDict is used to remove duplicates while preserving item order
        'location': OrderedDict(),
        'person_name': OrderedDict(),
        'org_name': OrderedDict(),
        'company_name': OrderedDict(),
        'product_name': OrderedDict(),
        'job_title': OrderedDict(),
        'other_proper': OrderedDict()
    }


def get_text(body: str) -> str:
    soup = BeautifulSoup(body, 'html.parser')
    texts = map(lambda x: x.get_text(), soup.find_all(['p', 'span']))
    text = ' '.join(texts)
    text = re.sub(r'[\s\n]+', ' ', text)[:5000]
    return text


def get_news(url: str, ancient=False) -> str:
    if ancient:
        return requests.get(url).content.decode('utf-8')
    else:
        return requests.get(url).text


def ner(text: str):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': '*/*'
    }
    result = get_default_words_dict()
    response = requests.post('https://bosonnlp.com/analysis/ner?sensitivity=4', headers=headers, data=('data=' + text).encode('utf-8'))
    if response.status_code != 200:
        logger.error('NER error! Text={}, Status={}, Headers={}, JSON={}'.format(text, response.status_code, response.headers, response.json()))
        return None
    response = response.json()[0]
    tags = response['tag']
    words = response['word']
    entities = response['entity']
    for start, end, category in entities:
        if category not in result:
            continue
        word = ''.join(words[start:end])
        if len(word) > 1:
            result[category][word] = None
    for i, tag in enumerate(tags):
        word = words[i]
        if len(word) <= 1:
            continue
        if tag == 'ns':  # 地名，如“中国”，“上海市”，“江浙”
            result['location'][word] = None
        elif tag == 'nt':  # 组织机构名，如“中国队”，“央行”
            result['org_name'][word] = None
        elif tag == 'nz':  # 其它专有名词，如“银联”，“腾讯”
            result['other_proper'][word] = None
    return {k: list(v) for k, v in result.items()}


def get_ner_entry(link, ancient=False) -> list:
    try:
        return [link, ner(get_text(get_news(link, ancient=ancient)))]
    except:
        return [link, None]


def crawl_single_page(url, fle, ancient=False):
    entry = get_ner_entry(url, ancient=ancient)
    fle.write(repr(entry) + '\n')
    logging.info('Saved page: {}'.format(url))


def dumb_crawler_ancient_news(page=0, file='news.txt'):
    with open(file, 'a') as fle:
        page_url = ''
        if page == 0:
            page_url = 'http://www.old.cuhk.edu.cn/News/index180.html'
        else:
            page_url = 'http://www.old.cuhk.edu.cn/News/index180_page_{}.html'.format(page)
        page_res = requests.get(page_url).text
        soup = BeautifulSoup(page_res, 'html.parser')
        news_links = ['http://www.old.cuhk.edu.cn/News/' + x.get('href') for x in soup.find_all('a', class_=None) if x.get('href')[0].isdigit()]
        for link in news_links:
            crawl_single_page(link, fle, ancient=True)


def dumb_crawler_main(page=0, file='news.txt'):
    with open(file, 'a') as fle:
        page_res = requests.get('http://www.cuhk.edu.cn/zh-hans/api/lists?page={}&type=all'.format(page)).json()
        news_links = ['http://www.cuhk.edu.cn' + x['link'] for x in page_res['data']['lists']]
        for link in news_links:
            crawl_single_page(link, fle)


def _dumb_crawler_legacy(page_url, starts_with_str, fle):
    page_res = requests.get(page_url).text
    soup = BeautifulSoup(page_res, 'html.parser')
    news_links = [page_url[:22] + x.get('href') for x in soup.find_all('a') if x.get('href').startswith(starts_with_str)]
    for link in news_links:
        crawl_single_page(link, fle)


def dumb_crawler_sme(page=0, file='news.txt'):
    with open(file, 'a') as fle:
        page_url = 'http://sme.cuhk.edu.cn/zh-hans/sme/news?page={}'.format(page)
        _dumb_crawler_legacy(page_url, '/zh-hans/news/', fle)


def dumb_crawler_sse(page=0, file='news.txt'):
    with open(file, 'a') as fle:
        page_url = 'http://sse.cuhk.edu.cn/zh-hans/sse/news-events?page={}'.format(page)
        _dumb_crawler_legacy(page_url, '/zh-hans/node/', fle)


def dumb_crawler_hss_upcoming_events(page=0, file='news.txt'):
    with open(file, 'a') as fle:
        page_url = 'http://hss.cuhk.edu.cn/zh-hans/subsite/common/lists/event/10/event/0?page={}'.format(page)
        _dumb_crawler_legacy(page_url, '/zh-hans/node/', fle)


def dumb_crawler_hss_students_activities(page=0, file='news.txt'):
    with open(file, 'a') as fle:
        page_url = 'http://hss.cuhk.edu.cn/zh-hans/subsite/common/lists/news/10/news/90?page={}'.format(page)
        _dumb_crawler_legacy(page_url, '/zh-hans/node/', fle)


def dumb_crawler_hss_academic_activities(page=0, file='news.txt'):
    with open(file, 'a') as fle:
        page_url = 'http://hss.cuhk.edu.cn/zh-hans/subsite/common/lists/news/10/news/89?page={}'.format(page)
        _dumb_crawler_legacy(page_url, '/zh-hans/node/', fle)


def generate_word_bank(original='news.txt', custom='custom.txt', noref_output='noref.txt', output='wordbank.txt'):
    res = get_default_words_dict()
    with open(original) as fle:
        for line in fle:
            link, word_dict = eval(line)
            if not word_dict:
                continue
            for key, words in word_dict.items():
                d = res[key]
                for word in words:
                    d[word] = None
    word_dict = ''
    noref_words = []
    with open(custom) as fle:
        word_dict = eval(fle.read())
    if word_dict:
        for key, words in word_dict.items():
            if key not in res:
                res[key] = OrderedDict.fromkeys(words)
            else:
                d = res[key]
                for word in words:
                    d[word] = None
            noref_words += words
    res = {k: list(v) for k, v in res.items()}
    with open(output, 'w') as fle:
        fle.write(repr(res) + '\n')
    with open(noref_output, 'w') as fle:
        fle.write(repr(set(noref_words)) + '\n')


def generate_merged_data(words_file='wordbank.txt', noref_words_file='noref.txt', templates_file='templates.txt', output='merged.txt'):
    words = {}
    noref_words = []
    templates = []
    with open(words_file) as fle:
        words = eval(fle.readlines()[0])
    with open(noref_words_file) as fle:
        noref_words = eval(fle.readlines()[0])
    with open(templates_file) as fle:
        for line in fle.readlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            templates.append(line)
    with open(output, 'w') as fle:
        fle.write(repr([words, noref_words, templates]))


# [dumb_crawler_main(i) for i in range(10, 15)]
# [dumb_crawler_sme(i) for i in range(6)]
# [dumb_crawler_sse(i) for i in range(5)]
# [dumb_crawler_hss_upcoming_events(i) for i in range(3)]
# [dumb_crawler_hss_students_activities(i) for i in range(3)]
# [dumb_crawler_hss_academic_activities(i) for i in range(5)]
# [dumb_crawler_ancient_news(i) for i in range(61)]
# generate_word_bank()
# generate_merged_data()
