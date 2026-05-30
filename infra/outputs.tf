output "resource_group_name"         { value = azurerm_resource_group.main.name }

output "adls_storage_account_name"   { value = module.storage.name }
output "adls_container_name"         { value = var.adls_container_name }

output "functions_app_name"          { value = module.functions.function_app_name }
output "functions_hostname"          { value = module.functions.default_hostname }

output "synapse_workspace_name"      { value = module.synapse.workspace_name }
output "synapse_serverless_sql_endpoint" {
  description = "Use as the server in SSMS / pyodbc / Streamlit"
  value       = module.synapse.serverless_sql_endpoint
}

output "streamlit_url"               { value = module.app_services.streamlit_url }
output "mlflow_url"                  { value = module.app_services.mlflow_url }
output "acr_login_server"            { value = module.app_services.acr_login_server }
output "key_vault_name"              { value = module.keyvault.key_vault_name }

output "litellm_env_config" {
  description = "Paste into your LiteLLM .env to wire up MLflow + ADLS logging."
  value = <<-EOT
    MLFLOW_TRACKING_URI=${module.app_services.mlflow_url}
    success_callback=["mlflow"]
    AZURE_STORAGE_CONNECTION_STRING=<get from Key Vault: adls-connection-string>
    ADLS_CONTAINER=${var.adls_container_name}
  EOT
}
