# ── Log Analytics & Container App Environment ─────────────────────────────

resource "azurerm_log_analytics_workspace" "agent" {
  name                = "law-${local.name_prefix}"
  location            = azurerm_resource_group.agent.location
  resource_group_name = azurerm_resource_group.agent.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.common_tags
}

resource "azurerm_container_app_environment" "agent" {
  name                       = "cae-${local.name_prefix}"
  location                   = azurerm_resource_group.agent.location
  resource_group_name        = azurerm_resource_group.agent.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.agent.id
  tags                       = local.common_tags
}

# ── Container App ─────────────────────────────────────────────────────────

resource "azurerm_container_app" "agent" {
  name                         = "ca-${local.name_prefix}"
  container_app_environment_id = azurerm_container_app_environment.agent.id
  resource_group_name          = azurerm_resource_group.agent.name
  revision_mode                = "Single"
  tags                         = local.common_tags

  template {
    container {
      name   = "agent"
      image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "CLOUD_PROVIDER"
        value = "azure"
      }

      env {
        name  = "APP_ENVIRONMENT"
        value = var.environment
      }
    }

    min_replicas = 0
    max_replicas = 3
  }

  ingress {
    external_enabled = true
    target_port      = 8200

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}
