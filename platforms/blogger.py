import os
import json
import re
import requests
import webbrowser
import markdown
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from utils.logger import get_logger
from utils.env import get_env

logger = get_logger()

def get_authenticated_service():
    """Get authenticated credentials for Blogger API."""
    SCOPES = ['https://www.googleapis.com/auth/blogger']
    creds = None
    
    # Load client credentials from environment variables
    client_id = get_env('GOOGLE_CLIENT_ID')
    client_secret = get_env('GOOGLE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        logger.error('GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables must be set')
        return None
        
    try:
        # Create client config dictionary from individual env vars
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
            }
        }
        
        # The file .blogger_token.json stores the user's access and refresh tokens
        if os.path.exists('.blogger_token.json'):
            creds = Credentials.from_authorized_user_file('.blogger_token.json', SCOPES)
            
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config(
                    client_config, SCOPES
                )
                # Use local server flow which opens a browser and captures the code
                print('Opening browser to authorize access (local server flow)...')
                creds = flow.run_local_server(port=0, prompt='consent')
                
                # Save the credentials for the next run
                with open('.blogger_token.json', 'w') as token:
                    token.write(creds.to_json())
                    
        return creds
        
    except Exception as e:
        logger.error(f'Error getting credentials: {e}')
        return None

def post(content):
    """
    Post content to Blogger using API v3 and OAuth 2.0.
    """
    blog_id = get_env('BLOGGER_BLOG_ID')
    if not blog_id:
        logger.error('BLOGGER_BLOG_ID environment variable not set')
        return False, 'Blog ID missing'
        
    # Get fresh credentials
    creds = get_authenticated_service()
    if not creds:
        return False, 'Authentication failed'
        
    url = f'https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/'
    headers = {
        'Authorization': f'Bearer {creds.token}',
        'Content-Type': 'application/json',
    }
    payload = {
        "kind": "blogger#post",
        "blog": {"id": blog_id},
        "title": (content.split("\n")[0] if content else "Post"),
        "content": markdown_to_html("\n".join(content.split("\n")[1:]) if content else "")
    }
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
        if resp.status_code in (200, 201):
            return True, 'Post successful.'
        else:
            logger.error(f'Blogger error: {resp.text}')
            return False, f'Error: {resp.text}'
    except Exception as e:
        logger.error(f'Blogger exception: {e}')
        return False, f'Exception: {e}'


def markdown_to_html(markdown_text):
    """
    Convert markdown text to HTML with some custom processing.
    """
    if not markdown_text:
        return ""
        
    # Convert markdown to HTML
    html = markdown.markdown(
        markdown_text,
        extensions=[
            'fenced_code',        # Support for code blocks
            'codehilite',         # Syntax highlighting
            'tables',             # Support for tables
            'toc',                # Table of contents
            'nl2br',              # Convert newlines to <br>
            'sane_lists',         # Better list handling
            'md_in_html',         # Allow markdown within HTML
            'attr_list',          # For adding attributes to elements
            'smarty',             # Smart quotes, dashes, etc.
        ],
        output_format='html5'
    )
    
    # Add some basic styling for code blocks
    html = (
        '<style>'
        'pre { background-color: #f5f5f5; padding: 1em; border-radius: 4px; overflow-x: auto; }'
        'code { font-family: monospace; }'
        'pre code { font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace; }'
        'blockquote { border-left: 4px solid #ccc; margin: 1.5em 10px; padding: 0.5em 10px; color: #666; }'
        'blockquote > :first-child { margin-top: 0; }'
        'blockquote > :last-child { margin-bottom: 0; }'
        'table { border-collapse: collapse; width: 100%; margin: 1em 0; }'
        'th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }'
        'th { background-color: #f2f2f2; }'
        'tr:nth-child(even) { background-color: #f9f9f9; }'
        '</style>\n' + html
    )
    
    return html
