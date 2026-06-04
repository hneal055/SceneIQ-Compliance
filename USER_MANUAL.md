# SceneIQ — Tax Incentive Compliance Platform
## User Manual v3.0

---

## Table of Contents

1. [Platform Overview](#1-platform-overview)
2. [Getting Started](#2-getting-started)
3. [Dashboard](#3-dashboard)
4. [Productions](#4-productions)
5. [Calculator & Scenario Tools](#5-calculator--scenario-tools)
6. [Jurisdictions](#6-jurisdictions)
7. [Local Rules & Rule Review](#7-local-rules--rule-review)
8. [AI Advisor](#8-ai-advisor)
9. [Budget Builder](#9-budget-builder)
10. [Reports & Exports](#10-reports--exports)
11. [Monitoring System](#11-monitoring-system)
12. [Incentive Maximizer](#12-incentive-maximizer)
13. [Admin & User Management](#13-admin--user-management)
14. [Notifications & Preferences](#14-notifications--preferences)
15. [Command-Line Tools](#15-command-line-tools)
16. [API Reference](#16-api-reference)
17. [Database Models](#17-database-models)
18. [Deployment & Operations](#18-deployment--operations)
19. [Environment Variables](#19-environment-variables)
20. [Troubleshooting](#20-troubleshooting)

---

## 1. Platform Overview

SceneIQ is a tax incentive compliance platform built for film and TV production professionals. It combines jurisdiction research, incentive calculation, compliance tracking, AI advisory, and script-to-budget intelligence in one unified system.

### Applications

| App | URL Path | Description |
|---|---|---|
| **Incentives & Compliance** | `/` | Jurisdiction database, compliance tracking, calculator, maximizer, AI advisor |
| **Budget Builder** | `/budget` | Script-to-budget pipeline with tax credit optimization and risk scoring |

### Core Capabilities

| Capability | Description |
|---|---|
| **Productions** | Track all productions with budget, expenses, status, and jurisdiction |
| **Calculator** | Estimate and compare tax credits across jurisdictions |
| **Scenario Analysis** | Model what-if spending scenarios per production |
| **Compliance Tracking** | Manage checklist items with due dates and status |
| **Jurisdiction Database** | 50+ jurisdictions with incentive rules and live feed monitoring |
| **Local Rules** | Sub-jurisdiction and county/city rules extracted from government feeds |
| **Rule Review** | Human-in-the-loop approval of AI-extracted rules |
| **AI Advisor** | Claude-powered chat for incentive questions |
| **Maximizer** | Stack-optimize incentives across jurisdiction layers by location |
| **Monitoring** | Automated change detection on government feeds |
| **Budget Builder** | Screenplay import → scene analysis → budget estimate → tax credit optimization |
| **Exports** | PDF and Excel reports for all major views |

### Tech Stack

| Layer | Technology |
|---|---|
| **Incentives Frontend** | React 19 + TypeScript + Vite + Tailwind CSS v4 |
| **Budget Frontend** | React 19 + TypeScript + Vite + Tailwind CSS v4 |
| **Incentives API** | FastAPI + Python 3.12 + Prisma ORM |
| **Budget API** | FastAPI + Python 3.12 + Prisma ORM |
| **Pipeline** | Screenplay Engine, Emotion Rules, Risk Service, Pilotforge Adapter, Orchestrator |
| **Database** | PostgreSQL (shared) |
| **Graph DB** | Neo4j 5 (pipeline scene graph) |
| **AI** | Anthropic Claude (Sonnet 4.6) — rule extraction, advisory, budget analysis |
| **Reverse Proxy** | nginx |
| **Background Jobs** | APScheduler (feed ingestion every 4 hours) |

---

## 2. Getting Started

### Default Credentials

| Field | Value |
|---|---|
| Email | `admin@sceneiq.com` |
| Password | `sceneiq2024` |

> Change these immediately after first login via Settings → Account.

### Local URLs

| Service | URL | Notes |
|---|---|---|
| **Incentives & Compliance** | `http://localhost:8080` | Main app via nginx reverse proxy |
| **Budget Builder** | `http://localhost:8080/budget` | Budget pipeline app |
| **Incentives API (via proxy)** | `http://localhost:8080/api/0.1.0/` | Proxied through nginx |
| **Incentives API (direct)** | `http://localhost:8001/api/0.1.0/` | Direct to container |
| **Budget API (direct)** | `http://localhost:8002/api/0.1.0/` | Direct to container |
| **API Docs — Incentives** | `http://localhost:8001/docs` | Swagger UI |
| **API Docs — Budget** | `http://localhost:8002/docs` | Swagger UI |
| **Pipeline Orchestrator** | `http://localhost:8080/pipeline/` | Via nginx proxy |
| **Neo4j Browser** | `http://localhost:7474` | Graph database UI |

> **Always use port 8080** (nginx) for the web UI. Direct container ports (8001, 8002) are for API testing only.

### Docker Services

| Compose Service | Container | Port | Role |
|---|---|---|---|
| `incentives-api` | `sceneiq-incentives-api` | 8001→8000 | Incentives/compliance FastAPI backend |
| `incentives-ui` | `sceneiq-incentives-ui` | (internal) | Incentives React frontend |
| `budget-api` | `sceneiq-budget-api` | 8002→8000 | Budget Builder FastAPI backend |
| `budget-ui` | `sceneiq-budget-ui` | (internal) | Budget Builder React frontend |
| `nginx` | `sceneiq-nginx` | 8080→80 | Reverse proxy for all services |
| `postgres` | `sceneiq-db` | 5435→5432 | PostgreSQL (shared database) |
| `neo4j` | `sceneiq-neo4j` | 7474, 7687 | Graph DB for scene analysis |
| `screenplay-engine` | `sceneiq-screenplay-engine` | 8010→8000 | Scene parsing and budget calculation |
| `emotion-rules` | `sceneiq-emotion-rules` | 8011→8000 | Emotion-based budget adjustments |
| `risk-service` | `sceneiq-risk-service` | 8012→8000 | Production risk scoring |
| `pilotforge-adapter` | `sceneiq-pilotforge-adapter` | 8013→8000 | Incentives API adapter for pipeline |
| `pipeline-orchestrator` | `sceneiq-pipeline-orchestrator` | 8014→8000 | Pipeline coordination service |

### Starting the Platform

```bash
cd c:/Projects/SceneIQ
docker compose up -d
```

### Stopping

```bash
docker compose down
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f incentives-api
docker compose logs -f budget-api
docker compose logs -f pipeline-orchestrator
```

### Fresh Database Recovery Order

If the database is empty or reset:

```bash
# 1. Run migrations
docker exec sceneiq-incentives-api python -m prisma migrate deploy

# 2. Seed jurisdictions
docker cp scripts/seed_jurisdictions.py sceneiq-incentives-api:/app/scripts/seed_jurisdictions.py
docker exec sceneiq-incentives-api python scripts/seed_jurisdictions.py

# 3. Seed incentive rules
docker cp scripts/seed_incentive_rules.py sceneiq-incentives-api:/app/scripts/seed_incentive_rules.py
docker exec sceneiq-incentives-api python scripts/seed_incentive_rules.py

# 4. Seed sub-jurisdictions and more rules
docker exec sceneiq-incentives-api python scripts/seed_more_jurisdictions.py
docker exec sceneiq-incentives-api python scripts/seed_more_rules.py

# 5. Seed maximizer test data (optional)
python scripts/seed_maximizer_test.py
```

---

## 3. Dashboard

**Navigation:** Click the SceneIQ logo or "Dashboard" in the sidebar.

The dashboard provides an executive overview of all productions and incentive performance.

### Metric Cards

| Card | What It Shows |
|---|---|
| **Total Budget Volume** | Sum of all production budgets across the portfolio |
| **Estimated Tax Credits** | Projected incentive value across all productions |
| **Active Projects** | Productions in planning, pre-production, or production status |
| **Alerts** | Compliance items overdue or jurisdictions with feed changes |

### Top Productions Chart

A horizontal bar chart showing the top 5 productions by budget, comparing **budgeted** vs. **actual** qualified spend. Use this to spot productions that are under- or over-spending their qualifying budget.

### Reading the Dashboard

- **Green values** — on track or ahead of targets
- **Amber values** — attention needed (compliance approaching due date, minor budget variance)
- **Red values** — action required (overdue compliance, significant budget shortfall)

---

## 4. Productions

**Navigation:** Sidebar → Productions

### Production List

The list shows all productions with:
- Title and production company
- Status badge (planning / pre-production / production / post-production / completed)
- Production type (feature, TV series, commercial, documentary)
- Home jurisdiction
- Total budget and qualifying spend

### Filtering & Search

| Filter | How |
|---|---|
| Search | Type in the search bar — matches title or production company |
| Status | Click a status badge in the filter bar |
| Production type | Dropdown in the filter bar |

### Creating a Production

1. Click **+ New Production**
2. Fill in the required fields:

| Field | Description |
|---|---|
| **Title** | Production working title |
| **Production Type** | Feature / TV Series / Commercial / Documentary |
| **Production Company** | Legal entity name |
| **Jurisdiction** | Primary filming jurisdiction (state/country) |
| **Total Budget** | Full production budget in USD |
| **Qualifying Budget** | Portion eligible for incentives |
| **Start Date** | Principal photography start |
| **End Date** | Wrap date (optional) |
| **Status** | Current phase |
| **Contact** | Production contact name/email |

3. Click **Create Production**

### Production Detail

Click any production to open the detail view with these tabs:

#### Overview Tab
Full metadata for the production. Click any field to edit inline.

#### Expenses Tab
Track individual expense line items.

**Adding an expense:**
1. Click **+ Add Expense**
2. Fill in category, description, amount, date, vendor
3. Toggle **Is Qualifying** to mark whether the expense counts toward incentives
4. Click **Save**

**Expense categories:** Labor, Equipment, Location, Post-Production, Travel, Legal, Marketing, Other

**Auto-generate sample expenses:** Click **Generate Sample Expenses** to populate test data for a new production.

#### Compliance Tab
Checklist of compliance requirements for this production's jurisdiction.

**Status values:**

| Status | Meaning |
|---|---|
| `pending` | Not yet done |
| `complete` | Verified and done |
| `waived` | Exempted from this requirement |
| `na` | Not applicable to this production |

**Auto-generate checklist:** Click **Generate Checklist** — creates standard compliance items for the selected jurisdiction.

#### Scenarios Tab
See [Section 5](#5-calculator--scenario-tools) for full scenario documentation.

### Editing a Production

All fields in the Overview tab are inline-editable. Click the field, make the change, and click **Save** or press Enter.

### Deleting a Production

Click the **trash icon** on the production list row or the **Delete** button in the production detail. A confirmation dialog will appear — this action is permanent.

---

## 5. Calculator & Scenario Tools

**Navigation:** Sidebar → Calculator

The Calculator has six calculation modes accessible via tabs.

---

### Mode 1: Quick Calculate

**Use for:** Fast estimate of the incentive for a production in a specific jurisdiction.

**Inputs:**
- Select production
- Select jurisdiction

**Output:**
- Estimated credit amount
- Effective rate
- Rule that was applied
- Minimum spend requirement check

---

### Mode 2: Simple Calculate

**Use for:** Apply a single known incentive rule to a qualified spend amount.

**Inputs:**
- Production
- Jurisdiction
- Qualified spend amount

**Output:**
- Credit amount (percentage × spend)
- Credit type (refundable / transferable / non-refundable)
- Eligibility requirements

---

### Mode 3: Compare

**Use for:** Side-by-side comparison of the same production across multiple jurisdictions.

**Inputs:**
- Production
- Select 2–6 jurisdictions to compare

**Output:**
- Table showing incentive value, effective rate, and credit type for each jurisdiction
- Ranked from highest to lowest incentive value
- Download as PDF or Excel

---

### Mode 4: Compliance Check

**Use for:** Verify whether a production's expense breakdown meets a jurisdiction's eligibility rules.

**Inputs:**
- Production
- Jurisdiction
- Expense breakdown by category

**Output:**
- Per-category eligibility (qualified / excluded / partially qualified)
- Total qualified spend
- Estimated credit based on qualified amounts
- Warning flags for categories at or near caps

---

### Mode 5: Scenario Analysis

**Use for:** Model multiple budget scenarios for a single production.

**Inputs:**
- Production
- 1–6 spending scenarios (vary total budget, qualifying %, category breakdowns)

**Output:**
- Incentive value for each scenario
- Chart showing scenario comparison
- Best-case and worst-case projections

---

### Mode 6: Date-Based Rules

**Use for:** Check which incentive rules apply on a specific date (useful for productions that span rule change dates).

**Inputs:**
- Jurisdiction
- Date

**Output:**
- All active rules on that date
- Rules that expired before or became effective after that date
- Credit rates and eligibility as of that date

---

### Scenario Calculator (Stacking Engine)

**Navigation:** Sidebar → Scenario Calculator

A dedicated multi-jurisdiction scenario tool powered by the stacking engine.

**How to use:**
1. Click **+ Add Scenario** — up to 6 scenarios
2. For each scenario, select:
   - Jurisdiction
   - Qualified Spend
   - Local Hire % (optional — unlocks local hire bonuses)
   - Shooting Days (optional — some jurisdictions have per-day thresholds)
   - Production Start Date (optional — for date-sensitive rule matching)
3. Click **Compare Stacks**

**Results show:**
- **Best Stack** badge on the highest-value jurisdiction
- Layer breakdown (state incentive + local incentive + any bonuses)
- Effective rate and total incentive per jurisdiction
- Warnings (e.g., annual cap exhaustion, minimum spend not met)
- Stacking conflicts (where rules cannot stack)

---

## 6. Jurisdictions

**Navigation:** Sidebar → Jurisdictions

Browse and manage the full jurisdiction database.

### Jurisdiction List

| Column | Description |
|---|---|
| Name | Full jurisdiction name |
| Code | Short identifier (e.g., `NY`, `CA`, `NY-ERIE`) |
| Type | state / county / city / country / province |
| Country | ISO country code |
| Rules | Count of active incentive rules |
| Feed Status | Last checked timestamp + change indicator |

### Filtering

- **Search:** Name or code
- **Type filter:** state, county, city, country, province
- **Active only:** Toggle to hide inactive jurisdictions

### Jurisdiction Detail

Click any row to open the detail modal:

| Tab | Content |
|---|---|
| **Overview** | Description, website, currency, treaty partners |
| **Incentive Rules** | All active rules with rates, caps, and eligibility |
| **Sub-Jurisdictions** | Counties and cities under this jurisdiction |
| **Monitoring** | Feed URL, last checked, last hash, manual refresh |

### Monitoring Feed Controls

In the **Monitoring** tab of a jurisdiction detail:
- **Feed URL** — the government page being watched
- **Last Checked** — timestamp of most recent fetch
- **Refresh Now** — trigger an immediate feed fetch (runs Claude extraction if content changed)

> Changes detected by the monitor create **Pending Rules** — see [Section 7](#7-local-rules--rule-review).

---

## 7. Local Rules & Rule Review

### Local Rules

**Navigation:** Sidebar → Local Rules

Local rules are jurisdiction-specific rules stored at the county, city, or sub-jurisdiction level. They supplement the main state-level IncentiveRules.

#### Local Rules List

Each row shows:
- Rule name and code
- Jurisdiction
- Category (film_incentive, local_incentive, permit_fee, etc.)
- Rule type (tax_credit, rebate, fee, restriction)
- Amount (USD) or Percentage
- Effective and expiration dates
- Status (active / inactive)

#### Stats Bar

At the top of the page:
- **Total Rules** — All local rules in the system
- **Active** — Currently in effect
- **Credits** — Rules that provide incentive value
- **Fees** — Rules that add cost (permit fees, etc.)

#### Filtering

| Filter | Options |
|---|---|
| Search | Rule name or code |
| Jurisdiction | Dropdown of all jurisdictions |
| Rule Type | credit / rebate / fee / restriction / all |
| Status | Active only / All |

#### Creating a Local Rule Manually

1. Click **+ Add Rule**
2. Fill in:

| Field | Description |
|---|---|
| **Jurisdiction** | Select from dropdown |
| **Name** | Display name for the rule |
| **Code** | Unique identifier (e.g., `NY-ERIE-FILM-FEE`) |
| **Category** | film_incentive / local_incentive / permit_fee / other |
| **Rule Type** | tax_credit / rebate / fee / restriction / exemption |
| **Amount** | Fixed USD value (use for flat fees) |
| **Percentage** | Rate (use for percentage-based credits) |
| **Description** | Full description |
| **Requirements** | Eligibility conditions |
| **Effective Date** | When rule becomes active |
| **Expiration Date** | When rule expires (leave blank for indefinite) |
| **Source URL** | Link to government source |

3. Click **Save Rule**

> Either Amount or Percentage should be filled — not both.

#### Editing and Deactivating

Click a rule row to open the edit form. Toggle the **Active** switch to deactivate without deleting.

---

### Rule Review (Pending Rules)

**Navigation:** Sidebar → Rule Review

When the monitor detects a feed change and Claude extracts rules from the government page, those rules land here as **Pending Rules** for human review before being promoted to Local Rules.

#### Pending Rules List

Each row shows:
- Jurisdiction the rule was extracted from
- Source URL fetched
- Extraction confidence score (0.0 – 1.0)
- Number of rules extracted
- Status: `pending` / `approved` / `rejected`
- Date created

#### Reviewing a Pending Rule

1. Click a pending rule row to open the review modal
2. Review tabs:

| Tab | Content |
|---|---|
| **Extracted Rules** | JSON array of rules Claude found (name, category, type, amount, percentage, description) |
| **Raw Content** | First 5,000 chars of the government page content fetched |
| **Metadata** | Source URL, confidence score, extraction timestamp |

3. Take action:

| Button | Effect |
|---|---|
| **Approve** | Promotes quantified rules (credits, rebates, fees with dollar/percent values) to the `incentive_rules` table; promotes non-quantified process rules (permits, insurance mandates, portal links) to `jurisdiction_requirements` |
| **Reject** | Marks as rejected — no rule is created |
| **Add Notes** | Save review notes before approving or rejecting |

#### Confidence Scores

| Score | Meaning |
|---|---|
| 0.8 – 1.0 | High confidence — rule found in clear, structured government text |
| 0.5 – 0.8 | Medium confidence — rule inferred from context, verify before approving |
| 0.0 – 0.5 | Low confidence — likely no relevant rules or ambiguous content |

> Always verify rules with the source URL before approving, especially for fee amounts and eligibility dates.

---

## 8. AI Advisor

**Navigation:** Sidebar → AI Advisor

The AI Advisor is a Claude-powered chat interface for tax incentive questions.

### Using the Advisor

1. **Optional:** Select a production from the sidebar dropdown — gives Claude context about your specific budget, jurisdiction, and dates
2. Type your question in the input field
3. Press Enter or click **Send**
4. Responses stream in real time with markdown formatting

### Suggested Prompts

Click any suggested prompt to pre-fill the input:

- "What expenses qualify for the New York film tax credit?"
- "Compare Georgia vs. New Mexico incentives for a $5M feature"
- "What are the local hire requirements in Illinois?"
- "Explain the stacking rules for California productions"
- "What documentation is required for a refundable credit?"

### Production Context

When a production is selected in the sidebar:
- Claude knows the jurisdiction, budget, and dates
- Questions like "What credits apply to my project?" will use your production's data
- Responses include jurisdiction-specific details

### Limitations

- The Advisor answers based on its training data and the rules in your database — always verify against official government sources before filing
- If `ANTHROPIC_API_KEY` is not configured, the Advisor returns scripted fallback responses for common questions
- Chat history is session-only — it is not saved between page reloads

---

## 9. Budget Builder

**Navigation:** `http://localhost:8080/budget`

The Budget Builder converts a screenplay or manual budget into a detailed cost estimate with tax credit optimization and risk scoring. It operates in two modes: **Script Pipeline** and **Manual Entry**.

---

### Mode 1: Script Pipeline

The pipeline ingests a screenplay, analyzes it, estimates a budget, evaluates tax credits across all jurisdictions, and scores production risk — all in a single request.

#### Importing a File

Click **Import** (top right of the Script Pipeline panel) to open the format dropdown:

| Format | Extensions | Description |
|---|---|---|
| **Screenplay** | `.fountain`, `.fdx`, `.txt` | Script text. `.fdx` (Final Draft XML) is auto-converted to Fountain format |
| **Budget CSV** | `.csv` | Line-item budget. Required columns: `category`, `amount`. Optional: `description`, `qualifying` |
| **Project Config** | `.json` | Saved session — restores title, jurisdictions, and optionally script text |
| **Previous Result** | `.json` | Exported pipeline result — reloads result panel without re-running |

#### Running the Pipeline

1. Import a screenplay (`.fountain`, `.fdx`, or `.txt`)
2. Optionally set **Production Title**, **Emotion Override**, **Genre Override**, and **Jurisdiction** filters
3. Click **Run Pipeline**
4. Results appear in the panel below

#### Pipeline Result Panels

| Panel | Content |
|---|---|
| **Script Stats** | Scene count, dialogue blocks, unique characters, total lines |
| **Budget Estimate** | Per-component breakdown (scenes × $15K, dialogue × $2K, characters × $5K), genre and emotion multipliers, final total |
| **Tax Credit Analysis** | Top 5 jurisdictions ranked by estimated credit, optimal jurisdiction highlighted |
| **Risk Assessment** | Risk score (0–100), risk level (low/medium/high), risk factors |
| **Pipeline Errors** | Any service failures during processing |

#### Downloading Results

From the result panel:
- **Download PDF** — formatted PDF report via the pipeline `/report` endpoint
- **Download CSV** — budget breakdown in spreadsheet format
- **Export JSON** — full result as importable JSON (use as "Previous Result" import)

#### FDX (Final Draft) Files

`.fdx` files are Final Draft XML. The Budget Builder converts them to Fountain format client-side before sending to the pipeline. Supported paragraph types: `Scene Heading`, `Action`, `Character`, `Dialogue`, `Parenthetical`, `Transition`, `Shot`, `General`.

#### CSV Budget Format

When importing a Budget CSV, the parser accepts these column names (case-insensitive):

| Data | Accepted column names |
|---|---|
| Category | `category`, `dept`, `department` |
| Description | `description`, `name`, `item` |
| Amount | `amount`, `cost`, `total` |
| Qualifying | `qualifying`, `is_qualifying` (yes/no/true/false/1/0) |
| Title | `title`, `production` (first row only) |

---

### Mode 2: Manual Entry

Click **Manual Entry** (toggle at top of the page) to switch to the budget builder form.

#### Building a Budget Manually

1. Enter **Production Title**
2. Select a **Budget Template** (see templates below)
3. Select **Jurisdiction** for tax credit calculation
4. Click **Build Budget**

The API returns a structured budget with all line items, categorized spend totals, qualifying vs. non-qualifying split, and estimated tax credit for the selected jurisdiction.

#### Budget Templates

| Template | Budget Tier | Typical Range |
|---|---|---|
| Feature Film — Micro Budget | micro | Under $1M |
| Feature Film — Low Budget | low | $1M – $3.5M |
| Feature Film — Mid Budget | mid | $10M – $30M |
| TV Drama — One Hour Episode | basic | Per episode |
| TV Comedy — Half Hour Episode | basic | Per episode |
| Limited Series — Per Episode (Prestige) | high | Per episode |
| Reality / Unscripted Series — Per Episode | basic | Per episode |
| Documentary Feature | micro | Under $2M |
| Short Film | micro | Under $50K |
| Animated Series — Half Hour Episode | mid | Per episode |
| Commercial / Branded Content | basic | Per spot |

---

### Other Budget Builder Features

#### Budget Analysis (`/budget/analyze`)

POST a list of line items to get a summary:
- Total budget
- Above-the-line vs. below-the-line split
- Qualifying spend and percentage
- Estimated credit for a jurisdiction
- Recommendations (e.g., if qualifying spend is below 60%)

#### Rate Cards (`/rates/*`)

Look up union and non-union crew rates:
- `/rates/union?guild=DGA` — rate card for a specific guild
- `/rates/nonunion?location=GA` — non-union rates by location
- `/rates/estimate` — estimate crew cost for a role

#### Schedule Analysis (`/schedule/analyze`)

POST a production brief to get a recommended shoot schedule:
- Estimated shoot days
- Cost-per-day breakdown
- Schedule tier recommendation

#### Budget AI Advisor (`/advisor/chat`)

The Budget Builder has its own AI advisor endpoint focused on below-the-line budgeting, crew rates, and cost estimation questions.

---

### Pipeline Services

The Script Pipeline uses these backend microservices (all run in Docker):

| Service | Role |
|---|---|
| `screenplay-engine` | Parses Fountain/FDX, counts scenes, calculates base budget |
| `emotion-rules` | Applies genre and emotional tone budget multipliers |
| `risk-service` | Scores production risk based on script complexity |
| `pilotforge-adapter` | Connects to incentives-api for live tax credit data |
| `pipeline-orchestrator` | Coordinates all services, aggregates results |

If a service is down, the orchestrator returns partial results with error messages in `pipeline_errors`.

---

## 10. Reports & Exports

Reports can be generated from the Calculator page or the API directly.

### PDF Reports

| Report Type | What It Contains | Endpoint |
|---|---|---|
| **Comparison Report** | Multi-jurisdiction comparison table, rates, caps, eligibility | `POST /reports/comparison/` |
| **Compliance Report** | Checklist status, completion rate, outstanding items | `POST /reports/compliance/` |
| **Scenario Report** | Scenario inputs, projected credits, chart | `POST /reports/scenario/` |
| **Budget Pipeline Report** | Script stats, budget breakdown, tax credit ranking, risk score | Budget app `/pipeline/report` |

### Excel Reports

| Report Type | Worksheets | Endpoint |
|---|---|---|
| **Comparison Workbook** | Summary, per-jurisdiction details, rule breakdown | `POST /excel/comparison/` |
| **Compliance Workbook** | Checklist, categories, due dates | `POST /excel/compliance/` |
| **Scenario Workbook** | Scenarios, projections, sensitivity table | `POST /excel/scenario/` |

### Generating a Report from the UI

1. Navigate to **Calculator** → run any calculation
2. Click **Download PDF** or **Download Excel** on the result card
3. The file downloads immediately

### Generating via API

```bash
# PDF comparison report
curl -X POST http://localhost:8080/api/0.1.0/reports/comparison/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"production_id": "uuid", "jurisdiction_ids": ["uuid1", "uuid2"]}' \
  --output report.pdf

# Excel compliance workbook
curl -X POST http://localhost:8080/api/0.1.0/excel/compliance/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"production_id": "uuid"}' \
  --output compliance.xlsx
```

---

## 11. Monitoring System

The monitoring system automatically tracks government web pages for rule changes and uses Claude to extract new rules.

### How It Works

```
Government Website  →  fetch_url()  →  SHA-256 hash comparison
                                              ↓ (changed)
                                       Claude extraction
                                              ↓
                                       PendingRule created
                                              ↓
                                       Human review → approve → LocalRule
```

### Feed Sources

Each jurisdiction can have a `feedUrl` pointing to a government web page, RSS feed, or PDF URL. The monitor fetches these and detects changes by comparing SHA-256 hashes.

**Currently monitored jurisdictions:**

| Code | Jurisdiction | Feed URL |
| ---- | ------------ | -------- |
| NY-ERIE | Erie County, NY | `filmbuffaloniagara.com/permits-guidelines/` |
| NY-NASSAU | Nassau County, NY | `nassaucountyny.gov/film` |
| NY-WESTCHESTER | Westchester County, NY | `visitwestchesterny.com/film/permits/` |
| NY-NYC | New York City | `nyc.gov/site/mome/industries/tv-film.page` |
| CA-LA | Los Angeles County | `filmla.com/for-filmmakers/permits/` |
| CA-SANFRANCISCO | San Francisco, CA | `sf.gov/topic-permitting` |
| CA-SANDIEGO | San Diego, CA | `sandiego.gov/specialevents-filming/filming` |
| CA-SACRAMENTO | Sacramento, CA | `filmsac.com/feed/` *(RSS — change detection only)* |
| CA-OAKLAND | Oakland, CA | *(WAF-protected — manual monitoring)* |
| IL-COOK | Cook County / Chicago | `chicago.gov/…/chicago_film_office_tax.html` |
| GA-SAVANNAH | Savannah, GA | `filmsavannah.org/permits/` |
| GA-FULTON | Fulton County, GA | `fultoncountyga.gov/fultonfilms` |
| GA-DEKALB | DeKalb County, GA | `dekalbcountyga.gov/planning-and-sustainability/other-permitting-services-1` |
| GA-ATLANTA | Atlanta, GA | *(WAF-protected — manual monitoring)* |
| LA-NEW-ORLEANS | New Orleans, LA | `nolafilm.com/feed` |
| LA-BATONROUGE | Baton Rouge, LA | `batonrougefilm.com/permits/` |
| LA-SHREVEPORT | Shreveport, LA | *(no verified URL — manual monitoring)* |
| LA-JEFFERSON | Jefferson Parish, LA | *(no verified URL — manual monitoring)* |
| NM-ALBUQUERQUE | Albuquerque, NM | `cabq.gov/film` |
| NM-SANTAFE | Santa Fe, NM | `santafe.org/film` |
| TX-HOUSTON | Houston, TX | `houstonfilmcommission.com` |
| TX-SANANTONIO | San Antonio, TX | `filmsanantonio.com/permits/` |
| TX-AUSTIN | Austin, TX | *(no verified URL — manual monitoring)* |
| TX-DALLAS | Dallas, TX | *(feedUrl cleared — redirects to unrelated site)* |
| TX-FORTWORTH | Fort Worth, TX | *(WAF-protected — manual monitoring)* |

### Automated Schedule

The scheduler runs feed ingestion **every 4 hours** automatically when the backend is running. No manual action is required.

### Monitoring Events

The monitoring events feed is accessible via:
- `GET /api/0.1.0/monitoring/events/` — all events
- `GET /api/0.1.0/monitoring/events/unread-count/` — badge count
- `PATCH /api/0.1.0/monitoring/events/{id}/read/` — mark read

Events include: title, summary, severity (info/warning/alert), and publish date.

### Adding a New Monitoring Source

```bash
curl -X POST http://localhost:8080/api/0.1.0/monitoring/sources/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Mexico Film Office",
    "url": "https://nmfilm.com/incentives/",
    "sourceType": "rss",
    "jurisdiction": "NM"
  }'
```

### Manual Ingest

```bash
curl -X POST http://localhost:8080/api/0.1.0/monitoring/ingest/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 12. Incentive Maximizer

The Maximizer resolves jurisdiction layers from a lat/lng coordinate and calculates the maximum incentive stack from all applicable rules in `incentive_rules`.

### How It Differs from the Calculator

| | Calculator | Maximizer |
|---|---|---|
| Input | Select jurisdiction from dropdown | Lat/lng coordinates or codes |
| Data source | `incentive_rules` (single jurisdiction) | `incentive_rules` (state + all sub-jurisdictions) |
| Stacking | Single jurisdiction | Additive stacking across all layers |
| Spatial | Manual selection | Automatic bounding-box lookup |
| Mutual exclusions | N/A | Automatically resolves conflicting rules (keeps higher value) |

### Via the UI

The **Maximizer** tab (⚡ icon, sidebar) provides a point-and-click interface to the stacking engine.

**Input controls:**

| Control | Description |
| ------- | ----------- |
| **Input Mode** | Toggle between *Codes* (comma/space-separated jurisdiction codes) and *Lat / Lng* (decimal coordinates) |
| **Jurisdiction Codes** | e.g. `NY, NY-NYC` — stack parent + sub-jurisdiction rules together |
| **Project Type** | Feature Film, TV Series, Commercial, Documentary, or All / Unknown — filters out TV-only rules for film projects |
| **Qualified Spend** | Dollar amount (USD) — converts percentage rules to real dollar values; live display shows formatted amount |
| **Split spend by location** | Appears when ≥ 2 codes are entered. Toggle to enter per-jurisdiction spend — sub-jurisdiction bonuses (e.g. IL-CHICAGO-BONUS) use their location's spend; other rules use the total. |

**Quick Presets** (one-click fill):

| Preset | Codes | Result (film, $5M) |
| ------ | ----- | ------------------- |
| NYC — $5M Film | `NY, NY-NYC` | $2.00M at 40% |
| Chicago — $5M Film | `IL, IL-COOK` | $2.50M at 50% |
| Los Angeles — $5M Film | `CA, CA-LA` | $1.00M at 20% |
| San Diego — $5M Film | `CA, CA-SANDIEGO` | $1.0025M at 20.05% |
| Georgia — $5M Film | `GA` | $1.00M at 20% + opt-in logo uplift |
| New Mexico — $5M Film | `NM` | $1.25M at 25% + opt-in uplifts |
| Louisiana — $5M Film | `LA` | $1.25M at 25% + opt-in labor/music |
| Texas — $5M Film | `TX` | $750K at 15% + opt-in uplifts |
| San Antonio — $5M Film | `TX, TX-SANANTONIO` | $750K base + $700K SA local opt-in |
| Erie County — $5M Film | `NY, NY-ERIE` | $1.50M at 30% |

**Results panel:**

- **Hero card** — total incentive value, effective rate, jurisdiction count, spend (shows *split* badge when location splits are active)
- **Applied Rules** — table of every rule applied, with rule type badge, dollar value, and underlying % rate
- **Breakdown by Category** — horizontal bar chart showing credit / rebate / permit-fee totals
- **Opt-in Upside** (amber) — rules that require an election and were excluded from the base total; shown as additive upside
- **Notes / Warnings** (slate) — mutual exclusions resolved, permit fees netted, and other advisory messages

### Via the API

**POST /api/0.1.0/maximize**

```json
{
  "jurisdiction_codes": ["IL", "IL-COOK"],
  "qualified_spend": 5000000,
  "project_type": "film",
  "spend_by_location": {
    "IL": 5000000,
    "IL-COOK": 2000000
  }
}
```

Lat/lng mode:

```json
{
  "lat": 42.8864,
  "lng": -78.8784,
  "qualified_spend": 5000000,
  "project_type": "film"
}
```

**GET /api/0.1.0/maximize/lookup?lat=42.8864&lng=-78.8784**

Returns the list of jurisdictions that contain the point — useful for populating frontend dropdowns.

### Via Command Line

```bash
# Basic — lat/lng, no spend (returns raw percentages)
python maximizer.py 42.8864 -78.8784

# With qualified spend — returns real dollar values
python maximizer.py 42.8864 -78.8784 --spend 5000000

# Explicit jurisdiction codes
python maximizer.py --codes NY NY-ERIE NY-NYC --spend 5000000

# Filter by project type
python maximizer.py 34.0522 -118.2437 --spend 10000000 --type film

# Split spend by location (Chicago: $5M total, $2M in Chicago)
python maximizer.py --codes IL IL-COOK --spend 5000000 --type film \
    --location-spend IL:5000000 IL-COOK:2000000
```

### Multi-Market Benchmark ($5M Film)

| Market | Jurisdiction Codes | Base Incentive | Rate | Opt-In Upside | Type |
| ------ | ------------------ | -------------- | ---- | ------------- | ---- |
| Chicago | `IL` + `IL-COOK` | $2,500,000 | 50% | +$500K (Green + Relocation) | Tax credit |
| New Mexico (rural) | `NM` | $1,250,000 | 25% | +$750K (TV uplift + QPF + rural) | Refundable credit |
| New Orleans | `LA` + `LA-NEW-ORLEANS` | $1,250,000 | 25% | +$750K (logo + labor) | Transferable credit |
| NYC | `NY` + `NY-NYC` | $2,000,000 | 40% | — | Tax credit |
| Georgia | `GA` | $1,000,000 | 20% | +$500K (logo in credits) | Tax credit |
| Los Angeles | `CA` + `CA-LA` | $1,000,000 | 20% | — | Tax credit |
| Texas (base) | `TX` | $750,000 | 15% | +$375K (music + veteran + post) | Cash grant |
| Texas — San Antonio | `TX` + `TX-SANANTONIO` | $750,000 | 15% | +$1,075K (SA local + all uplifts) | Cash grant |

### Opt-In Bonuses

Some rules require a production-specific election. The Maximizer **excludes opt-in rules from the base total** and surfaces them as warnings:

```text
[!] IL-FILM-GREEN-BONUS (5% = $250,000) requires opt-in election — not included in base total
[!] IL-FILM-RELOCATION-BONUS (5% = $250,000) requires opt-in election — not included in base total
```

### Mutual Exclusions

| Rule A | Rule B | Reason |
|---|---|---|
| `NY-FILM-BASE` | `NY-POST-PROD` | Post-production credit is for productions that did **not** shoot in NY |

---

## 13. Admin & User Management

**Navigation:** Sidebar → Settings → Admin (visible to admin role only)

### User Roles

| Role | Access |
|---|---|
| `admin` | Full access — all pages, user management, rule approval |
| `viewer` | Read-only — can view productions, run calculator, use advisor |

### Creating a User

1. Go to **Admin** page
2. Click **+ Invite User**
3. Enter email, temporary password, and assign role
4. Click **Create User**
5. Share credentials securely — users should change password on first login

### Updating a User

1. Click the user row in the admin table
2. Options:
   - **Change role** (admin ↔ viewer)
   - **Reset password** — set a new temporary password
   - **Deactivate** — blocks login without deleting the user
   - **Reactivate** — restores access
   - **Delete** — permanent

### Changing Your Own Password

1. Go to **Settings** → **Account**
2. Enter current password and new password
3. Click **Save**

---

## 14. Notifications & Preferences

**Navigation:** Settings → Notifications

### Setting Up Notifications

1. Enter your **email address** for notifications
2. Select **jurisdictions** to watch (you will be notified when their rules change)
3. Toggle **Active** to enable/disable all notifications
4. Click **Save**

### Notification Triggers

- A monitored jurisdiction's feed changes and a new PendingRule is created
- A compliance item on one of your productions is overdue
- A rule you follow is about to expire

### Managing via API

```bash
# Get preferences
GET /api/0.1.0/notifications/preferences/

# Create or update
POST /api/0.1.0/notifications/preferences/
{
  "jurisdictions": ["NY", "CA", "IL"],
  "emailAddress": "you@studio.com",
  "active": true
}

# Remove
DELETE /api/0.1.0/notifications/preferences/
```

---

## 15. Command-Line Tools

### monitor.py

Fetches government web pages, detects content changes, and extracts rules via Claude.

```bash
# Full scan — all sub-jurisdictions with feedUrl
python monitor.py

# Single jurisdiction
python monitor.py --code NY-ERIE

# Dry run — fetch and hash only, no DB writes or Claude calls
python monitor.py --dry-run

# Run with real Claude API (override MOCK_CLAUDE setting)
MOCK_CLAUDE=false python monitor.py --code NY-WESTCHESTER
```

**What it logs:**

```
[NY-ERIE] Change detected — sending to Claude
[NY-ERIE] 3 rule(s) extracted, confidence=0.82
[NY-NASSAU] No change
Complete — changed: 1  unchanged: 1  errors: 0  pending rules queued: 3
```

---

### maximizer.py

Command-line interface to the incentive stacking engine.

```bash
python maximizer.py <lat> <lng> [--spend AMOUNT] [--type TYPE] [--codes CODE1 CODE2...]

# Examples
python maximizer.py 42.8864 -78.8784 --spend 5000000
python maximizer.py 34.0522 -118.2437 --spend 8000000 --type film
python maximizer.py --codes CA CA-LA --spend 8000000
```

---

### Seed Scripts (scripts/)

| Script | Purpose | When to Run |
|---|---|---|
| `seed_jurisdictions.py` | Base US states + international | Fresh install only |
| `seed_incentive_rules.py` | State-level incentive rules | After jurisdictions |
| `seed_more_jurisdictions.py` | County/city sub-jurisdictions | After base jurisdictions |
| `seed_more_rules.py` | Additional rules and variants | After sub-jurisdictions |
| `seed_remaining_us_states.py` | Full 50-state coverage | Optional |
| `seed_global_expansion.py` | Canada, UK, Australia, Ireland, etc. | Optional |
| `seed_maximizer_test.py` | LocalRules for NY/CA/IL/GA (test data) | For Maximizer testing |
| `resolve_migrations.py` | Mark failed migrations as resolved | Migration fix only |
| `update_rules_2026.py` | Refresh rule rates and expiration dates | Annual update |

**Running a seed script:**

```bash
# Inside Docker container
docker cp scripts/seed_jurisdictions.py sceneiq-incentives-api:/app/scripts/seed_jurisdictions.py
docker exec sceneiq-incentives-api python scripts/seed_jurisdictions.py
```

> Scripts use `INSERT ... ON CONFLICT DO NOTHING` — safe to re-run.

---

## 16. API Reference

### Incentives API (`http://localhost:8001`)

All endpoints require a JWT Bearer token except `POST /auth/login`.

#### Authentication

```bash
POST /api/0.1.0/auth/login
Body: { "email": "admin@sceneiq.com", "password": "sceneiq2024" }
Returns: { "access_token": "eyJ...", "token_type": "bearer" }
```

Tokens expire after **8 hours** (configurable via `JWT_EXPIRE_HOURS`). A 401 response automatically clears the stored token and redirects to the login page.

#### Productions

| Method | Path | Description |
|---|---|---|
| GET | `/productions/` | List all productions |
| POST | `/productions/` | Create production |
| GET | `/productions/{id}` | Get production detail |
| PUT | `/productions/{id}` | Update production |
| DELETE | `/productions/{id}` | Delete production |
| GET | `/productions/{id}/expenses/` | List expenses |
| POST | `/productions/{id}/expenses/` | Add expense |
| DELETE | `/productions/{id}/expenses/{eid}` | Delete expense |
| POST | `/productions/{id}/expenses/generate/` | Auto-generate expenses |
| GET | `/productions/{id}/compliance/` | List compliance items |
| POST | `/productions/{id}/compliance/generate/` | Auto-generate checklist |
| PATCH | `/compliance/{item_id}` | Update compliance item |

#### Calculator

| Method | Path | Description |
|---|---|---|
| POST | `/calculate/` | Quick calculate |
| POST | `/calculate/simple/` | Single rule calculation |
| POST | `/calculate/compare/` | Multi-jurisdiction compare |
| GET | `/calculate/jurisdiction/{id}` | Rules for jurisdiction |
| POST | `/calculate/compliance/` | Compliance check |
| POST | `/calculate/date-based/` | Date-specific rules |
| POST | `/calculate/scenario/` | Scenario modeling |

#### Jurisdictions & Rules

| Method | Path | Description |
|---|---|---|
| GET | `/jurisdictions/` | List jurisdictions |
| GET | `/jurisdictions/{id}` | Jurisdiction detail |
| POST | `/jurisdictions/` | Create jurisdiction |
| PUT | `/jurisdictions/{id}` | Update jurisdiction |
| DELETE | `/jurisdictions/{id}` | Delete jurisdiction |
| GET | `/incentive-rules/` | List all incentive rules |
| GET | `/local-rules/` | List local rules |
| POST | `/local-rules/` | Create local rule |
| PATCH | `/local-rules/{id}/` | Update local rule |

#### Stacking Engine & Maximizer

| Method | Path | Description |
|---|---|---|
| POST | `/stacking-engine/calculate/` | Stack for a scenario |
| POST | `/stacking-engine/compare/` | Compare across jurisdictions |
| POST | `/maximize` | Full maximize (lat/lng or codes) |
| GET | `/maximize/lookup` | Resolve jurisdictions for a point |

#### Monitoring & Reports

| Method | Path | Description |
|---|---|---|
| GET | `/monitoring/events/` | List events |
| GET | `/monitoring/events/unread-count/` | Unread count |
| PATCH | `/monitoring/events/{id}/read/` | Mark read |
| POST | `/monitoring/ingest/` | Trigger ingest |
| POST | `/reports/comparison/` | PDF comparison report |
| POST | `/reports/compliance/` | PDF compliance report |
| POST | `/excel/comparison/` | Excel comparison workbook |
| POST | `/excel/compliance/` | Excel compliance workbook |

#### AI & Admin

| Method | Path | Description |
|---|---|---|
| POST | `/advisor/chat/` | Streaming AI chat (SSE) |
| GET | `/admin/users/` | List users |
| POST | `/admin/users/` | Create user |
| PATCH | `/admin/users/{id}/` | Update user |
| DELETE | `/admin/users/{id}/` | Delete user |
| GET | `/health` | Health check |

---

### Budget API (`http://localhost:8002`)

#### Budget Builder

| Method | Path | Description |
|---|---|---|
| POST | `/api/0.1.0/budget/create` | Create budget from template |
| GET | `/api/0.1.0/budget/templates` | List all budget templates |
| POST | `/api/0.1.0/budget/analyze` | Analyze line items |
| GET | `/api/0.1.0/budget/accounts` | Standard account codes |

#### Rates

| Method | Path | Description |
|---|---|---|
| GET | `/api/0.1.0/rates/union` | Union rate cards (optional `?guild=DGA`) |
| GET | `/api/0.1.0/rates/nonunion` | Non-union rates (optional `?location=GA`) |
| GET | `/api/0.1.0/rates/guilds` | List all guilds |
| POST | `/api/0.1.0/rates/estimate` | Estimate cost for a role |

#### Schedule & Incentives

| Method | Path | Description |
|---|---|---|
| POST | `/api/0.1.0/schedule/analyze` | Shoot schedule recommendation |
| GET | `/api/0.1.0/schedule/tiers` | Budget tiers |
| GET | `/api/0.1.0/schedule/production-types` | Production type list |
| POST | `/api/0.1.0/incentives/analyze` | Incentive analysis for a budget |
| GET | `/api/0.1.0/incentives/jurisdictions` | All available jurisdictions |
| POST | `/api/0.1.0/incentives/stack` | Stack incentives for a jurisdiction |

#### AI Advisor (Budget)

| Method | Path | Description |
|---|---|---|
| POST | `/api/0.1.0/advisor/chat` | Streaming chat (SSE) — budget focus |
| GET | `/api/0.1.0/advisor/prompts` | Suggested budget prompts |
| POST | `/api/0.1.0/advisor/rate-check` | Validate a proposed crew rate |

---

### Pipeline (`http://localhost:8080/pipeline/`)

| Method | Path | Description |
|---|---|---|
| POST | `/pipeline/orchestrate` | Run full pipeline (script → budget → credits → risk) |
| POST | `/pipeline/report` | Generate PDF report from result JSON |
| GET | `/pipeline/health` | Pipeline health check |

---

## 17. Database Models

### Core Models

**User** — Platform accounts
- `email` (unique), `passwordHash`, `role` (admin/viewer), `isActive`

**Jurisdiction** — States, counties, cities, countries
- `code` (unique — e.g., `NY`, `NY-ERIE`), `name`, `type`, `country`, `currency`
- `parentId` — links counties/cities to their parent state
- `feedUrl`, `feedLastChecked`, `feedLastHash` — monitoring fields
- `treatyPartners[]` — array of co-treaty jurisdiction codes

**IncentiveRule** — Primary state-level tax incentive rules
- `ruleCode` (unique), `ruleName`, `incentiveType`, `percentage`, `fixedAmount`
- `minSpend`, `maxCredit`, `eligibleExpenses[]`, `excludedExpenses[]`, `creditType`
- `effectiveDate`, `expirationDate`
- `requirements` (JSON) — machine-readable eligibility flags:
  - `"tvSeries": true` — rule is excluded when `project_type=film`
  - `"optIn": true` — rule requires production election; excluded from base total
  - `"relocatingProject": true` — rule only applies to relocating productions

**LocalRule** — County/city/sub-jurisdiction rules
- `code` (unique), `name`, `category`, `ruleType`, `amount`, `percentage`
- `effectiveDate`, `expirationDate`, `sourceUrl`, `extractedBy` (manual/monitor), `active`

**JurisdictionRequirement** — Non-quantified compliance requirements
- `name`, `category` — `permit | insurance | registration | designation | portal | contact | other`
- `requirementType` — `mandatory | recommended | informational`
- `description`, `applicableTo[]` — project types; empty = all types

**Production** — Film/TV productions
- `title`, `productionType`, `budgetTotal`, `budgetQualifying`
- `status` — `planning | pre_production | production | post_production | completed`
- `jurisdictionId`, `startDate`, `endDate`, `productionCompany`

**Expense** — Production expense line items
- `category`, `description`, `amount`, `expenseDate`
- `isQualifying` — whether this expense counts toward incentive calculation

**ComplianceItem** — Checklist items per production
- `label`, `category`, `status` (pending/complete/waived/na)
- `dueDate`, `completedAt`, `notes`

**PendingRule** — Extracted rules awaiting review
- `sourceUrl`, `rawContent`, `extractedData` (JSON), `confidence`
- `status` — `pending | approved | rejected`

**MonitoringEvent** — Change detections
- `title`, `summary`, `url`, `contentHash`
- `severity` (info/warning/alert), `isRead`, `publishedAt`

---

## 18. Deployment & Operations

### Docker Compose (Local Development)

```bash
# Start all services
docker compose up -d

# View logs for a service
docker compose logs -f incentives-api
docker compose logs -f budget-api
docker compose logs -f pipeline-orchestrator

# Rebuild a specific service
docker compose build budget-ui
docker compose up -d budget-ui

# Restart a service without rebuilding
docker compose restart incentives-api
```

### Rebuilding After Code Changes

| Change type | Command |
|---|---|
| Backend Python code (volume-mounted) | `docker compose restart incentives-api` |
| Budget API Python code (volume-mounted) | `docker compose restart budget-api` |
| Incentives frontend | `docker compose build incentives-ui && docker compose up -d incentives-ui` |
| Budget frontend | `docker compose build budget-ui && docker compose up -d budget-ui` |
| nginx.conf | `docker compose restart nginx` |

### Copying Files Into Containers

The backend `src/` directories are volume-mounted — Python changes are live after restart. Files at the project root (like `maximizer.py`) are **not** volume-mounted and must be copied:

```bash
docker cp maximizer.py sceneiq-incentives-api:/app/maximizer.py
docker cp scripts/my_script.py sceneiq-incentives-api:/app/scripts/my_script.py
```

### Railway Deployment

The platform deploys to Railway as 5 independent services. See the Railway project dashboard for current service URLs and variable configuration.

**Services:**
- `incentives-api` — Dockerfile (backend)
- `incentives-ui` — Dockerfile (frontend)
- `budget-api` — Dockerfile (backend)
- `budget-ui` — Dockerfile (frontend)
- `Postgres` — Railway managed plugin

**Key environment variables per service:**

| Service | Required Variables |
|---|---|
| incentives-api | `DATABASE_URL`, `JWT_SECRET`, `ANTHROPIC_API_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` |
| budget-api | `DATABASE_URL`, `JWT_SECRET`, `ANTHROPIC_API_KEY`, `INCENTIVES_API_URL` |
| incentives-ui | `VITE_API_URL` (build arg) |
| budget-ui | `VITE_API_URL`, `VITE_COMPLIANCE_URL` (build args) |

> Railway does not pass service Variables as Docker build args. Build-time env vars (`VITE_*`) must be declared in `railway.toml` as `buildArgs`.

---

## 19. Environment Variables

### Incentives API

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `JWT_SECRET` | Yes | — | Secret key for JWT signing (32+ chars) |
| `ANTHROPIC_API_KEY` | No | — | Claude API key (AI Advisor + rule extraction) |
| `ADMIN_EMAIL` | No | `admin@sceneiq.com` | Seeded admin email |
| `ADMIN_PASSWORD` | No | `sceneiq2024` | Seeded admin password |
| `MOCK_CLAUDE` | No | `false` | Set `true` to use simulated Claude responses |
| `JWT_EXPIRE_HOURS` | No | `8` | Token lifetime in hours |
| `API_VERSION` | No | `0.1.0` | API path version segment |

### Budget API

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `JWT_SECRET` | Yes | — | Must match incentives-api JWT_SECRET |
| `ANTHROPIC_API_KEY` | No | — | Claude API key for budget advisor |
| `INCENTIVES_API_URL` | No | — | Base URL of incentives-api (for live rate data) |
| `APP_ENV` | No | `production` | `development` enables debug logging |

**Example `.env` (local development):**

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5435/tax_incentive_db
JWT_SECRET=my-super-secret-32-char-key-here
ANTHROPIC_API_KEY=sk-ant-api03-...
ADMIN_EMAIL=admin@sceneiq.com
ADMIN_PASSWORD=sceneiq2024
MOCK_CLAUDE=false
JWT_EXPIRE_HOURS=8
```

---

## 20. Troubleshooting

### Login fails — "Invalid credentials"
- Confirm you are using `admin@sceneiq.com` / `sceneiq2024`
- Confirm the backend is running: `curl http://localhost:8080/health`
- Check backend logs: `docker compose logs incentives-api`

### All pages show blank / white screen
- Rebuild: `docker compose build incentives-ui && docker compose up -d incentives-ui`
- Check browser console for JS errors
- Confirm you are using `http://localhost:8080` — not port 3000 or port 80

### API calls return 405 Method Not Allowed
- The request is hitting the wrong service through nginx
- Budget API calls (`/budget/create`, `/rates/*`, etc.) must go to `http://localhost:8002` — the budget-ui is pre-built with this URL baked in
- Incentives API calls (`/productions`, `/jurisdictions`, etc.) go through `http://localhost:8080/api/`

### Budget Builder shows 405 on Build Budget
- This means the budget-ui JS bundle has the wrong API URL
- Rebuild: `docker compose build budget-ui && docker compose up -d budget-ui`
- Verify the build arg is set: `VITE_API_URL=http://localhost:8002` in docker-compose.yml

### Pipeline returns 404 on `/pipeline/orchestrate`
- Check the pipeline-orchestrator is running: `docker compose ps pipeline-orchestrator`
- Check nginx routing: `docker compose logs nginx`
- The pipeline location in nginx.conf must include `rewrite ^/pipeline/(.*)$ /$1 break;`

### Pipeline returns 0 scenes from FDX file
- The screenplay engine only parses Fountain format — FDX conversion happens client-side
- Verify the file is a valid Final Draft `.fdx` (XML with `<Paragraph Type="...">` elements)
- Check browser console for conversion errors

### Budget Builder shows stale results after import
- Import a new screenplay — the result panel should clear when a non-result file is imported
- If result persists, hard refresh: Ctrl+Shift+R (Windows) / Cmd+Shift+R (Mac)

### Pipeline-orchestrator 502 Bad Gateway
- Check the orchestrator container: `docker compose logs pipeline-orchestrator`
- Verify `entrypoint.sh` has LF line endings (not CRLF) — Windows machines can corrupt shell scripts
- `.gitattributes` should contain `*.sh text eol=lf`

### "Failed to load pending rules" or "Failed to load local rules"
- Check that migrations ran: `docker exec sceneiq-incentives-api python -m prisma migrate status`
- Re-run if needed: `docker exec sceneiq-incentives-api python -m prisma migrate deploy`

### monitor.py returns "invalid x-api-key" (401)
- `ANTHROPIC_API_KEY` in `.env` is missing or invalid
- Use mock mode for local testing: `MOCK_CLAUDE=true python monitor.py`

### maximizer.py returns "No jurisdictions found"
- The `jurisdictions` table is empty — run `seed_jurisdictions.py`
- Coordinates must fall within a US state's bounding box
- Use `--codes` to specify explicitly: `python maximizer.py --codes NY --spend 1000000`

### Prisma P3009 migration error on Railway
- A migration was recorded as failed in `_prisma_migrations`
- Run: `python scripts/resolve_migrations.py`

### Database connection refused
- Check `DATABASE_URL` is set correctly
- Verify postgres container is healthy: `docker compose ps`
- Test: `docker exec sceneiq-incentives-api python -c "import psycopg2, os; psycopg2.connect(os.environ['DATABASE_URL']); print('OK')"`

### AI Advisor shows no response / stops streaming
- Check `ANTHROPIC_API_KEY` is set: `docker exec sceneiq-incentives-api printenv ANTHROPIC_API_KEY`
- Set `MOCK_CLAUDE=true` for scripted fallback responses
- Check backend logs for SSE errors: `docker compose logs -f incentives-api`

### Neo4j fails to start (screenplay engine errors)
- Check Neo4j container: `docker compose logs neo4j`
- Default credentials are `neo4j` / `password123`
- APOC plugin must load on first start — can take 30–60 seconds

---

*SceneIQ v3.0 — Tax Incentive Compliance Platform*
*For support, file an issue at the project repository.*
