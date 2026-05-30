variable "project" {
  description = "Short project prefix used in all resource names."
  type        = string
  default     = "llmaven"
}

variable "environment" {
  description = "Deployment environment: dev | staging | prod"
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}

variable "location" {
  description = "Azure region for all resources."
  type        = string
  default     = "westus2"
}

variable "tenant_id" {
  description = "Azure AD tenant ID."
  type        = string
}

variable "current_user_object_id" {
  description = "Object ID of the deploying user — granted Key Vault admin."
  type        = string
}

# ── Storage (Carlos's existing account) ───────────────────────────────────────

variable "existing_storage_account_name" {
  description = "Existing ADLS Gen2 storage account where LiteLLM logs are written."
  type        = string
  default     = "llmavenissprodwestst"
}

variable "existing_storage_account_rg" {
  description = "Resource group of the existing storage account."
  type        = string
  default     = "rg-llmaven-iss-westus2"
}

variable "adls_container_name" {
  description = "Container in ADLS where LiteLLM logs land."
  type        = string
  default     = "litellm-logs"
}

# ── App Services ───────────────────────────────────────────────────────────────

variable "app_service_sku" {
  description = "SKU for the App Service Plan running Streamlit."
  type        = string
  default     = "B2"
}

variable "streamlit_image_tag" {
  description = "Docker image tag for the Streamlit dashboard."
  type        = string
  default     = "latest"
}
