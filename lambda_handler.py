import json
import logging
import random
import time
from datetime import date

import huanglitools

logger = logging.getLogger()
logger.setLevel(logging.INFO)
default_lambda_response = {'statusCode': 200}


def pack_lambda_reply(method: str=None, obj: dict=None):
    return {
        **default_lambda_response,
        'body': json.dumps({**obj, 'method': method})
    } if method else default_lambda_response


def handle(event, context):

    method = obj = None
    body = json.loads(event['body'])
    logger.debug('Received body: {}'.format(body))

    if 'message' not in body:
        return default_lambda_response

    message = body['message']
    if 'text' not in message or 'from' not in message:
        return default_lambda_response

    text = message['text']
    if not text.startswith('/'):
        return default_lambda_response

    reply = {
        'chat_id': message['chat']['id'],
        'text': '',
        'reply_to_message_id': message['message_id'],
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }

    do = do_not = first_name = ''
    user = message['from']

    if text.startswith('/my'):
        user_id = user['id']
        today = date.fromtimestamp(time.time() + 28800)  # AWS Lambda uses UTC timezone; 28800 = 8 * 3600
        do = huanglitools.calculate('{}{}do'.format(user_id, today))
        do_not = huanglitools.calculate('{}{}do_not'.format(user_id, today))
    elif text.startswith('/random'):
        do = huanglitools.calculate(random.random())
        do_not = huanglitools.calculate(random.random())
    else:
        return default_lambda_response

    reply['text'] = '{} 今日：\n*宜* {}\n*忌* {}'.format(user['first_name'], do, do_not)

    method = 'sendMessage'
    obj = reply

    return pack_lambda_reply(method, obj)
