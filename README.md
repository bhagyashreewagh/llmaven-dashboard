# LLMaven Analytics Pipeline

> Understand how LLMs are actually used in research software engineering.

LiteLLM logs every API call as a JSON file → Azure Data Lake Storage → Streamlit dashboard reads it all, anonymizes PII, and refreshes every 5 minutes. No ETL jobs. No intermediate databases.

```
LiteLLM Proxy  →  Azure Data Lake Storage  →  Streamlit Dashboard
(logs .json)       (litellm-logs container)     (reads + anonymizes)
```

**Live dashboard:** https://llmaven-prod-streamlit.azurewebsites.net

---

## Why we built this

The primary motivation is to leverage logged LLM usage data to better understand how LLMs are used in research software engineering. Beyond raw logs, this pipeline provides:

- **Proper sessions** — group individual requests into conversations instead of isolated calls
- **Anonymized data** — real identities replaced with consistent `user_001`, `user_002`, … IDs; reversible by admins via Key Vault
- **Dashboard + querying** — 7 analytics views covering cost, usage, cache, sessions, and AI Q&A
- **Fine-tuning datasets** — export anonymized session data in training format *(coming soon)*
- **Tool/skill/MCP evaluation** — understand which tools and MCP servers researchers rely on *(coming soon)*

---

## Architecture

```
┌─────────────────┐     one .json    ┌──────────────────────────────┐
│  LiteLLM Proxy  │ ──────────────►  │  Azure Data Lake Storage     │
│  (Carlos's)     │  per API call    │  Container: litellm-logs     │
└─────────────────┘                  │  Path: logs/YYYY/MM/DD/<id>  │
                                     └──────────────┬───────────────┘
                                                    │ reads all blobs
                                                    ▼
                                     ┌──────────────────────────────┐
                                     │  Streamlit Dashboard         │
                                     │  Azure App Service (B2)      │
                                     │  Docker: llmaven-dashboard   │
                                     │  Refreshes every 5 min       │
                                     └──────────────────────────────┘
```

### Azure Resources

| Resource | Name | Purpose |
|---|---|---|
| App Service Plan | `llmaven-prod-apps-plan` | Hosts Streamlit container |
| App Service (Streamlit) | `llmaven-prod-streamlit` | Dashboard |
| Container Registry | `llmavenprodacr141w` | Docker image storage |
| Key Vault | `llmaven-prod-kv-141w` | Connection string + anonymization map |
| App Insights | `llmaven-prod-ai` | Dashboard logs/monitoring |
| Storage Account | `llmavenissprodwestst` | ADLS Gen2, LiteLLM logs (Carlos's) |

---

## Repository Structure

```
llmaven/
├── dashboard/          # Streamlit app (deployed to Azure App Service)
│   ├── app.py          # Main app — tab router
│   ├── data.py         # Data loader — reads from ADLS, anonymizes PII
│   ├── config.py       # Color palette, constants
│   ├── styles.py       # CSS + Plotly theme
│   ├── utils.py        # Formatting helpers
│   ├── tabs/           # One file per dashboard tab
│   ├── requirements.txt
│   └── Dockerfile
│
├── infra/              # Terraform — provisions all Azure resources
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── terraform.tfvars.example   ← copy to terraform.tfvars and fill in
│   └── modules/
│       ├── app_services/   # ACR + App Service Plan + Streamlit web app
│       ├── keyvault/       # Key Vault with access policies
│       ├── monitoring/     # App Insights + Log Analytics
│       └── storage/        # References Carlos's existing ADLS account
│
├── pipeline/           # Azure Functions ETL (currently unused — kept for future use)
│   ├── function_app.py
│   ├── host.json
│   └── requirements.txt
│
└── slides/             # Presentation deck (PptxGenJS)
    ├── build.js        # Run with node build.js to regenerate .pptx
    └── LLMaven_Pipeline.pptx
```

---

## Dashboard Tabs

| Tab | What it shows |
|---|---|
| **Overview** | Total spend, requests, tokens, error rate — KPI cards at a glance |
| **Cost Explorer** | Spend by model, team, user; monthly burn rate; Haiku what-if calculator |
| **Time Intelligence** | Hourly/daily patterns; calendar heatmap; when are researchers most active? |
| **Users** | Per-user spend and activity (all users shown as `user_001`, `user_002`, …) |
| **Cache** | Cache hit rates and $ saved from prompt caching |
| **Sessions** | Multi-turn conversations grouped by session ID |
| **Ask the Data** | Natural language Q&A powered by Claude |

---

## Privacy & Anonymization

No PII is ever shown on the dashboard. All real user identifiers are replaced before display:

| Raw value | Dashboard shows |
|---|---|
| `researcher@uw.edu` | `user_001` |
| `abc-session-xyz` | `sess_0001` |
| `req-12345-abc` | `req_00001` |

The same user always maps to the same anonymous ID, so per-user patterns are preserved.

**Reversing anonymization (admins only):**

```bash
az keyvault secret show \
  --vault-name llmaven-prod-kv-141w \
  --name user-anonymization-map \
  --query value -o tsv
```

This returns a JSON object mapping `user_001 → real@email.com` for all known users.

---

## Local Development

### Dashboard

```bash
cd dashboard
pip install -r requirements.txt

# Set env var (or create .env)
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."
export ADLS_CONTAINER="litellm-logs"

streamlit run app.py
```

Without `AZURE_STORAGE_CONNECTION_STRING` set, the dashboard falls back to **demo data** automatically.

### Building and pushing the Docker image

```bash
# Build
docker build -t llmaven-dashboard ./dashboard

# Tag and push to ACR
az acr login --name llmavenprodacr141w
docker tag llmaven-dashboard llmavenprodacr141w.azurecr.io/llmaven-dashboard:latest
docker push llmavenprodacr141w.azurecr.io/llmaven-dashboard:latest

# Restart the App Service to pull the new image
az webapp restart --name llmaven-prod-streamlit --resource-group llmaven-prod-rg
```

---

## Infrastructure (Terraform)

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

terraform init
terraform plan
terraform apply
```

**What gets created:** App Service Plan, Streamlit App Service, Container Registry, Key Vault, App Insights, Log Analytics Workspace.

**What it reuses:** Carlos's existing ADLS Gen2 storage account (`llmavenissprodwestst`).

---

## Presenting the slides

The `slides/` folder contains a PptxGenJS build script. To regenerate:

```bash
cd slides
npm install
node build.js
# → LLMaven_Pipeline.pptx
```
