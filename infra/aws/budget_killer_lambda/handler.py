"""
Budget Killer Lambda — Emergency cost control for ai-agent.

Triggered via SNS when AWS Budget exceeds the threshold.
Finds all resources tagged with project=ai-agent and shuts them down.
"""

import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

PROJECT_NAME = os.environ.get("PROJECT_NAME", "ai-agent")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
REGION = os.environ.get("AWS_REGION_", "eu-west-1")


def lambda_handler(event: dict, context: object) -> dict:
    """SNS-triggered handler that kills all project resources."""
    logger.info("🚨 Budget killer triggered! Event: %s", json.dumps(event))

    prefix = f"{PROJECT_NAME}-{ENVIRONMENT}"
    killed: list[str] = []

    killed.extend(_kill_ecs(prefix))
    killed.extend(_kill_dynamodb(prefix))

    summary = {
        "status": "resources_killed",
        "project_name": PROJECT_NAME,
        "environment": ENVIRONMENT,
        "killed_count": len(killed),
        "killed_resources": killed,
    }
    logger.info("💀 Kill summary: %s", json.dumps(summary))
    return summary


def _kill_ecs(prefix: str) -> list[str]:
    """Scale all ECS services to 0."""
    killed = []
    ecs = boto3.client("ecs", region_name=REGION)
    try:
        for cluster_arn in ecs.list_clusters()["clusterArns"]:
            if prefix not in cluster_arn:
                continue
            for svc in ecs.list_services(cluster=cluster_arn)["serviceArns"]:
                ecs.update_service(cluster=cluster_arn, service=svc, desiredCount=0)
                killed.append(f"ecs:scaled-to-0:{svc}")
    except Exception:
        logger.exception("Error killing ECS")
    return killed


def _kill_dynamodb(prefix: str) -> list[str]:
    """Delete DynamoDB tables matching prefix."""
    killed = []
    ddb = boto3.client("dynamodb", region_name=REGION)
    try:
        for table in ddb.list_tables()["TableNames"]:
            if prefix in table:
                ddb.delete_table(TableName=table)
                killed.append(f"dynamodb:deleted:{table}")
    except Exception:
        logger.exception("Error killing DynamoDB")
    return killed
