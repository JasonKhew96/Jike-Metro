# -*- coding: utf-8 -*-

"""
utils
"""

import requests
import json
import os
import platform
import time
from collections import defaultdict
from mimetypes import guess_type

from .qr_code import make_qrcode
from .constants import ENDPOINTS, AUTH_TOKEN_STORE_PATH, URL_VALIDATION_PATTERN
from .objects.message import Answer, Comment, OfficialMessage, OriginalPost, PersonalUpdate, PersonalUpdateSection, Question, Repost

converter = defaultdict(lambda: dict,
                        {
                            'OFFICIAL_MESSAGE': OfficialMessage,
                            'ORIGINAL_POST': OriginalPost,
                            'QUESTION': Question,
                            'ANSWER': Answer,
                            'REPOST': Repost,
                            'PERSONAL_UPDATE': PersonalUpdate,
                            'PERSONAL_UPDATE_SECTION': PersonalUpdateSection,
                            'COMMENT': Comment,
                        })


def read_token_timestamp():
    if os.path.exists(AUTH_TOKEN_STORE_PATH):
        with open(AUTH_TOKEN_STORE_PATH, 'rt', encoding='utf-8') as fp:
            store = json.load(fp)
        return store['timestamp']


def read_refresh_token():
    if os.path.exists(AUTH_TOKEN_STORE_PATH):
        with open(AUTH_TOKEN_STORE_PATH, 'rt', encoding='utf-8') as fp:
            store = json.load(fp)
        return store['refresh_token']


def read_access_token():
    if os.path.exists(AUTH_TOKEN_STORE_PATH):
        with open(AUTH_TOKEN_STORE_PATH, 'rt', encoding='utf-8') as fp:
            store = json.load(fp)
        return store['access_token']


def write_token(access_token, refresh_token):
    timestamp = int(time.time())
    with open(AUTH_TOKEN_STORE_PATH, 'wt', encoding='utf-8') as fp:
        store = {
            'timestamp': timestamp,
            'access_token': access_token,
            'refresh_token': refresh_token
        }
        json.dump(store, fp, indent=2)


def check_token():
    now_timestamp = int(time.time())
    token_timestamp = read_token_timestamp()
    if (now_timestamp - token_timestamp) > 600:
        return refresh_auth_tokens(read_refresh_token())
    return read_access_token()


def wait_login(uuid):
    res = requests.get(ENDPOINTS['wait_login'], params=uuid)
    if res.status_code == 200:
        logged_in = res.json()
        return logged_in['logged_in']
    res.raise_for_status()
    return False


def confirm_login(uuid):
    res = requests.get(ENDPOINTS['confirm_login'], params=uuid)
    if res.status_code == 200:
        confirmed = res.json()
        if confirmed['confirmed'] is True:
            write_token(confirmed['x-jike-access-token'],
                        confirmed['x-jike-refresh-token'])
            return confirmed['x-jike-access-token']
        else:
            raise SystemExit('User not board Jike Metro, what a shame')
    res.raise_for_status()


def login():
    res = requests.get(ENDPOINTS['create_session'])
    uuid = None
    if res.status_code == 200:
        uuid = res.json()
    res.raise_for_status()

    assert uuid, 'Create session fail'
    make_qrcode(uuid)

    logging = False
    attempt_counter = 1
    while not logging:
        logging = wait_login(uuid)
        attempt_counter += 1
        if attempt_counter > 5:
            raise SystemExit('Login takes too long, abort')

    token = None
    attempt_counter = 1
    while token is None:
        token = confirm_login(uuid)
        attempt_counter += 1
        if attempt_counter > 5:
            raise SystemExit('Login takes too long, abort')

    return token


def refresh_auth_tokens(token):
    res = requests.get(ENDPOINTS['app_auth_tokens_refresh'], headers={
        'Origin': 'https://web.okjike.com',
        'Referer': 'https://web.okjike.com/feed',
        'x-jike-refresh-token': token
    })
    if res.status_code == 200:
        token_refresh = res.json()
        access_token = token_refresh['x-jike-access-token']
        refresh_token = token_refresh['x-jike-refresh-token']
        write_token(access_token, refresh_token)
        return access_token
    res.raise_for_status()
    return False


def extract_url(content):
    return URL_VALIDATION_PATTERN.findall(content)


def extract_link(jike_session, link):
    res = jike_session.post(ENDPOINTS['extract_link'], json={
        'link': link
    })
    link_info = None
    if res.status_code == 200:
        result = res.json()
        if result['success']:
            link_info = result['data']
    res.raise_for_status()
    return link_info


def get_uptoken():
    res = requests.get(ENDPOINTS['picture_uptoken'], params={'bucket': 'jike'})
    if res.ok:
        return res.json()['uptoken']
    res.raise_for_status()


def upload_a_picture(picture):
    assert os.path.exists(picture)
    name = os.path.split(picture)[1]
    mimetype, _ = guess_type(name)
    assert mimetype
    if not mimetype.startswith('image'):
        raise ValueError('Cannot upload file: {}, which is not picture'.format(name))

    uptoken = get_uptoken()
    with open(picture, 'rb') as fp:
        files = {'token': (None, uptoken), 'file': (name, fp, mimetype)}
        res = requests.post(ENDPOINTS['picture_upload'], files=files)
    if res.status_code == 200:
        result = res.json()
        if result['success']:
            return result['key']
        else:
            raise RuntimeError('Picture upload fail')
    res.raise_for_status()


def upload_pictures(picture_paths):
    if isinstance(picture_paths, str):
        picture_paths = [picture_paths]
    pic_url = [upload_a_picture(picture) for picture in picture_paths]
    return pic_url


def notify(title, message):
    assert isinstance(title, str), 'please provide string as title'
    assert isinstance(message, str), 'please provide string as message'
    if 'Darwin' not in platform.system():
        return 'Only support macOS system'
    cmd = """/usr/bin/osascript -e 'display notification "{msg}" with title "{title}"'""".format(title=title, msg=message)
    os.system(cmd)
