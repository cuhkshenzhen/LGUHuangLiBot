from collections import OrderedDict

import requests
from bs4 import BeautifulSoup


def get_text(body: str) -> str:
    soup = BeautifulSoup(body, 'html.parser')
    ret = ''
    texts = map(lambda x: x.get_text(), soup.find_all(['p', 'span']))
    for text in texts:
        if len(text) > 5000:
            ret += text[:5000] + '\n' + text[5000:] + '\n'
        else:
            ret += text + '\n'
    return ret


def get_news(url: str) -> str:
    return requests.get(url).text


def ner(text: str):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': '*/*'
    }
    res = {
        'time': OrderedDict(),  # Not using sets because order is significant
        'location': OrderedDict(),
        'person_name': OrderedDict(),
        'org_name': OrderedDict(),
        'company_name': OrderedDict(),
        'product_name': OrderedDict(),
        'job_title': OrderedDict(),
        'other_proper': OrderedDict()
    }
    res = requests.post('https://bosonnlp.com/analysis/ner?sensitivity=4', headers=headers, data=('data=' + text).encode('utf-8'))
    if res.status_code != 200:
        print(text, res.status_code, res.headers, res.json())
        return None
    res = res.json()[0]
    tags = res['tag']
    words = res['word']
    entities = res['entity']
    for start, end, category in entities:
        if category not in res:
            continue
        word = ''.join(words[start:end])
        if len(word) > 1:
            res[category][word] = None
    for i, tag in enumerate(tags):
        word = words[i]
        if len(word) <= 1:
            continue
        if tag == 'ns':  # 地名，如“中国”，“上海市”，“江浙”
            res['location'][word] = None
        elif tag == 'nt':  # 组织机构名，如“中国队”，“央行”
            res['org_name'][word] = None
        elif tag == 'nz':  # 其它专有名词，如“银联”，“腾讯”
            res['other_proper'][word] = None
    return {k: list(v) for k, v in res.items()}


def get_ner_entry(link) -> list:
    return [link, ner(get_text(get_news(link)))]


def crawl_single_page(url, fle):
    entry = get_ner_entry(url)
    fle.write(repr(entry) + '\n')
    print('Saved: {}'.format(url))


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
    res = {
        'time': OrderedDict(),
        'location': OrderedDict(),
        'person_name': OrderedDict(),
        'org_name': OrderedDict(),
        'company_name': OrderedDict(),
        'product_name': OrderedDict(),
        'job_title': OrderedDict(),
        'other_proper': OrderedDict()
    }
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
# generate_word_bank()
# generate_merged_data()
