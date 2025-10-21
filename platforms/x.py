
import os
import json
import time
import base64
import hashlib
import secrets
import webbrowser
import requests
from requests_oauthlib import OAuth2Session, OAuth1Session
from typing import List, Dict, Optional, Tuple, Any
from utils.logger import get_logger
from utils.env import get_env
from urllib.parse import urlparse, parse_qs

logger = get_logger()

def load_token():
    """Load token from file if it exists."""
    token_file = '.x_token.json'
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            return json.load(f)
    return None

def save_token(token):
    """Save token to file."""
    token_file = '.x_token.json'
    with open(token_file, 'w') as f:
        json.dump(token, f)

def refresh_token(client_id, client_secret, refresh_token_value):
    """Refresh the access token using the refresh token."""
    token_url = 'https://api.twitter.com/2/oauth2/token'
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token_value
    }
    
    auth = (client_id, client_secret)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    
    response = requests.post(
        token_url,
        data=data,
        auth=auth,
        headers=headers
    )
    
    if response.status_code == 200:
        token_data = response.json()
        # Ensure refresh_token is included in the response
        if 'refresh_token' not in token_data:
            token_data['refresh_token'] = refresh_token_value
        save_token(token_data)
        return token_data
    else:
        logger.error(f'Failed to refresh token: {response.text}')
        return None

def get_authenticated_session() -> Any:
    """
    Get an authenticated OAuth 2.0 session for X (Twitter) API.
    Handles the OAuth 2.0 PKCE flow with automatic browser opening.
    Returns an authenticated OAuth2Session or None if authentication fails.
    """
    client_id = get_env('X_CLIENT_ID')
    client_secret = get_env('X_CLIENT_SECRET')
    
    # OAuth 2.0 endpoints
    authorization_base_url = 'https://twitter.com/i/oauth2/authorize'
    token_url = 'https://api.twitter.com/2/oauth2/token'
    redirect_uri = 'https://localhost:8080/callback'  # Must match the one in your Twitter Developer Portal
    
    if not client_id or not client_secret:
        logger.error('X_CLIENT_ID and X_CLIENT_SECRET environment variables must be set')
        return None
    
    # Check for existing token
    token = load_token()
    
    # If we have a valid token, try to use it
    if token:
        # Check if token is expired
        if token.get('expires_at', 0) > time.time() + 60:  # 1 minute buffer
            try:
                twitter = OAuth2Session(
                    client_id,
                    token=token,
                    auto_refresh_url=token_url,
                    auto_refresh_kwargs={
                        'client_id': client_id,
                        'client_secret': client_secret,
                    },
                    token_updater=save_token
                )
                # Test the token with a simple request
                test_response = twitter.get('https://api.twitter.com/2/users/me')
                if test_response.status_code == 200:
                    return twitter
                logger.warning('Stored token is invalid, proceeding with new authentication')
            except Exception as e:
                logger.warning(f'Error using stored token: {e}, proceeding with new authentication')
        
        # Try to refresh the token if it's expired
        if 'refresh_token' in token:
            try:
                new_token = refresh_token(client_id, client_secret, token['refresh_token'])
                if new_token:
                    return OAuth2Session(
                        client_id,
                        token=new_token,
                        auto_refresh_url=token_url,
                        auto_refresh_kwargs={
                            'client_id': client_id,
                            'client_secret': client_secret,
                        },
                        token_updater=save_token
                    )
            except Exception as e:
                logger.warning(f'Error refreshing token: {e}, proceeding with new authentication')
    
    # If we get here, we need a new token
    # Generate PKCE code verifier and challenge
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode('ascii')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('ascii')).digest()
    ).rstrip(b'=').decode('ascii')
    
    twitter = OAuth2Session(
        client_id,
        redirect_uri=redirect_uri,
        scope=['tweet.read', 'tweet.write', 'users.read', 'offline.access']
    )
    
    # Get authorization URL with PKCE
    auth_url, _ = twitter.authorization_url(
        authorization_base_url,
        code_challenge=code_challenge,
        code_challenge_method='S256'
    )
    
    # Open browser for authorization
    print('Opening browser for X (Twitter) authorization...')
    webbrowser.open(auth_url)
    
    # Get the authorization code from the user
    try:
        redirect_response = input('After authorizing, paste the full redirect URL here: ')
        
        # Extract the authorization code from the redirect URL
        query = urlparse(redirect_response).query
        code = parse_qs(query).get('code')
        
        if not code:
            logger.error('No authorization code found in the redirect URL')
            return None
            
        # Prepare the token request data
        token_data = {
            'code': code[0],
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
            'code_verifier': code_verifier
        }
        
        # Make the token request with Basic Auth
        auth = (client_id, client_secret)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        token_response = requests.post(
            token_url,
            data=token_data,
            auth=auth,
            headers=headers
        )
        
        if token_response.status_code != 200:
            logger.error(f'Token request failed: {token_response.text}')
            return None
            
        # Parse and save the token response
        token_data = token_response.json()
        # Add expires_at for easier expiration checking
        token_data['expires_at'] = time.time() + token_data.get('expires_in', 7200)
        save_token(token_data)
        twitter.token = token_data
        
        return twitter
        
    except Exception as e:
        logger.error(f'Authentication failed: {e}')
        return None

