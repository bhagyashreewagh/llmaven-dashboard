output "acr_login_server"       { value = azurerm_container_registry.main.login_server }
output "acr_admin_username"     { value = azurerm_container_registry.main.admin_username }
output "streamlit_url"          { value = "https://${azurerm_linux_web_app.streamlit.default_hostname}" }
output "streamlit_app_name"     { value = azurerm_linux_web_app.streamlit.name }
output "streamlit_principal_id" { value = azurerm_linux_web_app.streamlit.identity[0].principal_id }

output "acr_admin_password" {
  value     = azurerm_container_registry.main.admin_password
  sensitive = true
}
