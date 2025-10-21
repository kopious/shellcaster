# Shellcaster CLI

Broadcast a message to multiple social platforms (Facebook, LinkedIn, X, Blogger) from your terminal with a single command.

## Features

- Post via CLI (`--post` or `--file`)
- Modular and easy to extend (add new platforms easily)
- Color-coded output for success/failure
- Centralized logging and error handling
- Reads credentials securely from `.env`

## Usage

```bash
python shellcaster.py --post "Hello from CLI"
python shellcaster.py --post "Hello from CLI" --platform facebook
python shellcaster.py --post "Hello from CLI" --platform linkedin
python shellcaster.py --post "Hello from CLI" --platform x
python shellcaster.py --post "Hello from CLI" --platform blogger
python shellcaster.py --platform facebook,linkedin,x,blogger --file "post.md"
```

- If `--platform` is omitted, all platforms are used.
- If `--file` is provided, only markdown files are accepted.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env_example` to `.env` and fill in your credentials (see below).
3. Run the CLI as shown above.

## Environment Variables

Add these to your `.env` file:

```env
# Facebook 
FACEBOOK_PAGE_ID=your_facebook_page_id
FACEBOOK_ACCESS_TOKEN=your_facebook_access_token

# LinkedIn
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token
LINKEDIN_AUTHOR_URN=urn:li:person:your_linkedin_urn

# X (Twitter)
X_CONSUMER_KEY=your_x_consumer_key
X_CONSUMER_SECRET=your_x_consumer_secret
X_ACCESS_TOKEN=your_x_access_token
X_ACCESS_TOKEN_SECRET=your_x_access_token_secret

# Blogger
BLOGGER_ACCESS_TOKEN=your_blogger_access_token
BLOGGER_BLOG_ID=your_blogger_blog_id
```

Note: you can get your page access token from the Facebook Graph API Explorer https://developers.facebook.com/tools/explorer/?method=GET&path=%2Fme%2Faccounts

You need to re-generate the token before the permissions take effect.


## Example `post.md`

```markdown
# 💥 New Recon Tool Released: Shellcaster CLI

Just dropped a new open-source CLI tool for bug bounty hunters and ethical hackers.  
Shellcaster lets you broadcast to **Facebook**, **LinkedIn**, **X**, and **Blogger** — all from your terminal.  
Designed for speed, stealth, and seamless automation.

![Shellcaster Screenshot](https://example.com/images/shellcaster-demo.png)

Check it out here: [GitHub Repo](https://github.com/yourname/shellcaster-cli)

#HackerTools #BugBounty #OSINT #CyberSecurity
```

## Extending

To add a new platform:
- Create `platforms/newplatform.py` with a `post(content)` function returning `(bool, str)` for success and message.
- Add the new platform to `PLATFORM_MAP` in `shellcaster.py`.

## Logging

- Logs are sent to stderr and include errors and info for debugging.

## Security

- Never commit your `.env` with real credentials.
- Tokens are loaded at runtime and not logged.

---

**Shellcaster** is designed for speed, security, and seamless automation. Contributions welcome!