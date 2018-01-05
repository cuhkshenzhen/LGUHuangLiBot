import logging
import os
import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor, wait
from urllib.request import urlopen

import boto3
import requests
from bs4 import BeautifulSoup

import newstools

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_links_in_page(page_url, legacy=True, starts_with_str=None):
    page_response = requests.get(page_url)
    if legacy:
        page_text = page_response.text
        soup = BeautifulSoup(page_text, 'html.parser')
        news_links = [page_url[:22] + x.get('href') for x in soup.find_all('a') if
                      x.get('href').startswith(starts_with_str)]
    else:
        page_json = page_response.json()
        news_links = ['http://www.cuhk.edu.cn' + x['link'] for x in page_json['data']['lists']]
    return news_links


def add_ner_entry(link, lst):
    lst.append(newstools.get_ner_entry(link))


def _get_updates0(page_link, pool, futures, original_links_set, updates, legacy=True, starts_with_str=None):
    links = set(get_links_in_page(page_link, legacy=legacy, starts_with_str=starts_with_str))
    new_links = links - original_links_set
    logger.info('New links from {}: {}'.format(page_link, new_links))
    if new_links:
        for link in new_links:
            future = pool.submit(add_ner_entry, link, updates)
            futures.append(future)


def get_updates(original: list):
    original_links_set = set(map(lambda x: x[0], original))
    pool = ThreadPoolExecutor()
    futures = []
    updates = []

    # Main site
    _get_updates0('http://www.cuhk.edu.cn/zh-hans/api/lists?page=0&type=all', pool, futures, original_links_set,
                  updates, legacy=False)

    # SME
    _get_updates0('http://sme.cuhk.edu.cn/zh-hans/sme/news?page=0', pool, futures, original_links_set, updates,
                  legacy=True, starts_with_str='/zh-hans/news/')

    # SSE
    _get_updates0('http://sse.cuhk.edu.cn/zh-hans/sse/news-events?page=0', pool, futures, original_links_set, updates,
                  legacy=True, starts_with_str='/zh-hans/node/')

    # HSS
    _get_updates0('http://hss.cuhk.edu.cn/zh-hans/subsite/common/lists/event/10/event/0?page=0', pool, futures,
                  original_links_set, updates,
                  legacy=True, starts_with_str='/zh-hans/node/')
    _get_updates0('http://hss.cuhk.edu.cn/zh-hans/subsite/common/lists/news/10/news/90?page=0', pool, futures,
                  original_links_set, updates,
                  legacy=True, starts_with_str='/zh-hans/node/')
    _get_updates0('http://hss.cuhk.edu.cn/zh-hans/subsite/common/lists/news/10/news/89?page=0', pool, futures,
                  original_links_set, updates,
                  legacy=True, starts_with_str='/zh-hans/node/')

    wait(futures)

    return updates


def update_news_file(file='news.txt'):
    original = []
    with open(file) as fle:
        for line in fle:
            line = line.strip()
            if not line:
                continue
            original.append(eval(line))

    updates = get_updates(original)
    if updates:
        with open(file, 'a') as fle:
            for update in updates:
                fle.write(repr(update) + '\n')
                logger.info('Saved: {}'.format(update[0]))


def lambda_handle(event, context):

    def work(s: str):
        return '/tmp/work/' + s

    logger.info('Preparing to download bot code')
    lambda_client = boto3.client('lambda')
    code_url = lambda_client.get_function(FunctionName=os.environ['LGUHUANGLIBOT_LAMBDA_NAME'])['Code']['Location']
    code_zip_data = urlopen(code_url).read()
    os.system('mkdir /tmp/work')
    with open('/tmp/code.zip', 'wb') as fle:
        fle.write(code_zip_data)

    logger.info('Preparing to extract bot code')
    with zipfile.ZipFile('/tmp/code.zip') as fle:
        fle.extractall('/tmp/work')

    logger.info('Preparing to update')
    if 'Records' in event:
        logger.info('Preparing to get update from S3')
        bucket = boto3.resource('s3').Bucket(os.environ['LGUHUANGLIBOT_DATA_BUCKET_NAME'])
        bucket.download_file('custom.txt', work('custom.txt'))
        bucket.download_file('templates.txt', work('templates.txt'))
    else:
        logger.info('Preparing to get update from news')
        update_news_file(work('news.txt'))

    logger.info('Preparing to regenerate word bank and merged data')
    newstools.generate_word_bank(work('news.txt'), custom=work('custom.txt'), noref_output=work('noref.txt'), output=work('wordbank.txt'))
    newstools.generate_merged_data(work('wordbank.txt'), noref_words_file=work('noref.txt'), templates_file=work('templates.txt'), output=work('merged_data.py'))

    logger.info('Preparing to make deploy.zip')
    shutil.make_archive('/tmp/deploy', 'zip', '/tmp/work')

    logger.info('Preparing to upload')
    lambda_client.update_function_code(FunctionName=os.environ['LGUHUANGLIBOT_LAMBDA_NAME'],
                           ZipFile=open('/tmp/deploy.zip', 'rb').read())

    logger.info('Returning')
