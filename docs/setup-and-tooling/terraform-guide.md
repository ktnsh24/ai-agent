# Terraform Guide — AI Agent

> **Platforms:** AWS (ECS Fargate, direct public IP) and Azure (Container Apps)
>
> **Files:** `infra/aws/` and `infra/azure/`

---

## Table of Contents

1. [Infrastructure Overview](#1-infrastructure-overview)
2. [AWS Architecture](#2-aws-architecture)
3. [Azure Architecture](#3-azure-architecture)
4. [Deployment](#4-deployment)
5. [Variables](#5-variables)
6. [Outputs](#6-outputs)
7. [Cost Notes](#7-cost-notes)
8. [Cross-References](#8-cross-references)

---

## 1. Infrastructure Overview

Both platforms deploy the same agent with equivalent infrastructure, kept intentionally lean:

| Component | AWS Service | Azure Service | 🚚 Courier |
|-----------|------------|---------------|-----------|
| Container runtime | ECS Fargate | Container Apps | The hired-by-the-hour depot plot — Fargate or Container Apps puts up the environment so you don't own a server. |
| Container registry | ECR | ACR | The image locker room where the packaged agent container is stored before being pulled into the live cloud. |
| Networking | VPC + public subnet | Container App Environment | The fenced yard and lane from the gate to the dispatch desk. |
| Logging | CloudWatch Logs | Container Apps log stream | The log shed that captures every agent step for 30 days. |
| IAM | IAM Roles | Managed Identity | The permission ledger deciding which container can call which cloud service. |

Unlike ai-gateway, there is **no load balancer, no Redis, and no managed database** — the agent uses a SQLite file for conversation persistence, mounted as an ECS volume.

---

## 2. AWS Architecture

### Resources Created

```
VPC (10.1.0.0/16)
└── Public Subnet (10.1.1.0/24 in {region}a)
    ├── Internet Gateway + Route Table
    ├── Security Group (inbound 8200, all egress)
    └── ECS Fargate Task (public IP assigned)
        ├── ECR Repository (ai-agent)
        ├── CloudWatch Log Group (/ecs/{name_prefix})
        └── IAM: execution role + task role
```

### Key Resources

| Resource | Type | Size | Purpose | 🚚 Courier |
|----------|------|------|---------|-----------|
| ECS Cluster | Fargate | Container Insights enabled | Hosts the agent container | The serverless container plot that launches the dispatch-desk container. |
| ECS Task | Fargate | 512 CPU / 1024 MiB, port 8200 | Runs the agent image from ECR | Hiring contract for the dispatch crew — half a vCPU, 1 GiB, one front door on port 8200. |
| ECR Repository | — | `ai-agent` | Stores Docker images | The locker room where freshly built agent uniforms are hung until ECS pulls them. |
| CloudWatch Logs | — | 30-day retention | Application logging | The 30-day log archive where every agent step is stored for debugging. |

### Security Groups

| SG | Inbound | From | 🚚 Courier |
|----|---------|------|-----------|
| Agent SG | 8200 | `0.0.0.0/0` | The dispatch window on port 8200 — open directly to the internet (dev/stg only, no ALB). |

### IAM Permissions

The ECS task execution role allows ECR pulls and CloudWatch log shipping. The ECS task role carries the LLM provider credentials needed by the running container (injected via environment variables or Secrets Manager at apply time).

---

## 3. Azure Architecture

### Resources Created

```
Resource Group (rg-ai-agent-{env})
└── Container App Environment
    └── Container App (ai-agent)
        └── Budget (EUR 5 default)
```

### Key Resources

| Resource | SKU | Purpose | 🚚 Courier |
|----------|-----|---------|-----------|
| Container App | 0.5 vCPU / 1 GiB | Runs the agent container | The Azure-side dispatch desk running at half a vCPU with 1 GiB of working memory. |
| Container App Environment | Default | Multi-tenant runtime | The shared compound where the dispatch-desk container lives on the Azure side. |

---

## 4. Deployment

### AWS Deployment

```bash
cd infra/aws

# Initialise
terraform init

# Preview changes
terraform plan \
  -var="environment=dev" \
  -var="alert_email=you@example.com"

# Apply
terraform apply \
  -var="environment=dev" \
  -var="alert_email=you@example.com"

# Build and push Docker image to ECR
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=eu-west-1
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin \
  $ACCOUNT.dkr.ecr.$REGION.amazonaws.com

docker build -t ai-agent .
docker tag ai-agent:latest \
  $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/ai-agent:latest
docker push \
  $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/ai-agent:latest

# Force new deployment (pick up the new image)
aws ecs update-service \
  --cluster ai-agent-dev \
  --service ai-agent \
  --force-new-deployment
```

### Azure Deployment

```bash
cd infra/azure

# Initialise
terraform init

# Preview changes
terraform plan \
  -var="environment=dev" \
  -var="alert_email=you@example.com"

# Apply
terraform apply \
  -var="environment=dev" \
  -var="alert_email=you@example.com"
```

### Destroying

```bash
# AWS
cd infra/aws && terraform destroy \
  -var="environment=dev" \
  -var="alert_email=you@example.com"

# Azure
cd infra/azure && terraform destroy \
  -var="environment=dev" \
  -var="alert_email=you@example.com"
```

Always destroy when finished with a lab session. The budget alert fires at 80% of €5/month — destroying manually before it fires is good practice.

---

## 5. Variables

### Required Variables (both clouds)

| Variable | Type | Description | 🚚 Courier |
|----------|------|-------------|-----------|
| `environment` | string | Deployment environment — `dev` or `stg` | The label stamped onto every resource so dev and stg never collide. |
| `alert_email` | string | Email address for budget notifications | The address where the 80% / 100% budget alarm rings. |

### Optional Variables (AWS)

| Variable | Type | Default | Description | 🚚 Courier |
|----------|------|---------|-------------|-----------|
| `aws_region` | string | `eu-west-1` | AWS deployment region | The depot location — eu-west-1 keeps European deliveries short. |
| `app_name` | string | `ai-agent` | Prefix for all resource names | The nameplate stamped on every wing of the depot. |
| `ecs_cpu` | number | `512` | ECS task CPU units | CPU tokens reserved for the dispatch-desk container. |
| `ecs_memory` | number | `1024` | ECS task memory (MiB) | Working-memory allocation for the Fargate task. |
| `cost_limit_eur` | number | `5` | Monthly budget cap in EUR | The monthly fuel-budget limit before the alarm fires. |

---

## 6. Outputs

### AWS Outputs

| Output | Description | 🚚 Courier |
|--------|-------------|-----------|
| `ecs_cluster_name` | ECS cluster name | Name of the yard where the dispatch shed stands. |
| `ecr_repository_url` | ECR URL for Docker push | The locker room address — push new uniforms here for ECS to pull. |
| `service_public_ip` | Public IP of the running ECS task | The direct front-door address to curl the agent (changes on each task replacement). |

### Azure Outputs

| Output | Description | 🚚 Courier |
|--------|-------------|-----------|
| `container_app_url` | Container App public URL | The stable front-gate address on the Azure side — use this to reach the dispatch desk. |

---

## 7. Cost Notes

| Resource | Approximate monthly cost | Note |
|----------|-------------------------|------|
| ECS Fargate (512 CPU / 1024 MiB, 1 task) | ~$8–12 | Depends on region and uptime |
| ECR repository | ~$0.50 | Storage only |
| CloudWatch Logs | ~$0.50 | At low log volume |
| **AWS total (dev)** | **~$10–13/month** | Well within €5 budget if kept running short sessions only |
| Azure Container App (0.5 vCPU) | ~$0–5 | Free tier applies for low request counts |

The €5 budget alert is set to warn before costs exceed the cap. For always-on development use, run `terraform destroy` at the end of each session.

---

## 8. Cross-References

| Topic | Document | 🚚 Courier |
|-------|----------|-----------|
| Architecture | [Architecture Overview](../architecture-and-design/architecture.md) | The master depot blueprint mapping every component from front door to conversation store. |
| Docker (local) | [Docker Compose Guide](docker-compose-guide.md) | The local Docker Compose setup for running the agent without any cloud account. |
| Getting started | [Getting Started](getting-started.md) | The on-call engineer's orientation guide from Python install to first agent request. |
| CI/CD pipeline | [CI/CD Explained](../architecture-and-design/cicd-explained.md) | The automated depot runner that builds, tests, and deploys the agent image on push. |
| Infra deep dive | [Infrastructure Explained](../architecture-and-design/infra-explained.md) | Every Terraform resource explained with sizing rationale and design decisions. |
