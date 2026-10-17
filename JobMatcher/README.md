# JobRadar

A local job search dashboard. It reads your resume, searches several job portals, and shows only the jobs that fit your skills and experience, ranked by how likely you are to get an interview.

Everything runs on your own machine. Your resume and job data stay in the `data` folder.

## Start

Double-click **start.bat**, or the **JobRadar** shortcut on your desktop.

The first start takes about a minute because it installs what it needs. Later starts are instant. Your browser opens at http://127.0.0.1:8765. Keep the black window open while you use it, and close it to stop.

You only need Python 3.10 or newer, plus Chrome or Edge for Naukri.

## Move to another computer

1. On the new computer, install Python 3.10 or newer from https://www.python.org/downloads/. Tick **Add python.exe to PATH** during setup. Chrome or Edge is needed for Naukri.
2. Copy the `JobMatcher` folder, or `JobRadar.zip` unzipped. You can leave out `.venv`, which is rebuilt automatically and is large. If you copy it anyway, the launcher notices it does not work on the new computer and rebuilds it.
3. Double-click `start.bat`. The first start installs everything and adds a desktop shortcut.

To keep your profile, saved and applied jobs, also copy the `data` folder. Copy it while JobRadar is closed. Leave it out to start fresh.

On macOS or Linux, run `./start.sh` instead of `start.bat`.

## Use

1. Drop your resume (PDF, DOCX or TXT) on the upload box.
2. Check what was read: current position, years of experience, skills and target roles. Fix anything that is wrong, then click **Save and re-score**.
3. Click **Find jobs**. All portals are searched in parallel and results appear as they arrive.
4. Use **Show JD** to read the job description and see why it matches. Use **Apply** to open the application page.
5. Use Save, Mark applied and Hide to track your progress. Export the current list with **CSV**.

## Tailor your resume to a job (AI)

1. Open **AI settings** at the top of the sidebar. Pick a provider: **Claude** (Anthropic), **OpenAI** or **Codecraft** (any OpenAI-compatible endpoint, which also needs a base URL and model name).
2. Paste your API key, keep or change the model, click **Test connection**, then **Save AI settings**. Keys are stored only in the local `data` folder.
3. On any job, click **Tailor resume** (on the card or inside the JD drawer). After 20 to 60 seconds you get two downloads, an ATS score, and a line-by-line list of what changed.

### ATS friendliness

Applicant tracking systems rank resumes by exact keyword matches and only read text they can parse. Every tailored resume therefore gets:

- **ATS rules in the rewrite.** The AI must use the job's exact wording for skills and tools, spell out acronyms once ("Amazon Web Services (AWS)"), lead bullets with action verbs, avoid symbols and first-person pronouns, and never stuff keywords.
- **An ATS-safe copy.** Next to the file in your own layout you get a single-column DOCX in Calibri with standard headings (Professional Summary, Work Experience, Education, Skills), real bullets, contact details in the body, and no tables, text boxes, columns or images. Use this one for online applications and keep the formatted one for people.
- **An ATS check with a score out of 100.** Twelve structural checks (columns, tables, text boxes, images, contact details in the body, standard headings, fonts, font size, special characters, length, employment dates, file type) plus keyword coverage: which of the job's key terms appear in the resume and which do not. Missing terms are listed so you can add them only if you genuinely have that experience.

PDF resumes are rebuilt directly in the ATS-safe layout. The score is a strong proxy, but no tool can guarantee a given employer's system, so also paste the job's must-have terms into your own review.

How it works: the job description and your resume text are sent to the provider you chose. The AI only rewrites the summary, skills and experience bullets, and is told never to invent experience or touch your name, contact details, dates, education or headings. Those lines are also protected on this side, so even a bad model answer cannot change them.

- **DOCX resumes** are edited in place. Fonts, styles, bullets and tables stay exactly as they were.
- **PDF resumes** cannot be edited in place, so the tailored version is rebuilt as a DOCX that follows the same line order. Upload a DOCX to keep your exact formatting.
- **TXT resumes** are edited line by line.

