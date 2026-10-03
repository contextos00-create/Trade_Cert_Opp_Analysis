Trade Certification Testing Content Analysis (51 States + Municipalities)
A comprehensive, data-driven platform designed to centralize statewide and municipal trade certification requirements, testing content, level of effort (LOE) metrics, and feasibility studies. This repository powers an advanced preparation and practice ecosystem built to help individuals enter skilled trades and seamlessly ascend through their professional disciplines.
---
🚀 Project Overview
Navigating the fragmented landscape of trade certifications across all 50 U.S. states plus Washington, D.C. is a massive hurdle for trade professionals. Requirements vary wildly between state-level boards and local municipalities.
This project solves that friction by:
Aggregating Regulatory Data: Automatically discovering and extracting certification rules, exam blueprints, and renewing guidelines at both state and municipal levels.
Analyzing Testing Blueprints: Assessing content coverage, difficulty tiers, and Level of Effort (LOE) required to pass.
Powering a Prep Platform: Utilizing the mapped content to generate dynamic, hyper-localized practice tests and career ascension pathways (e.g., Apprentice $\rightarrow$ Journeyman $\rightarrow$ Master).
---
🧠 Data Acquisition Architecture (LangGraph + LangSmith)
To gather highly unstructured regulatory data efficiently and reliably, this project utilizes an agentic multi-lane orchestration process.
```
                      +[ LangGraph Multi-Lane Agent ]+
                      |                              |
         [ Lane 1: Statewide ]             [ Lane 2: Municipalities ]
         - Board regulations               - Local building codes
         - Exam blueprints                 - Local ordinances
                      |                              |
                      +--------------+---------------+
                                     |
                           [ LangSmith Observability ]
                           - LLM Prompt Engineering
                           - Cost & Token Tracking
                           - Quality & Feasibility Guardrails
```
🛣️ Multi-Lane LangGraph Process
Statewide Focus Lane: Targets state-level licensing boards, department of labor portals, and centralized exam providers (e.g., PSI, Prometric) to catalog baseline requirements.
Municipality Focus Lane: Drills down into city and county-level building departments, localized code variations, and specific local licensing ordinances.
Evaluation Lane: Scores the retrieved data for accuracy, formatting completeness, and structured ingestion viability.
🛠️ Observability & Feasibility with LangSmith
We leverage LangSmith to monitor our data extraction pipelines:
Trace Analysis: Debugging multi-step agent reasoning paths across state web scrapers.
Feasibility Studies: Evaluating the reliable automation potential (Feasibility Index) of extracting data from notoriously legacy municipal portals.
Cost & Performance Tracking: Optimizing token spend and prompt latency during heavy content analysis jobs.
---
📊 Repository Structure
```text
├── .github/                # CI/CD workflows for data validation
├── data/
│   ├── raw/                # Unstructured PDFs, scraped HTML from state/local boards
│   └── processed/          # Unified JSON schema maps for all 51 states
├── pipelines/
│   ├── graphs/             # LangGraph topology definitions (statewide vs. local lanes)
│   ├── prompts/            # Structured system prompts optimized via LangSmith
│   └── evaluators/         # Feasibility and confidence scoring algorithms
├── analysis/
│   ├── loe_models/         # Level of Effort calculators based on exam item banks
│   └── feasibility/        # Reports on data extraction reliability by state
└── README.md
```
---
🛠️ Getting Started
Prerequisites
Python 3.10+
Poetry or Virtualenv
OpenAI / Anthropic API keys (configured for LangGraph agents)
LangSmith API Key (for pipeline tracing)
Installation
Clone the repository:
```bash
   git clone https://github.com/your-username/trade-cert-analysis.git
   cd trade-cert-analysis
   ```
Set up your environment variables (`.env`):
```env
   OPENAI_API_KEY=your_openai_key
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
   LANGCHAIN_API_KEY=your_langsmith_key
   LANGCHAIN_PROJECT="trade-certification-analysis"
   ```
Install dependencies:
```bash
   pip install -r requirements.txt
   # Or using poetry
   poetry install
   ```
Run a sample extraction lane (e.g., Ohio statewide electrical trades):
```bash
   python pipelines/run_lane.py --state OH --scope statewide --trade electrical
   ```
---
🎯 Target Platform Core Features
The underlying data processed here feeds a consumer-facing prep platform designed for trade progression:
Hyper-Localized Question Banks: Practice questions tailored precisely to the local municipality codes the user will be tested on.
Ascension Mapping: Clear visual timelines showing a professional what exams, hours, and LOE are needed to graduate from their current tier to the next.
Predictive Readiness Scores: Analysis of practice test telemetry mapped against real exam blueprints to verify when an applicant is actually ready to sit for the official test.
---
🤝 Contributing
Contributions to refine extraction prompts, update municipal schemas, or expand LOE calculations are welcome. Please read `CONTRIBUTING.md` and ensure all updated agent flows are traced and evaluated inside LangSmith before submitting a Pull Request.
---
📄 License
This project is licensed under the MIT License - see the `LICENSE` file for details.
