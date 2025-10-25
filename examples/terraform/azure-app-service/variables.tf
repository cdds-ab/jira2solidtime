variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
  default     = "rg-jira2solidtime"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "westeurope"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "app_service_plan_name" {
  description = "Name of the App Service Plan"
  type        = string
  default     = "plan-jira2solidtime"
}

variable "app_name" {
  description = "Name of the Web App (must be globally unique)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]{3,60}$", var.app_name))
    error_message = "App name must be 3-60 characters long and contain only lowercase letters, numbers, and hyphens"
  }
}

variable "sku_name" {
  description = "SKU for App Service Plan (B1, B2, S1, P1V2, etc.)"
  type        = string
  default     = "B1"

  validation {
    condition     = can(regex("^(F1|B1|B2|B3|S1|S2|S3|P1V2|P2V2|P3V2)$", var.sku_name))
    error_message = "SKU must be a valid App Service Plan tier"
  }
}

variable "docker_image" {
  description = "Docker image to deploy (format: image:tag)"
  type        = string
  default     = "cddsab/jira2solidtime:0.1.0"
}

variable "storage_account_name" {
  description = "Name of storage account (must be globally unique, lowercase, no hyphens)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
    error_message = "Storage account name must be 3-24 characters long, lowercase letters and numbers only"
  }
}

variable "data_share_quota_gb" {
  description = "Quota for data file share in GB"
  type        = number
  default     = 5

  validation {
    condition     = var.data_share_quota_gb >= 1 && var.data_share_quota_gb <= 102400
    error_message = "Quota must be between 1 GB and 102400 GB"
  }
}

variable "enable_monitoring" {
  description = "Enable Application Insights monitoring"
  type        = bool
  default     = false
}

variable "enable_vnet_integration" {
  description = "Enable VNet integration for private networking"
  type        = bool
  default     = false
}

variable "subnet_id" {
  description = "Subnet ID for VNet integration (required if enable_vnet_integration is true)"
  type        = string
  default     = null
}

variable "allowed_ip_addresses" {
  description = "List of IP addresses/CIDR blocks allowed to access the app"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
