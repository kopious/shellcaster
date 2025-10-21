"""
Shellcaster CLI: Publish to multiple social platforms from the terminal.
"""

import argparse
import sys
import os
from utils.logger import get_logger
from utils.color import print_colored, Color
from utils.env import ensure_env_loaded as load_env
from platforms import facebook, linkedin, x, blogger

logger = get_logger()

PLATFORM_MAP = {
    'facebook': facebook.post,
    'linkedin': linkedin.post,
    'x': x.post,
    'blogger': blogger.post,
}

def parse_args():
    parser = argparse.ArgumentParser(description="Broadcast a message to multiple social platforms.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--post', type=str, help='Text to post')
    group.add_argument('--file', type=str, help='Markdown file to post')
    group.add_argument('--trends', type=str, nargs='?', const='1', metavar='WOEID', 
                      help='Show trending topics for location (WOEID). Default: 1 (Worldwide)')
    parser.add_argument('--platform', type=str, help='Comma-separated list of platforms (default: all)')
    return parser.parse_args()

def load_post_content(args):
    if args.post:
        return args.post
    elif args.file:
        if not args.file.endswith('.md'):
            logger.error('Only markdown files are supported.')
            sys.exit(1)
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f'Failed to read file: {e}')
            sys.exit(1)
    else:
        logger.error('No post content provided.')
        sys.exit(1)

from utils.env import get_env

def platform_credentials_ok(platform):
    creds = {
        'facebook': ['FACEBOOK_PAGE_ID', 'FACEBOOK_ACCESS_TOKEN'],
        'linkedin': ['LINKEDIN_ACCESS_TOKEN', 'LINKEDIN_AUTHOR_URN'],
        'x': ['X_CONSUMER_KEY', 'X_CONSUMER_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_TOKEN_SECRET'],
        'blogger': ['BLOGGER_ACCESS_TOKEN', 'BLOGGER_BLOG_ID'],
    }
    required = creds.get(platform, [])
    for key in required:
        val = get_env(key)
        print(f"{key}: {val}")
        if not val or 'your_' in val:
            return False
    return True

def show_trends(woeid: str):
    """Display trending topics for the specified location."""
    try:
        woeid_int = int(woeid)
    except ValueError:
        print_colored(f"Invalid WOEID: {woeid}. Using default (Worldwide).", Color.YELLOW)
        woeid_int = 1
    
    from platforms import x as x_platform
    trends = x_platform.get_trends(woeid_int)
    
    if not trends:
        print_colored("No trends found or failed to fetch trends.", Color.RED)
        return
    
    print_colored(f"\n📊 Top {len(trends)} Trending Topics (WOEID: {woeid_int}):", Color.GREEN)
    print("-" * 80)
    for i, trend in enumerate(trends, 1):
        volume = f" ({trend['tweet_volume']:,} tweets)" if trend['tweet_volume'] else ""
        print(f"{i}. {trend['name']}{volume}")
        print(f"   🔗 {trend['url']}")
    print("")


def main():
    load_env()
    args = parse_args()
    
    # Handle trends request
    if args.trends is not None:
        show_trends(args.trends)
        return
        
    content = load_post_content(args)
    platforms = [p.strip().lower() for p in args.platform.split(',')] if args.platform else list(PLATFORM_MAP.keys())
    results = {}
    for platform in platforms:
        post_func = PLATFORM_MAP.get(platform)
        if not post_func:
            print_colored(f"Unsupported platform: {platform}", Color.YELLOW)
            continue
        if not platform_credentials_ok(platform): 
            print_colored(f"Skipping {platform}: credentials not set.", Color.YELLOW)
            continue
        try:
            success, msg = post_func(content)
            color = Color.GREEN if success else Color.RED
            print_colored(f"[{platform.capitalize()}] {msg}", color)
        except Exception as e:
            logger.exception(f"Error posting to {platform}")
            print_colored(f"[{platform.capitalize()}] Failed: {e}", Color.RED)

if __name__ == '__main__':
    main()

