<div align="center">

# 🎯 JobRadar

### Open-Source AI Job Search Aggregator, ATS Resume Tailor & Application Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](Dockerfile)
[![Playwright](https://img.shields.io/badge/Playwright-Automated-45ba4b.svg?logo=playwright&logoColor=white)](https://playwright.dev/)
[![Privacy: BYOK](https://img.shields.io/badge/Privacy-BYOK%20%7C%20Zero--Shared--Cost-success.svg)](#-privacy--multi-tenant-byok-architecture)

*Turn weeks of exhausting job hunting into minutes. Aggregate listings across top portals, calculate interview odds, tailor resumes with AI for ATS compliance, and semi-automate applications with human oversight.*

[Features](#-key-features) • [Privacy & BYOK](#-privacy--multi-tenant-byok-architecture) • [Quickstart](#-quickstart) • [Cloud Deployment](#-cloud-deployment-railway-docker-vps) • [How to Use](#-step-by-step-usage-guide) • [SEO & Hashtags](#-search-keywords--hashtags)

---

</div>

## 💡 What is JobRadar?

**JobRadar** is a local-first, privacy-respecting job search automation engine and dashboard. Instead of spending hours jumping between 10 different job boards, manually tweaking resumes, and copy-pasting answers into application forms, JobRadar does the heavy lifting:

1. **Aggregates Real-Time Listings** in parallel from LinkedIn, Naukri, Remotive, RemoteOK, Himalayas, Jobicy, We Work Remotely, Arbeitnow, and The Muse.
2. **Scores Every Role** against your actual resume skills, years of experience, and role seniority—giving you a transparent **Match Score** and **Interview Probability Index**.
3. **AI Resume Tailoring**: Uses state-of-the-art LLMs (Claude 3.5 Sonnet, GPT-4o, or any custom OpenAI-compatible endpoint) to rewrite bullet points for exact ATS keywords while preserving your original DOCX formatting.
4. **100-Point ATS Validator**: Performs structural audits (tables, columns, font sizes, heading syntax) and keyword gap analysis so your resume never gets lost in recruiter algorithms.
5. **Semi-Automated Apply Assistant**: Auto-fills job applications (Greenhouse, Lever, Ashby, Workday, LinkedIn Easy Apply, Naukri) and drafts AI answers for screening questions—keeping you in control for the final submission.

---

## 🔒 Privacy & Multi-Tenant BYOK Architecture

JobRadar is engineered with a **Zero-Shared-Cost / Bring-Your-Own-Key (BYOK)** security model:

- **Zero Server-Side Key Storage**: Your AI provider keys (Anthropic, OpenAI, or Codecraft/custom proxies) are stored exclusively in your browser’s local storage (`localStorage`). They are passed per-request over HTTPS and never written to server configuration files or databases.
- **Shared Deployment Safe**: You can host a single JobRadar instance on Railway, Render, or a VPS and share the public link with family, friends, or a community. Each user supplies their own API key and consumes their own token quota. **The server owner incurs $0 LLM costs.**
- **Per-User Workspace Isolation**: Candidate profiles, uploaded resumes, ATS scores, and tracked job statuses (`saved`, `applied`, `hidden`) are partitioned per browser using a local UUID workspace header (`X-User-Id`). Users accessing the same public link never see each other's data.
- **Local-First**: When running locally, all databases and files reside completely on your own machine in the `data/` folder.

---

## 🌟 Key Features

| Category | Highlights |
|---|---|
| 🔍 **Multi-Portal Scraping** | Parallel live search across **LinkedIn**, **Naukri**, **Remotive**, **RemoteOK**, **Himalayas**, **Jobicy**, **We Work Remotely**, **Arbeitnow**, and **The Muse**. |
| 📊 **Intelligent Matching** | Weighted calculation: **55% skills**, **30% experience**, **15% title similarity**. Considers posting freshness and applicant competition to predict your **Interview Chance**. |
| 🤖 **AI Resume Tailoring** | Supports **Claude 3.5 Sonnet**, **OpenAI GPT-4o**, and **Codecraft / OpenAI-compatible LLMs** (vLLM, Ollama, DeepSeek, LocalAI) with live dynamic model discovery. |
| 📝 **DOCX Preservation** | Tailors your existing Word document **in-place** (retaining your fonts, margins, headers, and aesthetic style) while simultaneously producing an ATS-optimized clean copy. |
| 🛡️ **ATS Compliance Score** | 12-point layout and structural check + detailed missing keyword report. |
| ⚡ **Playwright Apply Assistant** | Detects ATS portals (Greenhouse, Lever, Ashby, Workday, SmartRecruiters, LinkedIn Easy Apply, Naukri) and auto-populates personal details, resumes, and screening answers. |
| 👤 **Human-in-the-Loop** | Never blindly applies without your consent. You always inspect the pre-filled form and click the final submit button. |

---

## 🚀 Quickstart

### Option 1: Windows (1-Click Launch)

No command line required.

1. Install [Python 3.10+](https://www.python.org/downloads/) (Make sure to tick **"Add python.exe to PATH"** during installation).
2. [Download or clone](https://github.com/Vijayroyal358/JobRadar.git) this repository:
   ```cmd
   git clone https://github.com/Vijayroyal358/JobRadar.git
   cd JobRadar
   ```
3. Double-click **`start.bat`**.
   - The launcher will automatically build the virtual environment, install requirements, and open your browser at `http://127.0.0.1:8765`.
   - A desktop shortcut will also be created for future launches.

---

### Option 2: macOS / Linux

1. Clone repository:
   ```bash
   git clone https://github.com/Vijayroyal358/JobRadar.git
   cd JobRadar
   ```
2. Make script executable and launch:
   ```bash
   chmod +x start.sh
   ./start.sh
   ```
   *(Or run directly via `python3 run.py`)*

---

### Option 3: Docker & Docker Compose

Deploy locally in an isolated container with Playwright pre-installed:

```bash
# Clone and enter repo
git clone https://github.com/Vijayroyal358/JobRadar.git
cd JobRadar

# Launch container in background
docker compose up -d
```
Open **`http://localhost:8765`** in your browser. All your data and resumes are persisted in `./data`.

---

## ☁️ Cloud Deployment (Railway, Docker, VPS)

JobRadar is containerized and cloud-ready for instant deployment on services like **Railway.app**, **Render**, or any Linux VPS.

### Deploying on Railway:

1. Push this repository to your GitHub account.
2. Sign in to [Railway.app](https://railway.app/) and click **New Project** &rarr; **Deploy from GitHub repo**.
3. Select your **JobRadar** repository.
4. Railway will automatically detect the `Dockerfile` and build the container using Jammy + Playwright.
5. In your Railway service settings:
   - Under **Networking**, click **Generate Domain** (gives you a public `https://....up.railway.app` URL).
   - Ensure the port is set to `8765` (Railway binds `$PORT` automatically).
6. **You're live!** Share the URL with anyone—each visitor connects with their own private BYOK session.

---

## 📖 Step-by-Step Usage Guide

### 1. Set Up Your AI Credentials (BYOK)
- Click **AI settings** in the sidebar.
- Choose your provider:
  - **Claude (Anthropic)**: Enter `sk-ant-...`
  - **OpenAI**: Enter `sk-...`
  - **Codecraft / Compatible Endpoint**: Enter your API base URL (e.g. `https://api.yourproxy.com/v1` or local Ollama) and click to dynamically select available models.
- Click **Test connection** &rarr; **Save AI settings**. Keys remain safely stored in your browser's local storage.

### 2. Upload Your Resume
- Drag & drop your resume (**PDF**, **DOCX**, or **TXT**) into the upload box.
- JobRadar parses your experience, skills, and target roles automatically.
- Adjust any fields in the sidebar and click **Save and re-score**.

### 3. Find Jobs Across the Web
- Click **Find jobs**.
- JobRadar queries enabled job portals in parallel. Results stream into your dashboard ranked by **Match Score** and **Interview Chance**.
- Filter by location, remote-only, minimum score, or specific keywords.

### 4. Tailor Resume for Any Job
- Click **Tailor resume** on any job card.
- JobRadar's AI compares the job description against your resume, weaves in essential keywords, and formats bullet points using strong action verbs.
- Within 30 seconds, download:
  - **Your formatted DOCX** (original visual template preserved).
  - **Clean ATS-Safe DOCX** (single column, ATS-standard headers, zero parsing errors).
  - An **ATS Score out of 100** with a keyword gap analysis.

### 5. Fast-Track Applications
- Check the jobs you want to target and open **Apply assistant**.
- JobRadar opens a secure browser window, navigates to the application page, and automatically fills in your standard details (contact info, experience, portfolio links).
- When a portal presents custom screening questions, the AI drafts tailored answers from your resume.
- Review everything on screen and click submit yourself.

---

## 📁 Repository Structure

```plaintext
JobRadar/
├── app/
│   ├── ai.py                  # Anthropic, OpenAI & Codecraft LLM handlers
│   ├── apply.py               # Playwright-based application assistant
│   ├── config.py              # Application settings & environment loaders
│   ├── database.py            # SQLite schema (multi-user workspace partitioned)
│   ├── matcher.py             # Match score & interview probability algorithm
│   ├── resume_parser.py       # PDF/DOCX/TXT text & skill extraction
│   ├── tailor.py              # ATS resume rewriting & structural compliance
│   ├── routes/                # FastAPI endpoint controllers
│   └── scrapers/              # Scraping modules (LinkedIn, Naukri, Remote APIs)
├── static/                    # Frontend dashboard (HTML5, modern CSS, vanilla JS)
├── tests/                     # Unit and integration test suite
├── Dockerfile                 # Playwright Jammy production container
├── docker-compose.yml         # 1-command container deployment
├── requirements.txt           # Python dependencies
├── run.py                     # Entry point & browser launcher
├── start.bat                  # Windows 1-click bootstrapper
└── start.sh                   # macOS/Linux bootstrapper
```

---

## 🔒 Security & Privacy Guarantee

- **No Hardcoded Keys**: This codebase contains zero hardcoded API keys, tokens, or credentials.
- **Client-Side Secret Storage**: All user credentials remain in the client's browser storage.
- **No Third-Party Telemetry**: JobRadar contains zero tracking scripts, analytics beacons, or third-party tracking pixels.

---

## 🏷️ Search Keywords & Hashtags

Help others discover this project! If you are searching on Google, GitHub, or social platforms, use these keywords and hashtags:

### Google & GitHub Search Queries
> `ai job search aggregator`, `automated job application assistant`, `ats resume tailor open source`, `linkedin job scraper python`, `naukri job scraper playwright`, `ai resume builder claude openai`, `self hosted job application bot`, `free ats resume optimizer`, `job board aggregator python`, `byok ai resume tailor`

### GitHub Topic Tags
`ai` • `job-search` • `job-scraper` • `resume-builder` • `ats-optimizer` • `resume-tailoring` • `linkedin-scraper` • `naukri-scraper` • `playwright` • `fastapi` • `python` • `claude-ai` • `openai` • `automation` • `byok`

### Social Media Hashtags
`#JobSearch` `#OpenSource` `#AIResume` `#ATS` `#JobHunt` `#Python` `#FastAPI` `#Playwright` `#MachineLearning` `#CareerTech` `#ArtificialIntelligence` `#ResumeOptimization` `#DevCommunity`

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <b>Star ⭐ this repository if JobRadar helps you land your next interview!</b>
</div>
