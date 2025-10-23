import os
import sys
import json
import requests
import time
import re
import subprocess

import warnings
warnings.filterwarnings('ignore')
import random

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple

from utils.env import ensure_env_loaded as load_env, get_env
from utils.logger import get_logger

# Blogger helpers
from platforms.blogger import get_authenticated_service, markdown_to_html

# Gemini
import google.generativeai as genai

MAX_TOKENS = 10000

HASHTAGS = [
    '#Crypto', '#Blockchain', '#Web3', '#DeFi', '#Bitcoin', '#Ethereum',
    '#Altcoins', '#NFT', '#AI', '#FinTech', '#CryptoNews', '#OnChain',
    '#Layer2', '#SmartContracts', '#Stablecoins', '#YieldFarming',
    '#Tokenization', '#Web3Gaming', '#Airdrop', '#CryptoMarkets'
]

def choose_gemini_model() -> str:
    """Pick an available Gemini model that supports generateContent.
    Preference order is env GEMINI_MODEL, then a shortlist; finally, auto-detect via list_models().
    """
    api_key = get_env('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY not set')
    genai.configure(api_key=api_key)

    preferred = []
    env_model = get_env('GEMINI_MODEL')
    if env_model:
        preferred.append(env_model)

    # Try preferred list first
    for name in preferred:
        try:
            m = genai.GenerativeModel(name)
            # Dry call to ensure it exists via model info fetch
            # If it doesn't raise, accept it
            return name
        except Exception:
            continue

    # Auto-detect from available models
    try:
        models = genai.list_models()
        for m in models:
            # Some SDK versions expose supported_generation_methods
            methods = getattr(m, 'supported_generation_methods', None) or getattr(m, 'generation_methods', None)
            if methods and ('generateContent' in methods or 'generate_content' in methods):
                return m.name
        # Fallback to first model name
        if models:
            return models[0].name
    except Exception:
        pass
    # Last resort
    return 'gemini-2.5-flash'


logger = get_logger()


def load_template() -> str:
    """Load the blog post template from post.md (structure)."""
    path = os.path.join(os.path.dirname(__file__), 'post.md')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        # Minimal fallback template
        return (
            '# {title}\n\n'
            '{summary}\n\n'
            '{body}\n\n'
            '{cta}\n'
        )


def generate_blog_with_gemini(topic: str, template_text: str, site_tone_hint: str = 'Professional, concise, informative, in the tone of blog.arbitengine.com') -> str:
    """Generate a blog post using Gemini and the provided template as a guide."""
    api_key = get_env('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY not set')

    genai.configure(api_key=api_key)

    prompt = (
        f"You are a content writer for a crypto blog. Write a timely post using the strict markdown outline below.\n"
        f"Topic: {topic}\n"
        f"Tone: {site_tone_hint}\n"
        f"Rules:\n"
        f"- Use markdown only.\n"
        f"- Do not include financial advice.\n"
        f"- No placeholders; keep it factual and recent-context framed.\n"
        f"Structure:\n"
        f"- Begin with a single H1 title line.\n"
        f"- Include a 1–3 sentence summary as a blockquote.\n"
        f"- Then continue as a cohesive article with natural, model-chosen section headings.\n"
        f"- End with keywords as hashtags.\n"
        f"TEMPLATE START\n{template_text}\nTEMPLATE END\n"
    )
    name = choose_gemini_model()
    model = genai.GenerativeModel(name)
    cfg = {"temperature": 0.7, "max_output_tokens": int(MAX_TOKENS*3)}

    def try_generate(p: str) -> str:
        resp = model.generate_content(p, generation_config=cfg)
        # Prefer candidates parts text if present
        # print(resp)
        if getattr(resp, 'candidates', None):
            for cand in resp.candidates:
                parts = getattr(cand, 'content', None)
                if parts and getattr(parts, 'parts', None):
                    texts = []
                    for part in parts.parts:
                        t = getattr(part, 'text', None)
                        if t:
                            texts.append(t)
                    if texts:
                        return "\n".join(texts).strip()
        # No safe text available
        return ''

    text = try_generate(prompt)
    if not text:
        print('[workflow] Gemini blog generation produced empty content.')
        raise RuntimeError('Gemini returned empty content')
    print(f"[workflow] Gemini model used: {name}")
    return text.strip()


def save_topic_md(content: str, topic: str) -> str:
    """Save generated content to topic-<slug>.md (archive)."""
    def slugify(s: str) -> str:
        s = s.strip().lower()
        # keep alnum and spaces/dashes
        s = re.sub(r'[^a-z0-9\s-]', '', s)
        s = re.sub(r'\s+', '-', s).strip('-')
        # keep it brief
        return '-'.join(s.split('-')[:8]) or 'post'

    slug = slugify(topic)
    filename = f'topic-{slug}.md'
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    logger.info(f'Saved blog content to {path}')
    print(f"[workflow] Saved blog to {filename}")
    return path

