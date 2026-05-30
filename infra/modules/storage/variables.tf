variable "prefix"               { type = string }
variable "location"             { type = string }
variable "resource_group_name"  { type = string }
variable "suffix"               { type = string }
variable "adls_container_name"  { type = string }
variable "tags"                 { type = map(string) }

variable "existing_storage_account_name" {
  type    = string
  default = ""
}

variable "existing_storage_account_rg" {
  type    = string
  default = ""
}
