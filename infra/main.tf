locals {
  prefix = "${var.project}-${var.environment}"
  tags = {
    project     = var.project
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "azurerm_resource_group" "main" {
  name     = "${local.prefix}-rg"
  location = var.location
  tags     = local.tags
}

resource "random_string" "suffix" {
  length  = 4
  special = false
  upper   = false
}

# ── Modules ───────────────────────────────────────────────────────────────────

module "storage" {
  source = "./modules/storage"

  prefix                        = local.prefix
  location                      = azurerm_resource_group.main.location
  resource_group_name           = azurerm_resource_group.main.name
  suffix                        = random_string.suffix.result
  adls_container_name           = var.adls_container_name
  existing_storage_account_name = var.existing_storage_account_name
  existing_storage_account_rg   = var.existing_storage_account_rg
  tags                          = local.tags
}

module "monitoring" {
  source = "./modules/monitoring"

  prefix              = local.prefix
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.tags
}

module "app_services" {
  source = "./modules/app_services"

  prefix                 = local.prefix
  location               = azurerm_resource_group.main.location
  resource_group_name    = azurerm_resource_group.main.name
  suffix                 = random_string.suffix.result
  tags                   = local.tags
  sku                    = var.app_service_sku
  adls_connection_string = module.storage.connection_string
  adls_container        = "litellm-logs"
  app_insights_key       = module.monitoring.instrumentation_key
  streamlit_image_tag    = var.streamlit_image_tag
}

module "keyvault" {
  source = "./modules/keyvault"

  prefix                 = local.prefix
  location               = azurerm_resource_group.main.location
  resource_group_name    = azurerm_resource_group.main.name
  suffix                 = random_string.suffix.result
  tags                   = local.tags
  tenant_id              = var.tenant_id
  current_user_object_id = var.current_user_object_id
  adls_connection_string = module.storage.connection_string
  streamlit_principal_id = module.app_services.streamlit_principal_id
}
