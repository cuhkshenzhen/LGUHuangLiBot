import logging
import os
import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor, wait
from threading import Thread
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


def update_news_file(file='news.txt') -> bool:
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
        return True
    else:
        return False


def lambda_handle(event, context):

    lambda_client = boto3.client('lambda')

    def process_bot_code():
        logger.info('Preparing to download bot code')
        code_url = lambda_client.get_function(FunctionName=os.environ['LGUHUANGLIBOT_LAMBDA_NAME'])['Code']['Location']
        code_zip_data = urlopen(code_url).read()
        with open('/tmp/code.zip', 'wb') as fle:
            fle.write(code_zip_data)

        logger.info('Preparing to extract bot code')
        os.system('mkdir /tmp/work')
        with zipfile.ZipFile('/tmp/code.zip') as fle:
            fle.extractall('/tmp/work')

    bot_code_thread = Thread(target=process_bot_code, name='process_bot_code')
    bot_code_thread.start()

    logger.info('Preparing to update')

    def process_s3():
        logger.info('Preparing to get update from S3')
        os.mkdir('/tmp/s3')
        bucket = boto3.resource('s3').Bucket(os.environ['LGUHUANGLIBOT_DATA_BUCKET_NAME'])
        bucket.download_file('custom.txt', '/tmp/s3/custom.txt')
        bucket.download_file('templates.txt', '/tmp/s3/templates.txt')

    s3_thread = Thread(target=process_s3, name='process_s3')
    s3_thread.start()

    bot_code_thread.join()
    s3_thread.join()

    logger.info('Preparing to get update from news')
    update_news_file('/tmp/work/news.txt')

    logger.info('Preparing to regenerate word bank and merged data')

    os.chdir('/tmp/work')
    shutil.copy('/tmp/s3/custom.txt', '/tmp/work/custom.txt')
    shutil.copy('/tmp/s3/templates.txt', '/tmp/work/templates.txt')

    newstools.generate_word_bank('news.txt', custom='custom.txt', noref_output='noref.txt', output='wordbank.txt')
    newstools.generate_merged_data('wordbank.txt', noref_words_file='noref.txt', templates_file='templates.txt', output='merged.json')

    logger.info('Preparing to make deploy.zip')
    shutil.make_archive('/tmp/deploy', 'zip', '/tmp/work')

    logger.info('Preparing to upload')
    lambda_client.update_function_code(FunctionName=os.environ['LGUHUANGLIBOT_LAMBDA_NAME'],
                                       ZipFile=open('/tmp/deploy.zip', 'rb').read())

    logger.info('Done. Returning')