def format_blog_markdown(content: str, topic: str) -> str:
    """Lightly normalize markdown: ensure H1 title, normalize blank lines, ensure key headings.
    This does not rewrite content, only structural touches.
    """
    import re
    text = content.replace('\r\n', '\n').replace('\r', '\n')
    lines = [l.rstrip() for l in text.split('\n')]
    # Ensure title
    if not lines or not lines[0].startswith('# '):
        lines = [f"# {topic}"] + ([''] if lines and lines[0] else []) + lines
    # Normalize multiple blank lines
    out = []
    blank = False
    for l in lines:
        if l.strip() == '':
            if not blank:
                out.append('')
            blank = True
        else:
            out.append(l)
            blank = False
    # Ensure Key Takeaways heading exists if referenced bullets exist
    joined = '\n'.join(out)
    if '## Key Takeaways' not in joined and re.search(r'^- ', joined, re.M):
        # insert after summary blockquote if present, else after title
        insert_idx = 1
        for i, l in enumerate(out[:20]):
            if l.startswith('> '):
                insert_idx = i + 2
                break
        out[insert_idx:insert_idx] = ['## Key Takeaways', '']
    return '\n'.join(out).strip() + '\n'


def post_to_blogger(markdown_path: str) -> str:
    """Create a Blogger post and return its URL."""
    blog_id = get_env('BLOGGER_BLOG_ID')
    if not blog_id:
        raise RuntimeError('BLOGGER_BLOG_ID missing')

    creds = get_authenticated_service()
    if not creds:
        raise RuntimeError('Blogger authentication failed')

    with open(markdown_path, 'r', encoding='utf-8') as f:
        md = f.read()

    lines = md.splitlines()
    title = lines[0].lstrip('# ').strip() if lines else 'Post'
    body_md = '\n'.join(lines[1:]) if len(lines) > 1 else ''
    html_content = markdown_to_html(body_md)

    url = f'https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/'
    headers = {
        'Authorization': f'Bearer {creds.token}',
        'Content-Type': 'application/json',
    }
    payload = {
        "kind": "blogger#post",
        "blog": {"id": blog_id},
        "title": title,
        "content": html_content,
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f'Blogger error: {resp.status_code} {resp.text}')
    data = resp.json()
    post_url = data.get('url') or data.get('selfLink') or ''
    if not post_url:
        logger.warning('Blogger response missing post URL')
    return post_url


def compose_social_message(topic: str, url: str) -> str:
    # topic here is the full markdown of the blog post
    md = topic or ''
    title = ''
    summary = ''
    for line in md.splitlines():
        if not title and line.startswith('# '):
            title = line.lstrip('# ').strip()
            continue
        if not summary and line.lstrip().startswith('> '):
            # Use the first blockquote line as the summary
            summary = line.lstrip()[2:].strip()
        if title and summary:
            break

    # Fallbacks if parsing fails
    if not title:
        title = 'New Article'
    if not summary:
        # Try to derive a short snippet from the first non-empty paragraph after title
        lines = [l for l in md.splitlines() if l.strip()]
        if lines:
            # Prefer a non-heading, non-image line
            for l in lines:
                if not l.startswith('#') and not l.startswith('!['):
                    summary = l.strip()
                    break
        summary = summary or 'Read the latest insights.'

    snippet = summary[:60].rstrip()
    if len(summary) > 60:
        snippet += '…'

    base = f"{title} — {snippet} {url}".strip()
    chosen = random.sample(HASHTAGS, k=min(3, len(HASHTAGS)))
    tags = ' '.join(chosen)
    return f"{base}\n{tags}"


def post_to_social_platforms(message: str, platforms: str = 'x,facebook,linkedin') -> bool:
    """Execute shellcaster CLI to post message to social platforms.
    
    Args:
        message: The message content to post
        platforms: Comma-separated list of platforms (e.g., 'x,facebook,linkedin')
    
    Returns:
        True if posting succeeded, False otherwise
    """
    cmd = [
        sys.executable, 'shellcaster.py', '--post', message, '--platform', platforms
    ]
    try:
        print(f'[workflow] Posting to social platforms via shellcaster: {platforms}...')
        proc = subprocess.run(cmd, cwd=os.path.dirname(__file__), capture_output=True, text=True)
        print(proc.stdout)
        if proc.returncode != 0:
            print(proc.stderr)
            return False
        return True
    except Exception as e:
        print(f"[workflow] Social posting failed: {e}")
        return False


def select_topic_interactively(candidates: List[str], default_index: int = 0) -> str:
    """Prompt user to select a topic from candidates list.
    
    Args:
        candidates: List of topic segments to choose from
        default_index: Index of default topic if user doesn't select (default: 0)
    
    Returns:
        Selected topic string
    """
    if not candidates:
        return ''
    
    selected_topic = candidates[default_index] if default_index < len(candidates) else candidates[0]
    
    # Interactive selection: only prompt when stdin is a TTY
    if sys.stdin and sys.stdin.isatty():
        print('\n[workflow] Select a topic by number (press Enter to use the default):')

        try:
            choice = input('Enter topic number: ').strip()
            if choice:
                num = int(choice)
                if 1 <= num <= len(candidates):
                    selected_topic = candidates[num - 1]
        except Exception:
            pass
    
    return selected_topic


