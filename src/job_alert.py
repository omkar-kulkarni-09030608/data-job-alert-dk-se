"""
Job Alert Script — Data Engineering roles in Denmark & Sweden
Searches Indeed RSS, Jobindex RSS, TheHub, and Jobnet
Sends email digest of NEW jobs only (deduplicates via seen_jobs.json)
"""

import os
import json
import smtplib
import hashlib
import feedparser
import requests
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from bs4 import BeautifulSoup

# ── CONFIG ────────────────────────────────────────────────────────────────────
RECIPIENT       = "omkarkulkarni.1988@gmail.com"
SENDER_EMAIL    = os.environ.get("GMAIL_ADDRESS")
SENDER_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
SEEN_JOBS_FILE  = Path("seen_jobs.json")

# ── RSS FEEDS ─────────────────────────────────────────────────────────────────
RSS_FEEDS = [
    # Indeed Denmark
    {
        "source": "Indeed DK",
        "url": "https://dk.indeed.com/rss?q=data+engineer+OR+analytics+engineer+OR+data+consultant+OR+data+architect&l=Copenhagen%2C+Denmark&sort=date&fromage=1",
        "country": "Denmark"
    },
    {
        "source": "Indeed DK",
        "url": "https://dk.indeed.com/rss?q=data+engineer+OR+analytics+engineer&l=Denmark&sort=date&fromage=1",
        "country": "Denmark"
    },
    # Indeed Sweden
    {
        "source": "Indeed SE",
        "url": "https://se.indeed.com/rss?q=data+engineer+OR+analytics+engineer+OR+data+consultant&l=Stockholm&sort=date&fromage=1",
        "country": "Sweden"
    },
    {
        "source": "Indeed SE",
        "url": "https://se.indeed.com/rss?q=data+engineer+OR+analytics+engineer&l=Sweden&sort=date&fromage=1",
        "country": "Sweden"
    },
    # Jobindex Denmark (Copenhagen area)
    {
        "source": "Jobindex",
        "url": "https://www.jobindex.dk/jobsoegning.xml?q=data+engineer&where=storkbh",
        "country": "Denmark"
    },
    {
        "source": "Jobindex",
        "url": "https://www.jobindex.dk/jobsoegning.xml?q=analytics+engineer&where=storkbh",
        "country": "Denmark"
    },
    {
        "source": "Jobindex",
        "url": "https://www.jobindex.dk/jobsoegning.xml?q=data+consultant&where=storkbh",
        "country": "Denmark"
    },
    # Jobnet Denmark (official Danish job portal)
    {
        "source": "Jobnet",
        "url": "https://job.jobnet.dk/CV/FindWork/Search?SearchString=data+engineer&RegionId=1&County=1",
        "country": "Denmark"
    },
]

# Keywords to match in title (case-insensitive)
TITLE_KEYWORDS = [
    "data engineer",
    "analytics engineer",
    "data consultant",
    "data developer",
    "data architect",
    "data platform",
    "etl developer",
    "bi developer",
    "bi engineer",
    "data specialist",
]

# Keywords to EXCLUDE (avoid irrelevant hits)
EXCLUDE_KEYWORDS = [
    "student",
    "intern",
    "praktik",
    "junior",
    "trainee",
]


def load_seen_jobs() -> set:
    """Load previously seen job IDs from file."""
    if SEEN_JOBS_FILE.exists():
        with open(SEEN_JOBS_FILE) as f:
            data = json.load(f)
            return set(data.get("seen", []))
    return set()


def save_seen_jobs(seen: set):
    """Persist seen job IDs to file."""
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump({"seen": list(seen), "last_run": datetime.now(timezone.utc).isoformat()}, f, indent=2)


