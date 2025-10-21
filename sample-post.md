# 🚀 Introducing Shellcaster: Post to Social Platforms from Your Terminal with Markdown
We’re thrilled to announce the launch of Shellcaster — an open-source, extensible CLI tool that lets you write once in Markdown and post everywhere from your terminal.

Whether you're a developer, content creator, or automation enthusiast, Shellcaster empowers you to publish content to social platforms without leaving your shell.

### ✨ What Is Shellcaster?

Shellcaster is a command-line tool that turns Markdown files into social media posts, automatically formatting and publishing your content to platforms like:

🐦 Twitter / X
🧵 Facebook
📝 LinkedIn
📷 Instagram (via captioning)
📝 Blogger

### 📬 Newsletters & blogs (via webhook or API)

You write your content in simple Markdown. Shellcaster takes care of parsing, formatting, and pushing it live to one or many platforms.

### 🔧 Features

✅ Markdown-first content workflow
🔗 Cross-platform publishing
⚙️ Extensible architecture — add your own integrations
⏱️ Schedule posts (via CRON or CI)

### 🛠 Example Usage
```bash

shellcaster --file my-thread.md --platform twitter,linkedin
Your my-thread.md might look like:
```
```markdown

# This is a thread about open-source

Shellcaster just launched. It's an open-source CLI tool that posts Markdown to your social accounts.

---

You write once. It posts everywhere.

GitHub: https://github.com/yourname/shellcaster
Shellcaster auto-splits this into platform-specific formats, complete with character limits and formatting tweaks.
```

