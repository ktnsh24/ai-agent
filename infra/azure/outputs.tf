# ── Outputs ───────────────────────────────────────────────────────────────

output "container_app_url" {
  value       = azurerm_container_app.agent.latest_revision_fqdn
  description = "Container App URL"
}
