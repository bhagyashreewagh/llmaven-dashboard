variable "prefix"                 { type = string }
variable "location"               { type = string }
variable "resource_group_name"    { type = string }
variable "suffix"                 { type = string }
variable "tags"                   { type = map(string) }
variable "tenant_id"              { type = string }
variable "current_user_object_id" { type = string }
variable "streamlit_principal_id" { type = string }

variable "adls_connection_string" {
  type      = string
  sensitive = true
}
