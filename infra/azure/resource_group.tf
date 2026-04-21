# ── Resource Group ────────────────────────────────────────────────────────

resource "azurerm_resource_group" "agent" {
  name     = "rg-${local.name_prefix}"
  location = var.location
  tags     = local.common_tags
}
