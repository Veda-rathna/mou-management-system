# MOU Management System

### AI-Powered Institutional MOU Lifecycle Management & Contract Intelligence

An enterprise-ready, zero-cost web application designed for universities, colleges, and industrial partners to streamline the entire lifecycle of Memoranda of Understanding (MOUs).

---

## 🌟 Key Features

1. **Two-Way Collaboration Flow**:
   * **College Initiated**: The institution can create an MOU record, upload a draft PDF, and issue a time-limited secure link to the external partner.
   * **Partner Proposing**: The college can issue an empty collaboration link allowing the external organization to upload their proposed draft MOU directly.
2. **AI Contract Intelligence & Institutional Guardrails**:
   * Evaluates agreements against critical institutional safety rules:
     * **Intellectual Property (IP)**: Protects student and faculty research inventions from unilateral assignment.
     * **Liability & Indemnification**: Flags uncapped indemnities and broad indirect damages.
     * **Governing Law & Jurisdiction**: Alerts if dispute resolution is seated in foreign or non-local courts.
     * **Student Privacy**: Restricts transfer of student records and PII.
     * **Hidden Costs**: Flags undefined financial obligations.
   * **Hybrid Engine**: Uses Google Gemini 1.5 Flash API (100% Free Tier, 1,500 calls/day) with instant fallback to a deterministic offline heuristic engine.
3. **Split-Screen Reviewer Studio**:
   * Left side: In-browser PDF preview.
   * Right side: AI verdict, risk score (0–10), actionable redlines, and categorized clause breakdown.
4. **HTML5 Canvas Digital Signature Pad**:
   * Responsive touch/mouse signature capture for both external partner and authorized internal college signatories.
5. **Printable Executive Summary**:
   * 1-click board/dean-ready summary report formatted for printing or PDF export.
6. **Automated Expiry Radar**:
   * Background scan classifying agreements into 0–30 days (Urgent), 31–60 days (Warning), and 61–90 days (Advance Notice), with automated status updates.
7. **Immutable Audit Trail**:
   * Comprehensive historical logging of all user and partner actions with timestamps and client IP tracking.

---

## 🛠️ 100% Free Tech Stack

| Layer | Service / Library | Free Tier Details |
| :--- | :--- | :--- |
| **Backend** | Python 3.11 + Django 5.x | Open-source, batteries-included |
| **Frontend** | Bootstrap 5.3 + Custom CSS + HTML5 Canvas | Lightweight, responsive, zero-node bloat |
| **Database** | SQLite (Local) / Neon.tech (Production) | Neon offers 0.5 GB serverless PostgreSQL free forever |
| **AI Engine** | Google Gemini 1.5 Flash API + Offline Rule Engine | Free 1,500 reqs/day via Google AI Studio |
| **Hosting** | Render.com or Hugging Face Spaces | Render: 750 free hrs/mo; HF Spaces: 16 GB RAM free |
| **Cron & Alerts** | GitHub Actions Workflow | Free automated daily cron for expiry checking |

---

## 🚀 Quickstart (Local Development)

### 1. Clone & Set Up Virtual Environment

```bash
git clone <your-repo-url>
cd MOU-Management

# Create and activate virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize Database & Seed Demo Data

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_demo_data
```

This automatically creates:
* **Admin Account**: Username: `admin`, Password: `admin123`
* **Sample Agreement**: Pre-loaded with realistic research clauses, AI analysis, risk score, and an active partner link.

### 4. Run Development Server

```bash
python manage.py runserver
```

Open your browser at:
* **Internal Dashboard**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Admin Portal**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 🌐 Deploying 100% For Free

### Option A: Render.com (Recommended)

1. Push your repository to **GitHub**.
2. Sign in to [Render.com](https://render.com) with GitHub.
3. Click **New +** &rarr; **Blueprint** and select your repository (it will auto-detect `render.yaml`).
4. Set your Environment Variables in Render:
   * `DATABASE_URL`: Your free Neon PostgreSQL connection string (e.g. `postgres://user:pass@ep-xyz.neon.tech/neondb?sslmode=require`).
   * `GEMINI_API_KEY`: Your free Gemini API key from [Google AI Studio](https://aistudio.google.com).
5. Click **Apply** to deploy!

### Option B: Hugging Face Spaces (Docker 16 GB RAM Free)

1. Create a new Space on [Hugging Face Spaces](https://huggingface.co/spaces) selecting **Docker** SDK.
2. Push this repo. The included `Dockerfile` will automatically build, run migrations, seed data, and launch Gunicorn on port `7860`.

---

## 🧪 Running Automated Tests

Run the included test suite covering model transitions, token expiration, AI analysis, and expiry monitoring:

```bash
python manage.py test mous
```

---

## 📋 Security & Compliance

* **CSRF Protection**: Native Django CSRF tokens on all mutation endpoints.
* **Tokenized Access**: Partner collaboration links use cryptographically secure UUID4 tokens with expiration and click limits.
* **Audit Trail**: Every action logs timestamp, actor identity, and client IP address.
* **Zero-Retention Fallback**: The offline rule engine runs fully local without transmitting document text externally.