def make_job_id(title: str, url: str) -> str:
    """Create a stable unique ID for a job from title + url."""
    raw = f"{title.lower().strip()}|{url.strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def is_relevant(title: str) -> bool:
    """Check if job title matches our target roles."""
    title_lower = title.lower()
    has_keyword = any(kw in title_lower for kw in TITLE_KEYWORDS)
    has_exclude = any(ex in title_lower for ex in EXCLUDE_KEYWORDS)
    return has_keyword and not has_exclude


def fetch_rss_jobs(feed_config: dict, seen: set) -> list:
    """Fetch and parse an RSS feed, return new unseen jobs."""
    new_jobs = []
    try:
        feed = feedparser.parse(feed_config["url"])
        for entry in feed.entries:
            title   = entry.get("title", "").strip()
            url     = entry.get("link", "").strip()
            summary = entry.get("summary", "")
            pub     = entry.get("published", "")

            if not title or not url:
                continue
            if not is_relevant(title):
                continue

            job_id = make_job_id(title, url)
            if job_id in seen:
                continue

            # Try to extract company from summary (Indeed includes it)
            company = "—"
            if "<b>" in summary:
                soup = BeautifulSoup(summary, "html.parser")
                bold_tags = soup.find_all("b")
                if bold_tags:
                    company = bold_tags[0].get_text(strip=True)

            new_jobs.append({
                "id":      job_id,
                "title":   title,
                "company": company,
                "url":     url,
                "source":  feed_config["source"],
                "country": feed_config["country"],
                "posted":  pub,
            })

    except Exception as e:
        print(f"  ⚠ Error fetching {feed_config['source']}: {e}")

    return new_jobs


def fetch_thehub_jobs(seen: set) -> list:
    """Scrape TheHub.io for data engineering jobs in Copenhagen."""
    new_jobs = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; JobAlertBot/1.0)"}
        url = "https://thehub.io/jobs?q=data+engineer&location=Copenhagen"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return new_jobs

        soup = BeautifulSoup(resp.text, "html.parser")

        # TheHub job cards
        for card in soup.select("a[data-cy='job-ad-title']"):
            title   = card.get_text(strip=True)
            job_url = "https://thehub.io" + card.get("href", "")

            if not is_relevant(title):
                continue

            job_id = make_job_id(title, job_url)
            if job_id in seen:
                continue

            # Try to get company name from parent card
            parent = card.find_parent("div", class_=lambda x: x and "company" in x.lower())
            company = parent.get_text(strip=True) if parent else "—"

            new_jobs.append({
                "id":      job_id,
                "title":   title,
                "company": company,
                "url":     job_url,
                "source":  "TheHub.io",
                "country": "Denmark",
                "posted":  "Recent",
            })

    except Exception as e:
        print(f"  ⚠ Error fetching TheHub: {e}")

    return new_jobs


