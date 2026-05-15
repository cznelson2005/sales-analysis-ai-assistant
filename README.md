# Sales AI Assistant

An AI-powered sales analytics dashboard that automatically analyzes MRR trends, 
detects anomalies, and generates executive insights using a multi-agent LLM pipeline.

## 🔗 Live Demo
👉 [View Dashboard](https://customer-support-llm-agent-fklfbpgjecnfp8mlbbhych.streamlit.app/)

---

## 🏗️ Architecture
```
User selects market + time range
        ↓
Orchestrator — executes SQL queries on sales data
        ↓
Overview Agent — generates headline metrics narrative
        ↓
Anomaly Detector — scans for irregularities across MRR, churn, CAC
        ↓ (if anomaly found)
Deep Dive Agent — drills down into flagged markets to identify drivers
        ↓
Summary Agent — produces executive summary + prioritized recommendations
```
---

## 📁 Project Structure
```
sales-ai-assistant/
├── data/                        # Simulated SaaS dataset
│   ├── customers.csv            # 2,000 customer records (2022–2024)
│   ├── monthly_revenue.csv      # ~86,000 monthly revenue rows
│   ├── monthly_churn.csv        # 649 churned customer records
│   ├── schema.json              # Data dictionary for all tables
│   └── generate_data.py         # Data generation script
├── results/                     # Pre-run analysis results (JSON)
│   ├── All_2022_2024.json
│   ├── HK_2022_2024.json
│   └── ...
├── notebook/
│   └── sales_agent.ipynb        # Agent development & pipeline walkthrough
└── app/
    ├── streamlit_app.py         # Dashboard UI
    ├── orchestrator.py          # Data fetching layer (DuckDB SQL)
    └── agents.py                # LLM agent functions
```
Note on results dataset: For demo purposes results are pre-computed. In production this would call the API live with any user-selected date range
---

## 🤖 Agent Design

| Agent | Role | Temperature |
|---|---|---|
| Overview | Headline metrics + narrative | 0.3 |
| Anomaly Detector | Rule-based anomaly flagging + Python filter | 0.0 |
| Deep Dive | Market-level driver analysis | 0.1 |
| Summary | Executive summary + recommendations | 0.4 |

Key design decisions:
- **Python filter layer** on top of LLM output to enforce anomaly thresholds strictly
- **Pre-calculated metrics** injected into prompts to prevent LLM hallucination on numbers
- **Pre-run results** cached as JSON to enable reliable demo without live API calls
- **DuckDB** for in-memory SQL queries on CSV data — no database setup required

---

## 📊 Dataset

Simulated SaaS dataset for an accounting software company:
- **Markets**: SG, HK, AU, UK
- **Products**: Accounting, Compliance, Payroll, Incorporation
- **Segments**: Startup, SME, Corporate
- **Time range**: Jan 2022 — Dec 2024

Embedded patterns for demo:
- HK churn spike in Q3 2023 (simulating macro uncertainty)
- UK high CAC due to new market expansion
- SG Q1 incorporation spike (new financial year)
- 2024 plan upgrade trend (CFO service upsell)

---

## 🚀 Setup

1. Clone the repo
2. Install dependencies
   pip install -r requirements.txt
3. Set up API key
   cp .env.example .env
   # Add your Gemini API key to .env
4. Run the dashboard
   streamlit run app/streamlit_app.py

---

## 🛠️ Tech Stack

- Python, Pandas, DuckDB
- Google Gemini API (gemini-2.5-flash-lite)
- Streamlit
- Jupyter Notebook
