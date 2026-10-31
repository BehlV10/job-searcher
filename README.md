# StaffHunt 🎯
> **Automated Job Scraper & Recruiter Outreach Copilot for Senior & Staff Software Engineers in New York & Boston**  
> *Engineered for zero-maintenance hosting on GitHub Pages with scheduled GitHub Actions updates.*

---

## 🌟 Highlights & Capabilities

- 🤖 **Multi-Source Scraping Pipeline**:
  - **LinkedIn Guest API**: Scrapes live Senior and Staff SWE roles across NYC and Boston with zero login or credentials required.
  - **Greenhouse Direct ATS**: Scrapes leading tech companies (Datadog, MongoDB, Squarespace, Flatiron Health, etc.), extracting comprehensive descriptions and mandatory NYC/MA compensation ranges.
  - **Lever Direct ATS**: Scrapes premier engineering teams (Palantir, Spotify, etc.) directly.
- 💰 **Intelligent Attribute Parsing**:
  - **Salary Extraction**: Parses annual base salary ranges (`$180,000 - $240,000/yr`, `$190k - $240k`) and hourly rates.
  - **Years of Experience (YoE)**: Parses qualification hurdles (`7+ years`, `5-8 years of experience`).
  - **Seniority & Role Leveling**: Classifies roles into `Staff / Principal`, `Senior / Lead`, or `Engineering Manager`.
  - **Tech Stack Extractor**: Automatically detects keywords (Python, Go, Distributed Systems, Kubernetes, AWS, etc.).
- 🤝 **Recruiter Outreach Copilot**:
  - **1-Click LinkedIn Recruiter Search**: Instantly launches pre-filtered LinkedIn searches targeting Technical Recruiters, Engineering Managers, and Talent Leads at that specific company in NYC/Boston.
  - **Personalized Cold InMail / Connection Generator**: Auto-generates a personalized outreach message with the recruiter's company, target job title, candidate elevator pitch, and a **1-click Copy to Clipboard** button.
- ⚡ **GitHub Pages Ready (Zero Server Costs)**:
  - Runs 100% client-side on GitHub Pages.
  - Scheduled twice-daily scraper via GitHub Actions (`.github/workflows/scrape_and_deploy.yml`) that auto-updates `jobs.json` and deploys.
- 📌 **Application Tracker & Saved Jobs**:
  - Save interesting roles with one click.
  - Persisted locally in `localStorage`.

---

## 🚀 Quick Start (Local Preview)

To run the site locally in 5 seconds:

```bash
# Start the local server
./serve.sh
# Or run: python3 -m http.server 8000
```

Open your browser to: **`http://localhost:8000`**

---

## 🔄 Running the Scraper Locally

If you'd like to trigger a fresh scrape manually on your machine:

```bash
# 1. Activate python virtual environment
source venv/bin/activate

# 2. Run the aggregator pipeline
python3 -m scraper.run_scraper

# 3. Sync to root
cp web/jobs.json ./jobs.json
```

The pipeline will scrape, deduplicate, parse salaries/YoE, and update `jobs.json`.

---

## 🌐 Deploying to GitHub Pages (Step-by-Step)

### 1. Initialize Git & Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit of StaffHunt job board"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

### 2. Enable GitHub Pages

1. In your GitHub repository, go to **Settings** → **Pages**.
2. Under **Build and deployment** → **Source**, select:
   - **GitHub Actions** (Recommended: the included `.github/workflows/scrape_and_deploy.yml` workflow will automatically build, scrape, and deploy).
   - *Alternatively*, select **Deploy from a branch** → Branch: `main` / Folder: `/ (root)`.
3. In **Settings** → **Actions** → **General** → **Workflow permissions**, choose **Read and write permissions** (this allows the scheduled action to commit newly scraped jobs).

Once enabled, your website will be live at:
```
https://<your-username>.github.io/<repo-name>/
```

---

## ⚙️ Customizing Your Profile & Criteria

Edit `config/profile.json` or click **Profile** directly in the web app UI:

```json
{
  "user": {
    "name": "Varun Behl",
    "target_roles": [
      "Staff Software Engineer",
      "Senior Software Engineer",
      "Lead Software Engineer",
      "Principal Software Engineer"
    ],
    "target_locations": [
      "New York, NY",
      "Boston, MA",
      "Remote"
    ],
    "min_salary": 180000,
    "outreach_template": "Hi {{recruiter_name}},\n\nI noticed {{company}} is hiring for a {{job_title}} in {{location}}..."
  }
}
```

### Adding More Companies to Scrape

To add more Greenhouse or Lever companies:
- Open `scraper/greenhouse_scraper.py` and add the company's Greenhouse board token to `DEFAULT_GREENHOUSE_BOARDS`.
- Open `scraper/lever_scraper.py` and add the company's Lever slug to `DEFAULT_LEVER_COMPANIES`.

---

## 📁 Repository Structure

```
├── index.html                   # Main frontend entrypoint (for GitHub Pages root hosting)
├── app.js                       # Client-side search, filters, modal, and drawer logic
├── style.css                    # UI theme styling & animations
├── jobs.json                    # Aggregated jobs database (synced for static hosting)
├── config/
│   └── profile.json             # Search criteria & candidate profile configuration
├── data/
│   └── jobs.json                # Master scraped output
├── scraper/
│   ├── parser.py                # Regex parser for Salary, YoE, Tech stack & Recruiter URLs
│   ├── greenhouse_scraper.py    # Direct Greenhouse ATS scraper
│   ├── lever_scraper.py         # Direct Lever ATS scraper
│   ├── linkedin_scraper.py      # LinkedIn public guest scraper
│   └── run_scraper.py           # Pipeline orchestrator & deduplicator
├── .github/
│   └── workflows/
│       └── scrape_and_deploy.yml# Twice-daily GitHub Actions cron scraper & deployment
├── test_parser.py               # Unit tests verifying extraction accuracy
├── requirements.txt             # Python dependencies
└── serve.sh                     # Quick local server launcher
```

---

## 🧪 Testing

Run automated tests to verify parsing rules:

```bash
python3 -m unittest test_parser.py
```