Tailored files are saved under `data/tailored`, the ATS-safe copy with an `(ATS)` suffix. Every version stays listed in the job drawer until you delete it.

## Apply assistant

Select jobs with the checkbox on each card (or use **Apply to all shown**) and click **Apply to selected**. A Chrome or Edge window opens with its own profile, so once you log in to LinkedIn, Naukri or a company portal the session is kept under `data/apply/browser`.

For each job the assistant:

1. Opens the application page, follows "Apply" buttons, and detects the portal: LinkedIn Easy Apply, Naukri, Greenhouse, Lever, Ashby, SmartRecruiters, Workday, or a generic company form.
2. Fills every field it recognises from your **Apply** profile in the sidebar: name, contact details, links, location, experience, notice period, salary, work authorization, relocation, cover letter, and "prefer not to say" for diversity questions unless you set them.
3. Attaches the ATS-safe tailored resume for that job if you made one, otherwise your uploaded resume.
4. Answers screening questions from your **Saved answers**. Unknown questions go to the AI, which drafts an answer from your resume; drafts are shown in the Apply assistant panel where you can edit them and push them into the form.
5. Steps through multi-page forms (LinkedIn's Next and Review buttons, Workday's Save and Continue).
6. Stops at the final step. **You always click Submit in the browser.** When the portal confirms, or you click **I submitted it**, the job is marked Applied and the answers you approved are remembered.

If a portal asks you to log in or shows a captcha, the panel says so and waits for you. Naukri has no form before its one-click Apply, so there the assistant waits for you to click Apply and then answers the recruiter chatbot's questions.

Limits worth knowing: LinkedIn's terms prohibit automation, which is why the assistant never submits there on its own. Workday needs an account per company. Forms with unusual widgets may leave a field empty; the panel lists what was filled so you can check the rest in the browser.

## Sources

| Portal | Coverage | How |
|---|---|---|
| LinkedIn | Your locations, plus remote | Public job search, with full descriptions and applicant counts |
| Naukri | India | Your installed Chrome or Edge, run in the background |
| Remotive, RemoteOK, Himalayas, Jobicy, We Work Remotely | Remote | Public APIs and feeds |
| Arbeitnow | Europe and remote | Public API |
| The Muse | US and remote | Public API |

Turn individual sources on or off under **Job sources** in the profile panel. The sidebar has three panels: **Profile** (resume, skills, roles, locations, sources, advanced), **AI settings** (API keys and model) and **Apply** (application details, saved answers, portal logins).

## How jobs are scored

- **Match score** is 55% skills, 30% experience and 15% role similarity.
  - Skills found in the job title count three times, explicit skill tags count twice, and skills in the description count once.
  - Role similarity carries little weight because titles vary between companies.
- **Interview chance** is 75% match score, 13% freshness and 12% competition. Freshness is how recently the job was posted. Competition is based on the applicant count where the portal shows it.
- A job is **excluded** when it needs more than 2 years beyond your experience, or when you are far beyond its range. It is also excluded when no skills overlap or when it is limited to a country you cannot work from. Turn on **Show excluded** to see these jobs.
- **High** chance is 68 or more, **Medium** is 50 to 67, and **Low** is below 50.

## Settings worth knowing

- **Target roles** are the search keywords. Add the variations companies use, for example "Backend Developer" and "Python Engineer".
- **Search locations** are used by LinkedIn and Naukri. Add cities such as Bengaluru and Hyderabad.
- **Advanced** controls how deep each search goes. More pages give more jobs but take longer.
- If Naukri reports a captcha, turn off **Run Naukri browser hidden** and search again. A visible browser window passes the check more reliably.

## Files

```
start.bat            launcher (Windows)
run.py               sets up .venv, starts the server, opens the browser
app/                 server: resume parser, skill dictionary, matcher, scrapers, AI providers, resume tailoring, apply assistant, API
static/              dashboard (HTML, CSS, JS)
data/                your database, uploaded resume, API keys, tailored resumes and the apply browser profile (created on first run)
```

To add a portal, create a scraper in `app/scrapers/` and register it in `app/scrapers/__init__.py`.
