import os
import json
import base64
import webbrowser
import requests
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs, urlencode
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient, TokenExpiredError
from utils.logger import get_logger
from utils.env import get_env, set_env

class LinkedInOAuth:
    """Handles LinkedIn OAuth 2.0 authentication flow and token management."""
    
    def __init__(self):
        self.client_id = get_env('LINKEDIN_CLIENT_ID')
        self.client_secret = get_env('LINKEDIN_CLIENT_SECRET')
        self.redirect_uri = 'https://localhost:8080'
        self.token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
        self.auth_url = 'https://www.linkedin.com/oauth/v2/authorization'
        # Keep scope order stable to avoid LinkedIn "scope changed" errors
        self.scopes = [
            'openid',
            'email',
            'r_basicprofile',
            'w_organization_social',
            'profile',
            'w_member_social',
        ]
        self.token = self._load_token()
    
    def _load_token(self) -> Optional[Dict[str, Any]]:
        """Load token from environment or file."""
        access_token = get_env('LINKEDIN_ACCESS_TOKEN')
        refresh_token = get_env('LINKEDIN_REFRESH_TOKEN')
        print(f'access_token: {access_token}')
        print(f'refresh_token: {refresh_token}')
        if access_token:
            token = {'access_token': access_token}
            if refresh_token:
                token['refresh_token'] = refresh_token
            print(f'token: {token}')
            return token
       
        return None
    
    def _save_token(self, token: Dict[str, Any]) -> None:
        """Save token to environment and file."""
        set_env('LINKEDIN_ACCESS_TOKEN', token['access_token'])
        if 'refresh_token' in token:
            set_env('LINKEDIN_REFRESH_TOKEN', token['refresh_token'])
    
    def get_auth_url(self) -> str:
        """Generate the authorization URL for user consent."""
        linkedin = OAuth2Session(
            self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.scopes
        )
        auth_url, _ = linkedin.authorization_url(self.auth_url)
        return auth_url
    
    def fetch_token(self, authorization_response: str) -> Dict[str, Any]:
        """Fetch token using the authorization response."""
        linkedin = OAuth2Session(
            self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.scopes
        )
        
        # Extract the authorization code from the callback URL
        parsed = urlparse(authorization_response)
        code = parse_qs(parsed.query).get('code')
        
        if not code:
            raise ValueError("No authorization code found in the response URL")
        
        # Exchange the authorization code for an access token
        token = linkedin.fetch_token(
            self.token_url,
            client_secret=self.client_secret,
            code=code[0],
            include_client_id=True,
            timeout=10
        )
        
        self.token = token
        self._save_token(token)
        return token
    
    def refresh_token(self) -> Dict[str, Any]:
        """Refresh the access token using the refresh token."""
        if not self.token or 'refresh_token' not in self.token:
            raise ValueError("No refresh token available")
            
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.token['refresh_token'],
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        response = requests.post(self.token_url, data=data, timeout=10)
        response.raise_for_status()
        
        self.token = response.json()
        self._save_token(self.token)
        return self.token
    
    def get_session(self) -> OAuth2Session:
        """Get an authenticated session."""
        # Try to use refresh token if available
        print(f'LinkedIn token: {self.token}')
        if self.token and 'refresh_token' in self.token:
            try:
                self.refresh_token()
            except Exception as e:
                logger.warning(f"Failed to refresh token: {str(e)}. Will try to re-authenticate.")
                self.token = None
        
        # If no token or refresh failed, require authentication
        if not self.token:
            if not authenticate():
                raise ValueError("Authentication failed. Please run authenticate() first.")
            
        def token_updater(token):
            self.token = token
            self._save_token(token)
            
        return OAuth2Session(
            self.client_id,
            token=self.token,
            auto_refresh_url=self.token_url,
            auto_refresh_kwargs={
                'client_id': self.client_id,
                'client_secret': self.client_secret
            },
            token_updater=token_updater
        )

# Initialize OAuth helper
linkedin_oauth = LinkedInOAuth()

logger = get_logger()

def authenticate() -> bool:
    """
    Authenticate with LinkedIn using OAuth 2.0.
    Opens a browser for user authorization.
    """
    try:
        auth_url = linkedin_oauth.get_auth_url()
        print(f"Opening browser for LinkedIn authorization: {auth_url}")
        webbrowser.open(auth_url)
        
        redirect_url = input("After authorizing, paste the full redirect URL here: ")
        linkedin_oauth.fetch_token(redirect_url)
        print("Successfully authenticated with LinkedIn!")
        return True
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        return False

def refresh_access_token() -> bool:
    """Refresh the LinkedIn access token using the refresh token."""
    try:
        token = linkedin_oauth.refresh_token()
        logger.info("Successfully refreshed access token")
        return True
    except Exception as e:
        logger.error(f"Failed to refresh token: {str(e)}")
        return False

def get_authenticated_session() -> Optional[OAuth2Session]:
    """Get an authenticated OAuth2 session."""
    try:
        return linkedin_oauth.get_session()
    except Exception as e:
        logger.error(f"Failed to get authenticated session: {str(e)}")
        return None

def post(content: str) -> Tuple[bool, str]:
    """
    Post content to LinkedIn using v2 API (ugcPosts).
    
    Args:
        content (str): The text content to post
        
    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        # Get authenticated session
        session = get_authenticated_session()
        if not session:
            return False, "Not authenticated. Please run authenticate() first."
        
        # Determine author URN: prefer organization, fallback to member/person
        organization_urn = get_env('LINKEDIN_ORGANIZATION_URN')
        author_urn = None
        if organization_urn:
            author_urn = organization_urn if organization_urn.startswith('urn:li:organization:') else f'urn:li:organization:{organization_urn}'
        else:
            person_urn = get_env('LINKEDIN_AUTHOR_URN')
            if not person_urn:
                return False, 'Set LINKEDIN_ORGANIZATION_URN or LINKEDIN_AUTHOR_URN in your environment.'
            author_urn = person_urn if person_urn.startswith('urn:li:person:') else f'urn:li:person:{person_urn}'
        
        # Prepare the API request
        url = 'https://api.linkedin.com/v2/ugcPosts'
        headers = {
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0',
            'LinkedIn-Version': '202402'
        }
        
        # Prepare the request payload for post (organization or member)
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content,
                        "attributes": []  # Removed hashtag attributes as they're optional
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        # Make the API request
        response = session.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        
        return True, 'Post successful.'
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:  # Unauthorized
            logger.error("Token expired or invalid. Attempting to refresh...")
            if refresh_access_token():
                # Retry the request with the new token
                return post(content)
        logger.error(f"LinkedIn API error: {str(e)}")
        return False, f"API error: {str(e)}"
    except Exception as e:
        logger.error(f"Error posting to LinkedIn: {str(e)}")
        return False, f"Error: {str(e)}"