def build_email_html(jobs: list) -> str:
    """Build a clean HTML email with job listings."""
    now = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")

    dk_jobs = [j for j in jobs if j["country"] == "Denmark"]
    se_jobs = [j for j in jobs if j["country"] == "Sweden"]

    def job_block(job):
        return f"""
        <div style="border:1px solid #e0e0e0; border-radius:8px; padding:14px 16px;
                    margin-bottom:10px; background:#ffffff;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <strong style="font-size:15px; color:#1A1A2E;">{job['title']}</strong>
            <span style="background:#EAF3DE; color:#27500A; font-size:11px;
                         padding:2px 8px; border-radius:4px; white-space:nowrap;
                         margin-left:8px;">{job['source']}</span>
          </div>
          <p style="margin:4px 0; font-size:13px; color:#555;">
            {job['company']} &nbsp;·&nbsp; {job['country']}
            {f"&nbsp;·&nbsp; {job['posted']}" if job['posted'] != 'Recent' else ''}
          </p>
          <a href="{job['url']}"
             style="font-size:13px; color:#185FA5; text-decoration:none;">
            View job →
          </a>
        </div>"""

    def section(title, flag, jobs_list):
        if not jobs_list:
            return ""
        blocks = "".join(job_block(j) for j in jobs_list)
        return f"""
        <h3 style="color:#185FA5; font-size:15px; margin:24px 0 10px;
                   border-bottom:2px solid #E6F1FB; padding-bottom:6px;">
          {flag} {title} ({len(jobs_list)} new)
        </h3>
        {blocks}"""

    return f"""
    <html><body style="font-family:Arial,sans-serif; max-width:640px;
                        margin:0 auto; color:#222; padding:20px;">

      <div style="background:#185FA5; border-radius:10px 10px 0 0;
                  padding:20px 24px; margin-bottom:0;">
        <h2 style="color:#ffffff; margin:0; font-size:20px;">
          🔔 Data Engineering Job Alert
        </h2>
        <p style="color:#B5D4F4; margin:6px 0 0; font-size:13px;">
          {len(jobs)} new jobs found &nbsp;·&nbsp; {now}
        </p>
      </div>

      <div style="background:#F8FAFC; border:1px solid #e0e0e0;
                  border-top:none; border-radius:0 0 10px 10px; padding:20px 24px;">

        <p style="font-size:13px; color:#555; margin-top:0;">
          Hi Omkar, here are the latest Data Engineering, Analytics Engineering,
          and Data Consultant roles in Denmark and Sweden matching your profile.
        </p>

        {section("Denmark", "🇩🇰", dk_jobs)}
        {section("Sweden", "🇸🇪", se_jobs)}

        <hr style="border:none; border-top:1px solid #e0e0e0; margin:20px 0;">
        <p style="font-size:11px; color:#999; margin:0;">
          Matched roles: Data Engineer · Analytics Engineer · Data Consultant ·
          Data Architect · Data Platform Engineer · ETL Developer · BI Engineer<br>
          Sources: Indeed DK/SE · Jobindex · TheHub.io · Jobnet
        </p>
      </div>

    </body></html>"""


def send_email(jobs: list):
    """Send the job alert email via Gmail SMTP."""
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("✗ GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set in environment")
        return False

    subject = f"[Job Alert] {len(jobs)} new Data Engineering jobs — Denmark & Sweden"
    html    = build_email_html(jobs)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT, msg.as_string())
        print(f"✓ Email sent: {subject}")
        return True
    except Exception as e:
        print(f"✗ Email failed: {e}")
        return False


def main():
    print(f"\n{'='*55}")
    print(f"Job Alert Run — {datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')}")
    print(f"{'='*55}")

    seen     = load_seen_jobs()
    all_jobs = []

    # Fetch RSS feeds
    for feed in RSS_FEEDS:
        print(f"  Checking {feed['source']} ({feed['country']})...")
        jobs = fetch_rss_jobs(feed, seen)
        print(f"    → {len(jobs)} new jobs")
        all_jobs.extend(jobs)

    # Fetch TheHub
    print("  Checking TheHub.io (Denmark)...")
    hub_jobs = fetch_thehub_jobs(seen)
    print(f"    → {len(hub_jobs)} new jobs")
    all_jobs.extend(hub_jobs)

    # Deduplicate within this run (same job may appear in multiple feeds)
    seen_this_run = set()
    unique_jobs   = []
    for job in all_jobs:
        if job["id"] not in seen_this_run:
            seen_this_run.add(job["id"])
            unique_jobs.append(job)

    print(f"\n  Total new unique jobs: {len(unique_jobs)}")

    if unique_jobs:
        print(f"\n  New jobs found:")
        for j in unique_jobs:
            print(f"    [{j['country']}] {j['title']} — {j['company']} ({j['source']})")

        sent = send_email(unique_jobs)

        if sent:
            # Only mark as seen if email was sent successfully
            for job in unique_jobs:
                seen.add(job["id"])
            save_seen_jobs(seen)
            print(f"\n✓ Marked {len(unique_jobs)} jobs as seen")
    else:
        print("\n  No new jobs this run — no email sent")

    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
