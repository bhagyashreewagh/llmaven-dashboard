# ── Container Registry ────────────────────────────────────────────────────────

resource "azurerm_container_registry" "main" {
  name                = "${replace(var.prefix, "-", "")}acr${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = true
  tags                = var.tags
}

# ── App Service Plan ──────────────────────────────────────────────────────────

resource "azurerm_service_plan" "main" {
  name                = "${var.prefix}-apps-plan"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.sku
  tags                = var.tags
}

# ── Streamlit Dashboard ───────────────────────────────────────────────────────

resource "azurerm_linux_web_app" "streamlit" {
  name                = "${var.prefix}-streamlit"
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.main.id

  identity { type = "SystemAssigned" }

  site_config {
    application_stack {
      docker_image_name        = "${azurerm_container_registry.main.login_server}/llmaven-dashboard:${var.streamlit_image_tag}"
      docker_registry_url      = "https://${azurerm_container_registry.main.login_server}"
      docker_registry_username = azurerm_container_registry.main.admin_username
      docker_registry_password = azurerm_container_registry.main.admin_password
    }
  }

  app_settings = {
    WEBSITES_PORT                   = "8501"
    AZURE_STORAGE_CONNECTION_STRING = var.adls_connection_string
    ADLS_CONTAINER                  = var.adls_container
    APPINSIGHTS_INSTRUMENTATIONKEY  = var.app_insights_key
  }

  tags = var.tags
}
