#!/usr/bin/env python3
import json
import requests
import os
import sys

WEBHOOK_URL = 'https://hooks.slack.com/services/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'
SUB = os.environ['CUAUV_VEHICLE'].capitalize()


def send(msg):
    try:
        requests.post(
            WEBHOOK_URL,
            data=json.dumps({
                'text': msg,
                'username': SUB,
            }),
            headers={
                'Content-Type': 'application/json'
            },
            timeout=60,
        )
    except requests.exceptions.RequestException:
        print('Timed out posting message to Slack: {}'.format(msg), file=sys.stderr)

