# Getting Started — AI Agent

> **Time to first agent response:** ~5 minutes (local) | ~20 minutes (cloud deployment)

---

## Table of Contents

- [What you need before starting](#what-you-need-before-starting)
- [Step 1 — Install Python 3.12](#step-1--install-python-312)
- [Step 2 — Install Poetry](#step-2--install-poetry)
- [Step 3 — Clone and install dependencies](#step-3--clone-and-install-dependencies)
- [Step 4 — Configure environment variables](#step-4--configure-environment-variables)
- [Step 5 — Start the agent (local)](#step-5--start-the-agent-local)
- [Step 6 — Test the Agent](#step-6--test-the-agent)
- [Step 7 — Run Labs Locally](#step-7--run-labs-locally)
- [Step 8 — Connect to AWS (and run on AWS)](#step-8--connect-to-aws-and-run-on-aws)
- [Step 9 — Connect to Azure (and run on Azure)](#step-9--connect-to-azure-and-run-on-azure)
- [Step 10 — Run the Tests](#step-10--run-the-tests)
- [Step 11 — Project Structure](#step-11--project-structure)
- [Troubleshooting](#troubleshooting)

---

## What you need before starting

| Tool | Version | Why you need it |
| --- | --- | --- |
| **Python** | 3.12+ | The agent is written in Python |
| **Poetry** | 1.8+ | Package manager (manages dependencies + virtual environment) |
| **Git** | 2.40+ | Version control |
| **Ollama** | Latest | Local LLM (for `CLOUD_PROVIDER=local`) |
| **AWS CLI** | 2.x | Connect to AWS services (optional) |
| **Azure CLI** | 2.x | Connect to Azure services (optional) |
| **Terraform** | 1.5+ | Deploy cloud infrastructure (optional) |

### Check what is already installed

```bash
python3 --version      # Need 3.12+
poetry --version       # Need 1.8+
git --version          # Need 2.40+
ollama --version       # Need latest
aws --version          # Optional
az --version           # Optional
terraform --version    # Optional
```

---

## Step 1 — Install Python 3.12

```bash
# Ubuntu / WSL
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# Verify
python3.12 --version
```

---

## Step 2 — Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH (add to ~/.bashrc for persistence)
export PATH="$HOME/.local/bin:$PATH"

# Verify
poetry --version

# Configure Poetry to create virtualenvs inside the project
poetry config virtualenvs.in-project true
```

---

## Step 3 — Clone and install dependencies

```bash
cd repos/ai-agent

# Install dependencies
poetry install

# Verify the virtual environment
poetry env info
```

---

## Step 4 — Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with these key settings:

| Variable | Default | Description |
| --- | --- | --- |
| `CLOUD_PROVIDER` | `local` | LLM provider: `aws`, `azure`, `local` |
| `APP_PORT` | `8200` | Server port |
| `LLM_TEMPERATURE` | `0.3` | Default model temperature |
| `LLM_MAX_TOKENS` | `2048` | Maximum tokens for LLM response |
| `AGENT_MAX_ITERATIONS` | `10` | Maximum iterations for agent tool loop |
| `TOOL_WEB_SEARCH_ENABLED` | `true` | Enable web search tool |
| `TOOL_CALCULATOR_ENABLED` | `true` | Enable calculator tool |
| `TOOL_DATABASE_QUERY_ENABLED` | `true` | Enable database query tool |
| `MCP_ENABLED` | `false` | Connect to MCP Server (Phase 4) |

**Local provider settings (default — works out of the box):**

```bash
CLOUD_PROVIDER=local
# Ollama is auto-detected at http://localhost:11434
```

**AWS provider settings:**

```bash
CLOUD_PROVIDER=aws
AWS_REGION=eu-west-1
# Bedrock access required (see Step 8)
```

**Azure provider settings:**

```bash
CLOUD_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01
```

---

## Step 5 — Start the agent (local)

### Install Ollama and pull models

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull required model
ollama pull llama3.2    # LLM (~2 GB)

# Verify
ollama list
```

### Start the agent

```bash
poetry run start
# → http://localhost:8200
# → Swagger UI at http://localhost:8200/docs
```

---

## Step 6 — Test the Agent

### Simple chat (no tools needed)

```bash
curl -X POST http://localhost:8200/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?"}'
```

### Calculator tool

```bash
curl -X POST http://localhost:8200/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the square root of 256 multiplied by 3?"}'
```

### Database query tool

```bash
curl -X POST http://localhost:8200/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many electronics products are in the database?"}'
```

### List available tools

```bash
curl http://localhost:8200/v1/tools | jq
```

### Health check

```bash
curl http://localhost:8200/health | jq
```

### Conversation continuity

```bash
# Start a conversation
RESPONSE=$(curl -s -X POST http://localhost:8200/v1/chat \
  -d '{"message": "Remember that my name is Alex."}')
CONV_ID=$(echo $RESPONSE | jq -r '.conversation_id')

# Continue the conversation
curl -X POST http://localhost:8200/v1/chat \
  -d "{\"message\": \"What is my name?\", \"conversation_id\": \"$CONV_ID\"}"
```

### SSE Streaming

```bash
curl -N http://localhost:8200/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a joke about programming"}'
```

---

## Step 7 — Run Labs Locally

Once the agent is running locally (see [Step 5](#step-5--start-the-agent-local)), you can run all 8 hands-on labs.

**Cost: $0. No API keys needed. Runs entirely on your machine.**

### 7a. Automated (recommended)

```bash
# 1. Start the agent (in one terminal)
poetry run start

# 2. Run all labs (in another terminal)
poetry run python scripts/run_all_labs.py --env local
```

This runs all 8 hands-on labs against Ollama and prints a pass/fail report.

No infrastructure to deploy or destroy — it's all local.

**Results are saved to:** `scripts/lab_results/local/`

### 7b. Or run manually (step by step)

```bash
# Start the agent
poetry run start

# Then test manually through Swagger UI at http://localhost:8200/docs
```

**Results location:** `scripts/lab_results/local/`

> **Note:** `run_cloud_labs.sh` is for cloud deployments only (AWS/Azure). It wraps
> `terraform apply` → labs → `terraform destroy`. For local development, use
> `run_all_labs.py` directly as shown above.

### Hardware requirements

| Component | Minimum | Recommended |
| --- | --- | --- |
| **RAM** | 8 GB | 16 GB |
| **Disk** | 5 GB (for models) | 10 GB |
| **GPU** | Not required (CPU works) | NVIDIA GPU (faster inference) |

---

## Step 8 — Connect to AWS (and run on AWS)

### 8a. Install AWS CLI

```bash
# Ubuntu / WSL
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws --version
```

### 8b. Configure AWS credentials

**Option A: Access keys (simplest for personal account)**

```bash
aws configure
# AWS Access Key ID: <paste your key>
# AWS Secret Access Key: <paste your secret>
# Default region name: eu-west-1
# Default output format: json
```

Get your access keys from: AWS Console → IAM → Users → Your User → Security credentials → Create access key.

**Option B: SSO (if your account uses AWS Organizations)**

```bash
aws configure sso --profile ai-agent
# Follow the prompts for SSO start URL, region, account, role
```

### 8c. Enable Bedrock model access

Bedrock models are not enabled by default. You need to request access:

1. Go to AWS Console → Amazon Bedrock → Model access
2. Click "Manage model access"
3. Enable:
   - **Anthropic → Claude 3.5 Sonnet v2** (for LLM)
4. Wait for approval (usually instant for personal accounts)

### 8d. Verify AWS connectivity

```bash
aws sts get-caller-identity
# Should show your account ID and ARN

aws bedrock list-foundation-models --region eu-west-1 \
  --query "modelSummaries[?contains(modelId, 'claude')].[modelId]" --output table
```

### Cost-saving tips for AWS

- **Bedrock**: Pay-per-token only. No idle costs. A typical development session costs < $1.
- **DynamoDB**: Pay-per-request mode. Free tier: 25 GB + 25 WCU + 25 RCU.
- **⚠️ Always destroy after labs** — the budget guard (€5 default) is your safety net.

### 8e. Deploy and run labs (automated)

```bash
./scripts/run_cloud_labs.sh --provider aws --email you@example.com
```

The script automatically:

1. `terraform apply` — deploys ECS, DynamoDB, and a budget guard
2. Starts the agent with `CLOUD_PROVIDER=aws`
3. Runs all 8 hands-on labs against AWS
4. Prints a pass/fail completion report
5. `terraform destroy` — tears down ALL infrastructure (even on Ctrl+C or errors)

**Budget control:** The default budget limit is €5. To increase it:

```bash
./scripts/run_cloud_labs.sh --provider aws --email you@example.com --cost-limit 15
```

**Results are saved to:** `scripts/lab_results/aws/`

### 8f. Or deploy and run manually (step by step)

```bash
# 1. Deploy infrastructure
cd infra/aws
terraform init
terraform apply -var="cost_limit_eur=5" -var="alert_email=you@example.com"

# 2. Set CLOUD_PROVIDER=aws in .env (see Step 4)

# 3. Start the agent
cd ../..  # back to repo root
poetry run start

# 4. Run labs automatically (in another terminal)
poetry run python scripts/run_all_labs.py --env aws

# OR — test manually through Swagger UI at http://localhost:8200/docs

# 5. ALWAYS destroy when done
cd infra/aws
terraform destroy -var="cost_limit_eur=5" -var="alert_email=you@example.com"
```

> ⚠️ **CAUTION — Manual mode means manual cleanup!** When running manually, there
> is no automatic `terraform destroy` on exit. Monitor your costs in the
> [AWS Billing Console](https://console.aws.amazon.com/billing/)
> and **always run `terraform destroy` when finished.**

**Results location:** `scripts/lab_results/aws/`

---

## Step 9 — Connect to Azure (and run on Azure)

### 9a. Install Azure CLI

```bash
# Ubuntu / WSL
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az --version
```

### 9b. Login to Azure

```bash
az login
# Opens a browser — sign in with your Azure account

# Set the active subscription (if you have multiple)
az account set --subscription "your-subscription-id"
```

### 9c. Create Azure OpenAI resource

1. Go to Azure Portal → Create a resource → "Azure OpenAI"
2. Select your subscription and resource group
3. Region: **West Europe** (cheapest in EU)
4. Pricing tier: **Standard S0**
5. After creation, go to the resource → Keys and Endpoint
6. Copy the **Endpoint** and **Key 1** to your `.env` file

### 9d. Deploy models in Azure OpenAI

1. Go to Azure AI Studio (<https://ai.azure.com>)
2. Select your Azure OpenAI resource
3. Go to Deployments → Create deployment
4. Deploy:
   - **gpt-4o** — deployment name: `gpt-4o`

### 9e. Verify Azure connectivity

```bash
az account show
# Should show your subscription

curl -X POST "https://your-resource.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-01" \
  -H "api-key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}], "max_tokens": 10}'
```

### Cost-saving tips for Azure

- **Azure OpenAI**: Pay-per-token. Development costs < $1/day.
- **⚠️ Always destroy after labs** — the budget guard (€5 default) is your safety net.

### 9f. Deploy and run labs (automated)

```bash
./scripts/run_cloud_labs.sh --provider azure --email you@example.com
```

The script automatically:

1. `terraform apply` — deploys Container Apps, DynamoDB, and a budget guard
2. Starts the agent with `CLOUD_PROVIDER=azure`
3. Runs all 8 hands-on labs against Azure
4. Prints a pass/fail completion report
5. `terraform destroy` — tears down ALL infrastructure (even on Ctrl+C or errors)

**Budget control:**

```bash
./scripts/run_cloud_labs.sh --provider azure --email you@example.com --cost-limit 15
```

**Results are saved to:** `scripts/lab_results/azure/`

### 9g. Or deploy and run manually (step by step)

```bash
# 1. Deploy infrastructure
cd infra/azure
terraform init
terraform apply -var="cost_limit_eur=5" -var="alert_email=you@example.com"

# 2. Set CLOUD_PROVIDER=azure in .env (see Step 4)

# 3. Start the agent
cd ../..  # back to repo root
poetry run start

# 4. Run labs automatically (in another terminal)
poetry run python scripts/run_all_labs.py --env azure

# OR — test manually through Swagger UI at http://localhost:8200/docs

# 5. ALWAYS destroy when done
cd infra/azure
terraform destroy -var="cost_limit_eur=5" -var="alert_email=you@example.com"
```

> ⚠️ **CAUTION — Manual mode means manual cleanup!** When running manually, there
> is no automatic `terraform destroy` on exit. Monitor your costs in the
> [Azure Cost Management](https://portal.azure.com/#view/Microsoft_Azure_CostManagement)
> and **always run `terraform destroy` when finished.**

**Results location:** `scripts/lab_results/azure/`

---

## Step 10 — Run the Tests

```bash
# All tests
poetry run pytest tests/ -v

# With coverage
poetry run pytest tests/ -v --cov=src --cov-report=term-missing
```

---

## Step 11 — Project Structure

```text
ai-agent/
├── src/
│   ├── main.py              ← FastAPI app factory + lifespan
│   ├── config.py            ← Pydantic Settings
│   ├── models.py            ← Request/response models
│   ├── llm/
│   │   └── provider.py      ← LLM provider (Bedrock/Azure/Ollama)
│   ├── agent/
│   │   ├── graph.py         ← LangGraph agent with tool loop
│   │   └── conversation.py  ← Conversation persistence (SQLite)
│   ├── tools/
│   │   ├── registry.py      ← Tool registration and discovery
│   │   ├── web_search.py    ← Tavily or mock web search
│   │   ├── calculator.py    ← Safe math evaluator
│   │   └── database_query.py ← SQL query against sample DB
│   └── routes/
│       ├── chat.py           ← POST /v1/chat (+ SSE stream)
│       ├── conversations.py  ← Conversation CRUD
│       ├── tools.py          ← GET /v1/tools
│       └── health.py         ← GET /health
├── scripts/
│   ├── run_all_labs.py       ← 8 automated lab experiments
│   ├── run_cloud_labs.sh     ← One-command cloud deploy → run → destroy
│   └── lab_results/          ← Lab output (local/, aws/, azure/)
├── tests/
├── docs/
├── infra/
│   ├── aws/main.tf
│   └── azure/main.tf
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

---

## Troubleshooting

### Ollama not running

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags
# If not, start it:
ollama serve
```

### Port already in use

```bash
lsof -i :8200
kill -9 <PID>
poetry run start
```

### Agent stuck in tool loop

The agent has a maximum iteration limit (`AGENT_MAX_ITERATIONS=10`). If it exceeds this, it returns the best answer so far. Increase the limit in `.env` if your queries need more tool calls.

### ModuleNotFoundError

```bash
poetry install
```

### Terraform errors

```bash
cd infra/aws   # or infra/azure
terraform init -upgrade
terraform plan -var="cost_limit_eur=5" -var="alert_email=you@example.com"
```