def identify_trending_with_gemini(window_hours: int = 72, topic: str = None) -> Tuple[str, List[str]]:
    """Use Gemini to identify current trending topics and return (top_topic, candidates).
    We print the full structured response and parse topic segments.
    
    Args:
        window_hours: Time window in hours to search for trends (default: 72)
        topic: Optional user-provided topic domain. If None, defaults to cryptocurrency topics.
    
    Returns:
        Tuple of (default_top_topic, list_of_candidate_segments)
    """
    api_key = get_env('GEMINI_API_KEY')
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY not set')

    genai.configure(api_key=api_key)

    if not topic:
        topic = 'cryptocurrency'

    prompt = (
        f"Identify current trending topics related to: {topic}. "
        f"Use sources from the last {window_hours} hours, including news outlets, major social media platforms, and relevant analytics. "
        "Present the information in a brief, and easy-to-read, structured markdown format with clear bullets and each Segment must include bold-numbered headers like **1., **2., **n."
    )

    # Reuse model fallback
    name = choose_gemini_model()
    model = genai.GenerativeModel(name)
    cfg = {"temperature": 0.6, "max_output_tokens": int(MAX_TOKENS/2)}

    def try_generate(p: str) -> str:
        resp = model.generate_content(p, generation_config=cfg)
        # print(resp) 
        if getattr(resp, 'candidates', None):
            for topic in resp.candidates:
                parts = getattr(topic, 'content', None)
                if parts and getattr(parts, 'parts', None):
                    texts = []
                    for part in parts.parts:
                        t = getattr(part, 'text', None)
                        if t:
                            texts.append(t)
                    if texts:
                        return "\n".join(texts).strip()
        return ''

    text = try_generate(prompt)
    if not text:
        time.sleep(1)
        # Fallback prompt
        if topic:
            lighter = (
                f"List trending topics related to {topic} from the last {window_hours} hours in markdown.\n"
                "For each: a title, a 1-2 sentence why-it's-trending, and 3-6 related keywords.\n"
                "End with: 'Strongest Blog Post Recommendation: <topic>'."
            )
        else:
            lighter = (
                "List trending cryptocurrency topics from the last 72 hours in markdown.\n"
                "For each: a title, a 1-2 sentence why-it's-trending, and 3-6 related keywords/projects.\n"
                "End with: 'Strongest Blog Post Recommendation: <topic>'. Avoid financial advice."
            )
        text = try_generate(lighter)
    if not text:
        raise RuntimeError('Gemini trend identification returned empty content')
    print(f"[workflow] Gemini model used for trend ID: {name}")

    # Prefer explicit recommendation line
    top_topic = ''


    # Segment by bold-numbered headers like '**1.' up to '**2.' etc.

    lines = text.splitlines()
    indices: List[int] = []
    for idx, ln in enumerate(lines):
        s = ln.lstrip()
        if re.match(r"^\*\*\d+\.(\*\*)?\s*", s):
            indices.append(idx)
    segments: List[str] = []
    if indices:
        for i, start in enumerate(indices):
            end = indices[i + 1] if i + 1 < len(indices) else len(lines)
            seg = "\n".join(lines[start:end]).strip()
            if seg:
                segments.append(seg)

    candidates: List[str] = []
    if segments:
        print('[workflow] Parsed topic segments:')
        for i, seg in enumerate(segments, start=1):
            print(f"\n=== Topic {i} ===")
            print(seg)
            # Title is first line after stripping leading '**N.' and surrounding '**'
            # Remove leading bold markers and numbering, handling '**N.**' or '**N.'
            candidates.append(seg)

    return top_topic, candidates


def main():
    load_env()

    # Step 1: Use Gemini to identify trending topics (last 72h) and print them
    try:
        default_topic, candidates = identify_trending_with_gemini(window_hours=72)
    except Exception as e:
        print(f"[workflow] Trend identification failed: {e}")
        sys.exit(1)
    
    # Step 1a: Allow user to select topic interactively
    top_topic = select_topic_interactively(candidates, default_index=0)
    if not top_topic:
        top_topic = default_topic
    
    print(f"[workflow] Selected top topic: {top_topic}")
 
    # Step 2: Generate blog post with Gemini using post.md as template
    template_text = load_template()
    blog_md = generate_blog_with_gemini(top_topic, template_text)

    # Step 3: Save archive file
    blog_md = format_blog_markdown(blog_md, top_topic)
    topic_md_path = save_topic_md(blog_md, top_topic)

    # Step 5: Post to Blogger and get URL
    try:
        post_url = post_to_blogger(topic_md_path)
        print(f"[workflow] Blogger post URL: {post_url}")
    except Exception as e:
        print(f"[workflow] Blogger post failed: {e}")
        sys.exit(1)

    # Step 6: Compose social message and post to X, Facebook, LinkedIn via shellcaster
    message = compose_social_message(blog_md, post_url or '')
    post_to_social_platforms(message, platforms='x,facebook,linkedin')


if __name__ == '__main__':
    main()
