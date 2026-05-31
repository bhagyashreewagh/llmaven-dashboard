# LLMoxie Analytics Pipeline

> Understand how LLMs are actually used in research software engineering.

LiteLLM logs every API call as a JSON file, Azure Data Lake Storage holds the data, and the Streamlit dashboard reads everything, anonymizes PII, and refreshes every 5 minutes.

```
LiteLLM Proxy  ->  Azure Data Lake Storage  ->  Streamlit Dashboard
(logs .json)       (litellm-logs container)     (reads + anonymizes)
```

**Live dashboard:** https://llmaven-prod-streamlit.azurewebsites.net

---

## Why we built this

The primary motivation is to leverage logged LLM usage data to better understand how LLMs are used in research software engineering. Beyond raw logs, this pipeline provides:

- **Proper sessions** — group individual requests into conversations instead of isolated calls
- **Anonymized data** — real identities replaced with consistent `user_001`, `user_002`, ... IDs; reversible by admins via Key Vault
- **Dashboard + querying** — 6 analytics views covering cost, usage, sessions, and AI Q&A
- **Fine-tuning datasets** — export anonymized session data in training format *(coming soon)*
- **Tool/skill/MCP evaluation** — understand which tools and MCP servers researchers rely on *(coming soon)*

---

## Architecture

```
+-----------------+     one .json    +------------------------------+
|  LiteLLM Proxy  | -------------->  |  Azure Data Lake Storage     |
|                 |  per API call    |  Container: litellm-logs     |
+-----------------+                  |  Path: logs/YYYY/MM/DD/<id>  |
                                     +--------------+---------------+
                                                    |  reads all blobs
                                                    v
                                     +------------------------------+
                                     |  Streamlit Dashboard         |
                                     |  Azure App Service (B2)      |
                                     |  Docker: llmaven-dashboard   |
                                     |  Refreshes every 5 min       |
                                     +------------------------------+
```

### Azure Resources

| Resource | Name | Purpose |
|---|---|---|
| App Service Plan | `llmaven-prod-apps-plan` | Hosts Streamlit container |
| App Service (Streamlit) | `llmaven-prod-streamlit` | Dashboard |
| Container Registry | `llmavenprodacr141w` | Docker image storage |
| Key Vault | `llmaven-prod-kv-141w` | Connection string + anonymization map |
| App Insights | `llmaven-prod-ai` | Dashboard logs/monitoring |
| Storage Account | `llmavenissprodwestst` | ADLS Gen2, LiteLLM logs |

---

## Repository Structure

```
llmaven/
+-- dashboard/          # Streamlit app (deployed to Azure App Service)
|   +-- app.py          # Main app: tab router
|   +-- data.py         # Data loader: reads from ADLS, anonymizes PII
|   +-- config.py       # Color palette, constants
|   +-- styles.py       # CSS + Plotly theme
|   +-- utils.py        # Formatting helpers
|   +-- tabs/           # One file per dashboard tab
|   +-- requirements.txt
|   +-- Dockerfile
|
+-- infra/              # Terraform: provisions all Azure resources
|   +-- main.tf
|   +-- variables.tf
|   +-- outputs.tf
|   +-- providers.tf
|   +-- terraform.tfvars.example   <- copy to terraform.tfvars and fill in
|   +-- modules/
|       +-- app_services/   # ACR + App Service Plan + Streamlit web app
|       +-- keyvault/       # Key Vault with access policies
|       +-- monitoring/     # App Insights + Log Analytics
|       +-- storage/        # References existing ADLS account
|
+-- pipeline/           # Azure Functions ETL (kept for future use)
|   +-- function_app.py
|   +-- host.json
|   +-- requirements.txt
|
+-- slides/             # Presentation deck (PptxGenJS)
    +-- build.js        # Run: node build.js
    +-- LLMoxie_Pipeline.pptx
```

---

## Dashboard Tabs

| Tab | What it shows |
|---|---|
| **Overview** | Total spend, requests, tokens, error rate |
| **Cost Explorer** | Spend by model, team, user; monthly burn rate; model comparison |
| **Time Intelligence** | Hourly/daily patterns; calendar heatmap |
| **Users** | Per-user spend and activity (all users shown as `user_001`, `user_002`, ...) |
| **Sessions** | Multi-turn conversations grouped by session ID |
| **Ask the Data** | Natural language Q&A powered by Claude |

---

## Privacy and Anonymization

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

This returns a JSON object mapping `user_001 -> real@email.com` for all known users.

---

## Local Development

### Dashboard

```bash
cd dashboard
pip install -r requirements.txt

# Set env vars (or create a .env file in dashboard/)
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."
export ADLS_CONTAINER="litellm-logs"
export ANTHROPIC_API_KEY="sk-ant-..."   # needed for Ask the Data tab

streamlit run app.py
```

Without `AZURE_STORAGE_CONNECTION_STRING` set, the dashboard falls back to demo data automatically.

Without `ANTHROPIC_API_KEY` set, the first five tabs work normally — only the **Ask the Data** tab is disabled.

### Enabling Ask the Data on the deployed dashboard

The **Ask the Data** tab requires an Anthropic API key. Use a **team or project key** — not a personal one — so queries are billed to the right account.

```bash
az webapp config appsettings set \
  --name llmaven-prod-streamlit \
  --resource-group llmaven-prod-rg \
  --settings ANTHROPIC_API_KEY="sk-ant-..."
```

No rebuild or restart needed — App Service picks up new settings within ~30 seconds.

To verify it's set (shows the name only, never the value):
```bash
az webapp config appsettings list \
  --name llmaven-prod-streamlit \
  --resource-group llmaven-prod-rg \
  --query "[?name=='ANTHROPIC_API_KEY'].name" -o tsv
```

---

### Building and pushing the Docker image

```bash
# Build (--platform linux/amd64 required — Azure App Service runs AMD64, not ARM)
docker build --platform linux/amd64 -t llmaven-dashboard ./dashboard

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

**What it reuses:** Existing ADLS Gen2 storage account where LiteLLM writes logs.

---

## Regenerating the slides

```bash
cd slides
npm install
node build.js
# -> LLMoxie_Pipeline.pptx
```
