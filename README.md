# 🔔 Data Engineering Job Alert — Denmark & Sweden

Automated job alert that runs every 30 minutes on GitHub Actions (free),
searches multiple Danish and Swedish job sites, and emails new postings
directly to your inbox.

## What it monitors

| Source | Coverage |
|---|---|
| Indeed Denmark | Data Engineer, Analytics Engineer, Data Consultant, Data Architect |
| Indeed Sweden | Data Engineer, Analytics Engineer, Data Consultant |
| Jobindex.dk | Copenhagen area — Data Engineer, Analytics Engineer, Data Consultant |
| TheHub.io | Copenhagen startups & scaleups |
| Jobnet.dk | Official Danish job portal |

## How it works

1. Runs every 30 minutes on weekdays (07:00–21:00 CET), 3x/day on weekends
2. Fetches RSS feeds and scrapes job boards for new postings
3. Deduplicates against previously seen jobs (no repeat emails)
4. Sends a formatted HTML email only when new jobs are found
5. Persists seen job IDs via GitHub Actions cache

## Setup (5 minutes)

### Step 1 — Fork this repo
Click **Fork** top right on GitHub.

### Step 2 — Get a Gmail App Password
1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Security → 2-Step Verification → turn ON
3. Security → App passwords → create one named "job-alert"
4. Copy the 16-character password shown

### Step 3 — Add GitHub Secrets
In your forked repo: **Settings → Secrets and variables → Actions → New secret**

| Secret name | Value |
|---|---|
| `GMAIL_ADDRESS` | your Gmail address |
| `GMAIL_APP_PASSWORD` | the 16-char app password from Step 2 |

### Step 4 — Enable Actions
Go to **Actions** tab in your repo → click **"I understand my workflows, enable them"**

### Step 5 — Test it manually
Actions → "Job Alert — Data Engineering DK & SE" → **Run workflow**

You should receive an email within 60 seconds.

## Email preview

The email groups jobs by country (🇩🇰 Denmark / 🇸🇪 Sweden) with:
- Job title
- Company name
- Source (Indeed / Jobindex / TheHub)
- Direct link to apply

## Customising

Edit `src/job_alert.py`:

```python
# Change target roles
TITLE_KEYWORDS = [
    "data engineer",
    "analytics engineer",
    ...
]

# Change recipient
RECIPIENT = "your@email.com"

# Add more RSS feeds
RSS_FEEDS = [...]
```

## Cost

**Free.** GitHub Actions gives 2,000 free minutes/month on public repos.
This workflow uses ~1 minute per run × ~300 runs/month = ~300 minutes/month.
