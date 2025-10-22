#!/usr/bin/env python3
"""Test script to verify Facebook token refresh logic."""

import sys
from platforms.facebook import _should_refresh_token, _refresh_facebook_page_token
from utils.env import get_env

# Test 1: Verify the error detection logic
print("=== Test 1: Error Detection ===")
test_error = {
    "message": "Error validating access token: Session has expired on Tuesday, 21-Oct-25 14:00:00 PDT.",
    "type": "OAuthException",
    "code": 190,
    "error_subcode": 463,
    "fbtrace_id": "Ad91lA1nf-gZakfUiTdc4Iu"
}

should_refresh = _should_refresh_token(test_error)
print(f"Should refresh token: {should_refresh}")
print()

# Test 2: Verify env vars are present
print("=== Test 2: Environment Variables ===")
app_id = get_env('FACEBOOK_APP_ID')
app_secret = get_env('FACEBOOK_APP_SECRET')
user_token = get_env('FACEBOOK_USER_ACCESS_TOKEN')
page_id = get_env('FACEBOOK_PAGE_ID')

print(f"FACEBOOK_APP_ID: {'✓ Present' if app_id else '✗ Missing'}")
print(f"FACEBOOK_APP_SECRET: {'✓ Present' if app_secret else '✗ Missing'}")
print(f"FACEBOOK_USER_ACCESS_TOKEN: {'✓ Present' if user_token else '✗ Missing'}")
print(f"FACEBOOK_PAGE_ID: {'✓ Present' if page_id else '✗ Missing'}")
print()

# Test 3: Attempt token refresh
print("=== Test 3: Token Refresh Attempt ===")
if not all([app_id, app_secret, user_token, page_id]):
    print("Cannot test refresh - missing required env vars")
    sys.exit(1)

print("Attempting to refresh token...")
new_token = _refresh_facebook_page_token(page_id)

if new_token:
    print(f"✓ Token refresh successful!")
    print(f"New token (first 20 chars): {new_token[:20]}...")
else:
    print("✗ Token refresh failed - check logs above for details")
    print("\nMost likely cause: FACEBOOK_USER_ACCESS_TOKEN is expired")
    print("You need to generate a new user access token with these permissions:")
    print("  - pages_show_list")
    print("  - pages_read_engagement")
    print("  - pages_manage_posts")
    print("  - pages_manage_metadata")
    print("  - pages_read_user_content")
