locals {
  use_existing = var.existing_storage_account_name != ""
}

data "azurerm_storage_account" "existing" {
  count               = local.use_existing ? 1 : 0
  name                = var.existing_storage_account_name
  resource_group_name = var.existing_storage_account_rg != "" ? var.existing_storage_account_rg : var.resource_group_name
}

resource "azurerm_storage_account" "adls" {
  count                    = local.use_existing ? 0 : 1
  name                     = "${replace(var.prefix, "-", "")}${var.suffix}st"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  is_hns_enabled           = true

  blob_properties {
    versioning_enabled  = true
    change_feed_enabled = true
  }

  tags = var.tags
}

locals {
  id                = local.use_existing ? data.azurerm_storage_account.existing[0].id                : azurerm_storage_account.adls[0].id
  name              = local.use_existing ? data.azurerm_storage_account.existing[0].name              : azurerm_storage_account.adls[0].name
  connection_string = local.use_existing ? data.azurerm_storage_account.existing[0].primary_connection_string : azurerm_storage_account.adls[0].primary_connection_string
  dfs_endpoint      = local.use_existing ? data.azurerm_storage_account.existing[0].primary_dfs_endpoint      : azurerm_storage_account.adls[0].primary_dfs_endpoint
}

resource "azurerm_storage_data_lake_gen2_filesystem" "container" {
  name               = var.adls_container_name
  storage_account_id = local.id
}

resource "azurerm_storage_data_lake_gen2_path" "raw" {
  path               = "raw"
  filesystem_name    = azurerm_storage_data_lake_gen2_filesystem.container.name
  storage_account_id = local.id
  resource           = "directory"
}

resource "azurerm_storage_data_lake_gen2_path" "processed" {
  path               = "processed"
  filesystem_name    = azurerm_storage_data_lake_gen2_filesystem.container.name
  storage_account_id = local.id
  resource           = "directory"
}

resource "azurerm_storage_data_lake_gen2_path" "checkpoints" {
  path               = "checkpoints"
  filesystem_name    = azurerm_storage_data_lake_gen2_filesystem.container.name
  storage_account_id = local.id
  resource           = "directory"
}

# Separate storage account for Azure Functions internal use
resource "azurerm_storage_account" "functions" {
  name                     = "${replace(var.prefix, "-", "")}fn${var.suffix}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = var.tags
}
