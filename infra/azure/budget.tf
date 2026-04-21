# =============================================================================
# Cost Controller — Azure Budget Guard (€5 kill switch)
# =============================================================================

resource "azurerm_automation_account" "budget_killer" {
  name                = "${local.name_prefix}-budget-killer"
  location            = azurerm_resource_group.agent.location
  resource_group_name = azurerm_resource_group.agent.name
  sku_name            = "Basic"
  tags                = local.common_tags
}

resource "azurerm_automation_runbook" "kill_resources" {
  name                    = "${local.name_prefix}-kill-resources"
  location                = azurerm_resource_group.agent.location
  resource_group_name     = azurerm_resource_group.agent.name
  automation_account_name = azurerm_automation_account.budget_killer.name
  log_verbose             = true
  log_progress            = true
  runbook_type            = "PowerShell"

  content = <<-POWERSHELL
    param([string]$ResourceGroupName = "${azurerm_resource_group.agent.name}")
    Write-Output "🚨 Budget exceeded! Killing all resources in: $ResourceGroupName"
    Connect-AzAccount -Identity
    $resources = Get-AzResource -ResourceGroupName $ResourceGroupName
    Write-Output "Found $($resources.Count) resources to delete"
    foreach ($resource in ($resources | Sort-Object -Property ResourceType -Descending)) {
        try {
            Remove-AzResource -ResourceId $resource.ResourceId -Force
            Write-Output "  ✅ Deleted: $($resource.Name)"
        } catch {
            Write-Output "  ⚠️ Failed: $($resource.Name): $_"
        }
    }
    Write-Output "💀 Budget kill complete"
  POWERSHELL

  tags = local.common_tags
}

resource "azurerm_monitor_action_group" "budget_kill" {
  name                = "${local.name_prefix}-budget-kill"
  resource_group_name = azurerm_resource_group.agent.name
  short_name          = "budgetkill"

  email_receiver {
    name          = "budget-alert-email"
    email_address = var.alert_email
  }

  automation_runbook_receiver {
    name                    = "kill-resources"
    automation_account_id   = azurerm_automation_account.budget_killer.id
    runbook_name            = azurerm_automation_runbook.kill_resources.name
    webhook_resource_id     = azurerm_automation_account.budget_killer.id
    is_global_runbook       = false
    service_uri             = "https://s1events.azure-automation.net"
    use_common_alert_schema = true
  }
}

resource "azurerm_consumption_budget_resource_group" "cost_limit" {
  name              = "${local.name_prefix}-cost-limit"
  resource_group_id = azurerm_resource_group.agent.id

  amount     = var.cost_limit_eur
  time_grain = "Monthly"

  time_period {
    start_date = formatdate("YYYY-MM-01'T'00:00:00Z", timestamp())
  }

  notification {
    enabled        = true
    threshold      = 80
    threshold_type = "Actual"
    operator       = "GreaterThan"
    contact_emails = [var.alert_email]
  }

  notification {
    enabled        = true
    threshold      = 100
    threshold_type = "Actual"
    operator       = "GreaterThan"
    contact_emails  = [var.alert_email]
    contact_groups = [azurerm_monitor_action_group.budget_kill.id]
  }

  lifecycle {
    ignore_changes = [time_period]
  }
}
