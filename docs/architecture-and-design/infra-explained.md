# Infrastructure (Terraform) — Deep Dive

> `infra/aws/` and `infra/azure/` — every cloud resource the agent needs, defined as Terraform HCL. Two parallel module trees (one per cloud) plus a cost-guard pattern that alerts when a monthly budget cap is approached.

> **Related docs:**
>
> - [Terraform Guide](../setup-and-tooling/terraform-guide.md) — `terraform init/plan/apply/destroy` runbook
> - [CI/CD Explained](cicd-explained.md) — the GitHub Actions pipelines that drive these modules
> - [Architecture Overview](architecture.md) — what the application expects from the infra
> - [Cost Analysis](../ai-engineering/cost-analysis.md) — projected unit pricing per resource
> - [Monitoring](../reference/monitoring.md) — what observability runs on top of these resources

---

## Table of Contents

- [What's in infra/](#whats-in-infra)
- [Terraform Layout](#terraform-layout)
- [AWS Resources](#aws-resources)
- [Azure Resources](#azure-resources)
- [Apply / Destroy Flow](#apply--destroy-flow)
- [Cost Guardrails](#cost-guardrails)
- [Design Decisions](#design-decisions)
- [Courier Explainer](#courier-explainer)

---

## What's in infra/

```
infra/
├── aws/                       # AWS module — applied with `cd infra/aws && terraform apply`
│   ├── networking.tf          # VPC 10.1.0.0/16, public subnet 10.1.1.0/24, IGW, route table
│   ├── security_groups.tf     # Ingress port 8200 from 0.0.0.0/0, all egress open
│   ├── ecr.tf                 # ECR repository `ai-agent`
│   ├── ecs.tf                 # ECS cluster (Container Insights), Fargate task (512 CPU / 1024 MiB), service
│   ├── iam.tf                 # ECS execution role + ECS task role
│   ├── cloudwatch.tf          # Log group `/ecs/{name_prefix}`, 30-day retention
│   ├── budget.tf              # AWS Budget (EUR 5 default), SNS alert at 80% + 100%
│   └── outputs.tf             # ecs_cluster_name, ecr_repository_url, service public IP
│
└── azure/                     # Azure module — applied with `cd infra/azure && terraform apply`
    ├── resource_group.tf      # rg-${prefix}
    ├── container_app.tf       # Container App Environment + Container App
    ├── budget.tf              # Consumption Budget + alert actions
    └── outputs.tf
```

The two trees deliberately mirror each other: a container runtime, an image registry, IAM/identity, a log stream, and a budget guard. Either cloud can be applied or destroyed independently.

- 🚚 **Courier:** Two parallel sets of infrastructure blueprints — one for the AWS depot, one for the Azure hub — drawn so closely that any new wing on the AWS side has a matching wing on the Azure side.

---

## Terraform Layout

| File | Purpose | 🚚 Courier |
|------|---------|-----------|
| `networking.tf` | VPC, subnet, internet gateway, route table | The road network connecting the depot to the outside world — one public lane, one entrance point. |
| `security_groups.tf` | Front-door firewall rules (port 8200 open, all egress) | Front-door bouncer rules — the dispatch window is open to the world on port 8200; couriers can leave by any door. |
| `ecr.tf` | ECR repository storing Docker images | Locker room where every new dispatch-desk uniform is hung before ECS pulls it into service. |
| `ecs.tf` | Cluster, task definition, service | The hiring contract for the dispatch crew — cluster name, resource allocation, and how many couriers to keep on shift. |
| `iam.tf` | Execution role (ECR + CloudWatch) and task role | Two sets of keys — one for the janitor opening the locker room and log shed, one for the courier's actual work badge. |
| `cloudwatch.tf` | Log group and retention policy | The log shed — every depot voice memo is filed here for thirty days then shredded automatically. |
| `budget.tf` | AWS Budget + SNS topic, alert at 80% and 100% | Owner's monthly fuel-budget alarm — chimes early at 80% so the depot hand can investigate calmly. |
| `outputs.tf` | Exposes cluster name, ECR URL, and service details | Index card pinned at the door listing the new addresses for every cable and pipe the dispatch desk needs. |

---

## AWS Resources

| Resource | Type | Sizing | Purpose | 🚚 Courier |
|----------|------|--------|---------|-----------|
| VPC | `aws_vpc` | `10.1.0.0/16` | Isolated network for all resources | The fenced depot yard — all lanes and wings live inside this boundary. |
| Public subnet | `aws_subnet` | `10.1.1.0/24` in `{region}a` | Subnet where the ECS task receives a public IP | The lane from the fence gate to the dispatch desk — publicly reachable. |
| Internet gateway + route table | `aws_internet_gateway`, `aws_route_table` | — | Routes internet traffic into the VPC | The road sign pointing outside traffic to the depot gate. |
| Security group | `aws_security_group` | Inbound `0.0.0.0/0:8200`, all egress | Firewall on the ECS task | Front-door bouncer — opens the dispatch window to the world, lets couriers roam anywhere outbound. |
| ECS cluster | `aws_ecs_cluster` | Container Insights enabled | Hosts the Fargate task running the agent image | Front-yard plot where the dispatch shed actually stands and the couriers start their shifts. |
| ECS task definition | `aws_ecs_task_definition` | 512 CPU, 1024 MiB, port 8200, ECR `ai-agent:latest` | Defines the agent container and its environment | Hiring contract for the dispatch crew — staff size, shift length, and the front door they answer at. |
| ECS service | `aws_ecs_service` | `desired_count=1`, FARGATE, public IP assigned | Keeps one task running; replaces it on failure | Permanent shift schedule — one courier always on duty, auto-replaced if they disappear. |
| ECR repository | `aws_ecr_repository` | `ai-agent` | Stores Docker images pushed by CI | Locker room where every new dispatch-desk uniform is hung; CI hangs one before ECS pulls it. |
| CloudWatch log group | `aws_cloudwatch_log_group` | `/ecs/{name_prefix}`, 30-day retention | Container stdout/stderr destination | The log shed — every dispatcher's voice memo is filed here for thirty days then shredded automatically. |
| IAM execution role | `aws_iam_role` | `AmazonECSTaskExecutionRolePolicy` | Lets ECS pull from ECR + ship logs to CloudWatch | Janitor's keys — opens the locker room and the log shed, nothing more. |
| IAM task role | `aws_iam_role` | Inline policies for LLM provider access | Lets the running container call the configured LLM provider | Courier's parcel pass — the only badge that grants access to the remote LLM depot. |
| AWS Budget | `aws_budgets_budget` | EUR 5 default, tag-filtered | Triggers SNS at 80% + 100% of the cap | Budget owner's monthly fuel-budget alarm — quietly chimes at 80%, screams at 100%. |

**No ALB / load balancer.** The ECS task is directly accessible via its assigned public IP. This is an intentional dev/stg cost-saving choice — an ALB adds ~$16/month for a single-task service. For production, add an ALB and move the task into a private subnet.

---

## Azure Resources

| Resource | Type | Purpose | 🚚 Courier |
|----------|------|---------|-----------|
| Resource group | `azurerm_resource_group` | Container for every other Azure resource | Plot of land the Azure depot is built on — every wing must sit inside this fenced area. |
| Container App Environment | `azurerm_container_app_environment` | Multi-tenant runtime for the container app | Shared dispatch-shed compound where multiple stables can co-exist on the same yard. |
| Container App | `azurerm_container_app` | Runs the agent image, single revision | Hiring contract for the Azure-side dispatch crew, with a single live shift schedule per deploy. |
| Consumption Budget | `azurerm_consumption_budget_resource_group` | Watches the resource group's spend, default EUR 5 | Azure-side fuel-budget alarm scoped to this single fenced plot. |

---

## Apply / Destroy Flow

```
Operator clones repo, picks a cloud, exports vars
    │
    ▼
cd infra/aws    (or infra/azure)
    │
    ▼
terraform init                 (downloads provider + state)
terraform plan -out plan.bin   (reads current state → diff vs HCL)
terraform apply plan.bin       (creates/updates resources)
    │
    ▼
outputs printed — agent is reachable on the public IP:8200
    │
    ▼ (when the lab is over)
terraform destroy              (deletes everything the module owns)
```

The CI pipelines (`deploy-aws.yml`, `deploy-azure.yml`) run the same three commands inside a short-lived runner, with credentials sourced from the GitHub environment via OIDC. No long-lived cloud keys are stored in CI.

---

## Cost Guardrails

| Layer | Mechanism | Effective behaviour | 🚚 Courier |
|-------|-----------|---------------------|-----------|
| Sizing | 512 CPU / 1024 MiB Fargate, `desired_count=1` | Smallest Fargate allocation; one task only | Smallest stall you can rent at the depot — enough room for a single courier, no luxury pasture. |
| No ALB | Public IP assigned directly to task | Avoids ~$16/month fixed ALB cost | Dev/stg only shortcut — the dispatch desk answers the door directly, no front-gate guard hired. |
| Log retention | 30-day CloudWatch retention | Prevents log storage from compounding | Log shed auto-shreds after a month — old voice memos don't pile up and inflate the bill. |
| Budget alert | AWS Budget / Azure Consumption Budget, default EUR 5 | Notification at 80% and 100% | Owner's wall-clock alarm — chimes early at 80% so the depot hand can investigate before it hits the cap. |

---

## Design Decisions

**Why no ALB?** The agent is a dev/stg lab service with a single task and a single caller (a developer or a lab script). Adding an ALB triples the fixed monthly cost for no real benefit at this scale. The trade-off is that the public IP changes on each new task deployment — callers should use the ECS service's task IP from `terraform output`, not a stable DNS name.

**Why a public subnet?** To reach Ollama or external LLM APIs, the Fargate task needs outbound internet access. A private subnet would require a NAT gateway (~$32/month), which exceeds the €5 budget cap immediately. For production, move to a private subnet with NAT or VPC endpoints.

**Why local Terraform state?** The backend block is intentionally left as local state for the lab. Flip it to an S3 + DynamoDB backend before using this module in a shared team environment.

---

## 🚚 Courier Explainer

`infra/` is the **set of infrastructure blueprints**, not the depot itself. Two complete blueprint folders sit side by side — one labelled "AWS depot", one labelled "Azure hub" — and either can be raised, demolished, or rebuilt independently with a single `terraform apply` / `terraform destroy`.

The AWS blueprint is deliberately lean: one public lane, one dispatch shed (ECS Fargate), one image locker room (ECR), and a log shed (CloudWatch). There is no front-gate guard (no ALB) — the dispatch window answers directly on port 8200 from a public IP. That keeps the monthly blueprint cost well under €5, which is the budget cap the `budget.tf` watches.

When the 80% alarm fires, the depot hand gets a notification to investigate. At 100%, a further notification fires — the operator is expected to run `terraform destroy` manually to avoid overspend.
