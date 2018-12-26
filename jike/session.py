# -*- coding: utf-8 -*-

"""
Session that communicates with Jike server
"""

import requests
import time
from .utils import check_token
from .constants import HEADERS


class JikeSession:
    def __init__(self, token):
        self.session = requests.Session()
        self.token = token
        self.headers = dict(HEADERS)
        self.headers.update({'x-jike-access-token': token})

    def __del__(self):
        self.session.close()

    def __repr__(self):
        return 'JikeSession({}...{})'.format(self.token[:10], self.token[-10:])

    def get(self, url, params=None):
        self.token = check_token()
        return self.session.get(url, params=params, headers=self.headers)

    def post(self, url, params=None, json=None):
        self.token = check_token()
        return self.session.post(url, params=params, json=json, headers=self.headers)
