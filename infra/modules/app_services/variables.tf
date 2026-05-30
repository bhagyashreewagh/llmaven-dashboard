variable "prefix"               { type = string }
variable "location"             { type = string }
variable "resource_group_name"  { type = string }
variable "suffix"               { type = string }
variable "tags"                 { type = map(string) }

variable "sku" {
  type    = string
  default = "B2"
}

variable "streamlit_image_tag" {
  type    = string
  default = "latest"
}

variable "adls_connection_string" {
  type      = string
  sensitive = true
}

variable "adls_container" {
  type    = string
  default = "litellm-logs"
}

variable "app_insights_key" {
  type      = string
  sensitive = true
}
