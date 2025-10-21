import os
import requests
from utils.logger import get_logger
from utils.env import get_env

logger = get_logger()

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
            logger.error(f'Facebook error: {resp.text}')
            return False, f'Error: {resp.text}'
    except Exception as e:
        logger.error(f'Facebook exception: {e}')
        return False, f'Exception: {e}'
