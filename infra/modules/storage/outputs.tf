output "id"   { value = local.id }
output "name" { value = local.name }
output "dfs_endpoint"    { value = local.dfs_endpoint }
output "filesystem_id"   { value = azurerm_storage_data_lake_gen2_filesystem.container.id }
output "functions_account_name" { value = azurerm_storage_account.functions.name }
output "functions_account_id"   { value = azurerm_storage_account.functions.id }

output "connection_string" {
  value     = local.connection_string
  sensitive = true
}

output "functions_connection_string" {
  value     = azurerm_storage_account.functions.primary_connection_string
  sensitive = true
}

output "functions_primary_access_key" {
  value     = azurerm_storage_account.functions.primary_access_key
  sensitive = true
}