def post(content):
    """
    Post content to X (Twitter) using OAuth 2.0 with PKCE
    """
    # Get authenticated session
    twitter = get_authenticated_session()
    if not twitter:
        return False, 'Authentication failed'
        
    try:
        # Post the tweet
        response = twitter.post(
            "https://api.twitter.com/2/tweets",
            json={"text": content[:280]}
        )
        
        response_data = response.json()
        
        if response.status_code == 201:
            tweet_id = response_data.get('data', {}).get('id')
            tweet_url = f'https://twitter.com/user/status/{tweet_id}' if tweet_id else 'Unknown URL'
            return True, f'Post successful. {tweet_url}'
        else:
            error_detail = response_data.get('detail', 'Unknown error')
            logger.error(f'X API error: {error_detail}')
            return False, f'Error: {error_detail}'
            
    except Exception as e:
        logger.error(f'X exception: {e}')
        return False, f'Exception: {e}'


def get_trends(woeid: int = 1) -> List[Dict[str, str]]:
    """
    Get trending topics from X (Twitter) for a specific location.
    
    Args:
        woeid: Where On Earth ID for the location (1 = Worldwide)
        
    Returns:
        List of trending topics with name and URL
    """
    # First try v2 free-tier endpoint with OAuth2 session
    try:
        twitter = get_authenticated_session()
        if twitter:
            v2_url = 'https://api.twitter.com/2/users/personalized_trends'
            v2_resp = twitter.get(v2_url)
            if v2_resp.status_code == 200:
                data = v2_resp.json()
                items = []
                # Defensive parsing: expect a list under 'data' or top-level list
                raw_list = []
                if isinstance(data, list):
                    raw_list = data
                elif isinstance(data, dict):
                    raw_list = data.get('data') or data.get('trends') or []
                # Map to name/url pairs when possible
                for it in (raw_list or [])[:10]:
                    name = (
                        it.get('name')
                        or it.get('topic')
                        or it.get('display_name')
                        or it.get('query')
                        or ''
                    )
                    if not name and isinstance(it, str):
                        name = it
                    url = it.get('url') if isinstance(it, dict) else ''
                    if name:
                        items.append({'name': name, 'url': url or '', 'tweet_volume': None})
                if items:
                    return items
            else:
                logger.error(f'Failed v2 personalized_trends: {v2_resp.status_code} {v2_resp.text}')
    except Exception as e:
        logger.error(f'Error fetching v2 personalized trends: {e}')

    # Fallback to legacy v1.1 trends (requires OAuth1 keys and access)
    consumer_key = get_env('X_CONSUMER_KEY')
    consumer_secret = get_env('X_CONSUMER_SECRET')
    access_token = get_env('X_ACCESS_TOKEN')
    access_token_secret = get_env('X_ACCESS_TOKEN_SECRET')

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        logger.error('X OAuth1 credentials missing for v1.1 trends fallback.')
        return []

    try:
        oauth = OAuth1Session(
            consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )

        trends_url = f"https://api.twitter.com/1.1/trends/place.json?id={woeid}"
        response = oauth.get(trends_url)

        if response.status_code == 200:
            trends_data = response.json()
            if trends_data and isinstance(trends_data, list) and len(trends_data) > 0:
                trends = []
                for trend in trends_data[0].get('trends', [])[:10]:
                    trends.append({
                        'name': trend.get('name', ''),
                        'url': trend.get('url', ''),
                        'tweet_volume': trend.get('tweet_volume', 0)
                    })
                return trends
        else:
            logger.error(f'Failed to fetch v1.1 trends: {response.text}')

    except Exception as e:
        logger.error(f'Error fetching v1.1 trends: {str(e)}')

    return []
