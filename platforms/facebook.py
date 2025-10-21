import os
import requests
from utils.logger import get_logger
from utils.env import get_env, set_env

logger = get_logger()

def _exchange_long_lived_user_token(app_id, app_secret, user_token):
    url = 'https://graph.facebook.com/oauth/access_token'
    params = {
        'grant_type': 'fb_exchange_token',
        'client_id': app_id,
        'client_secret': app_secret,
        'fb_exchange_token': user_token,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get('access_token')

def _get_page_access_token(page_id, user_access_token):
    url = 'https://graph.facebook.com/me/accounts'
    params = {'access_token': user_access_token}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    for acct in data.get('data', []):
        if str(acct.get('id')) == str(page_id):
            return acct.get('access_token')
    return None

def _refresh_facebook_page_token(page_id):
    app_id = get_env('FACEBOOK_APP_ID')
    app_secret = get_env('FACEBOOK_APP_SECRET')
    user_token = get_env('FACEBOOK_USER_ACCESS_TOKEN')
    if not app_id or not app_secret or not user_token:
        logger.error('Facebook refresh prerequisites missing (FACEBOOK_APP_ID/SECRET/USER_ACCESS_TOKEN).')
        return None
    try:
        long_lived_user_token = _exchange_long_lived_user_token(app_id, app_secret, user_token)
        if not long_lived_user_token:
            logger.error('Failed to obtain long-lived user token.')
            return None
        page_token = _get_page_access_token(page_id, long_lived_user_token)
        if not page_token:
            logger.error('Failed to obtain page access token from user token.')
            return None
        set_env('FACEBOOK_ACCESS_TOKEN', page_token)
        return page_token
    except Exception as e:
        logger.error(f'Facebook token refresh failed: {e}')
        return None

def post(content):
    """
    Post content to Facebook Page feed using Graph API.
    """
    page_id = get_env('FACEBOOK_PAGE_ID')
    access_token = get_env('FACEBOOK_ACCESS_TOKEN')
    if not page_id or not access_token:
        logger.error('Facebook credentials missing.')
        return False, 'Credentials missing.'
    url = f'https://graph.facebook.com/{page_id}/feed'
    data = {'message': content, 'access_token': access_token}
    try:
        resp = requests.post(url, data=data, timeout=10)
        if resp.status_code == 200:
            return True, 'Post successful.'
        else:
            try:
                err = resp.json().get('error', {})
            except Exception:
                err = {}
            if err.get('code') == 190:
                new_token = _refresh_facebook_page_token(page_id)
                if new_token:
                    retry = requests.post(url, data={'message': content, 'access_token': new_token}, timeout=10)
                    if retry.status_code == 200:
                        return True, 'Post successful.'
                    logger.error(f'Facebook error after refresh: {retry.text}')
                    return False, f'Error after refresh: {retry.text}'
            logger.error(f'Facebook error: {resp.text}')
            return False, f'Error: {resp.text}'
    except Exception as e:
        logger.error(f'Facebook exception: {e}')
        return False, f'Exception: {e}'
