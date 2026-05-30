resource "azurerm_key_vault" "main" {
  name                       = "${var.prefix}-kv-${var.suffix}"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  tenant_id                  = var.tenant_id
  sku_name                   = "standard"
  purge_protection_enabled   = true
  soft_delete_retention_days = 90
  tags                       = var.tags

  # Deploying user — full secret management
  access_policy {
    tenant_id          = var.tenant_id
    object_id          = var.current_user_object_id
    secret_permissions = ["Get", "List", "Set", "Delete", "Purge", "Recover"]
  }

  # Streamlit managed identity — read only
  access_policy {
    tenant_id          = var.tenant_id
    object_id          = var.streamlit_principal_id
    secret_permissions = ["Get", "List"]
  }
}

resource "azurerm_key_vault_secret" "adls_connection" {
  name         = "adls-connection-string"
  value        = var.adls_connection_string
  key_vault_id = azurerm_key_vault.main.id
}
