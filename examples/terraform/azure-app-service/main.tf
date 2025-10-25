terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    Environment = var.environment
    Application = "jira2solidtime"
    ManagedBy   = "Terraform"
  }
}

# Storage Account for persistent data
resource "azurerm_storage_account" "main" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = {
    Environment = var.environment
    Application = "jira2solidtime"
    ManagedBy   = "Terraform"
  }
}

# File Share for data persistence
resource "azurerm_storage_share" "data" {
  name                 = "jira2solidtime-data"
  storage_account_name = azurerm_storage_account.main.name
  quota                = var.data_share_quota_gb

  lifecycle {
    prevent_destroy = false
  }
}

# App Service Plan
resource "azurerm_service_plan" "main" {
  name                = var.app_service_plan_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = var.sku_name

  tags = {
    Environment = var.environment
    Application = "jira2solidtime"
    ManagedBy   = "Terraform"
  }
}

# Linux Web App (Container)
resource "azurerm_linux_web_app" "main" {
  name                = var.app_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_service_plan.main.location
  service_plan_id     = azurerm_service_plan.main.id
  https_only          = true

  site_config {
    always_on = var.sku_name != "F1" ? true : false

    application_stack {
      docker_image_name   = var.docker_image
      docker_registry_url = "https://index.docker.io"
    }

    health_check_path                 = "/"
    health_check_eviction_time_in_min = 5
  }

  app_settings = {
    WEBSITES_PORT                        = "8080"
    DOCKER_REGISTRY_SERVER_URL           = "https://index.docker.io"
    WEBSITES_ENABLE_APP_SERVICE_STORAGE  = "false"
    DOCKER_ENABLE_CI                     = "true"
  }

  storage_account {
    name         = "data"
    type         = "AzureFiles"
    account_name = azurerm_storage_account.main.name
    share_name   = azurerm_storage_share.data.name
    access_key   = azurerm_storage_account.main.primary_access_key
    mount_path   = "/app/data"
  }

  identity {
    type = "SystemAssigned"
  }

  logs {
    detailed_error_messages = true
    failed_request_tracing  = true

    http_logs {
      file_system {
        retention_in_days = 7
        retention_in_mb   = 35
      }
    }
  }

  tags = {
    Environment = var.environment
    Application = "jira2solidtime"
    ManagedBy   = "Terraform"
  }
}

# Optional: Application Insights
resource "azurerm_log_analytics_workspace" "main" {
  count               = var.enable_monitoring ? 1 : 0
  name                = "log-jira2solidtime"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    Environment = var.environment
    Application = "jira2solidtime"
    ManagedBy   = "Terraform"
  }
}

resource "azurerm_application_insights" "main" {
  count               = var.enable_monitoring ? 1 : 0
  name                = "appi-jira2solidtime"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_id        = azurerm_log_analytics_workspace.main[0].id
  application_type    = "web"

  tags = {
    Environment = var.environment
    Application = "jira2solidtime"
    ManagedBy   = "Terraform"
  }
}

# Optional: IP Restrictions
resource "azurerm_app_service_virtual_network_swift_connection" "main" {
  count          = var.enable_vnet_integration ? 1 : 0
  app_service_id = azurerm_linux_web_app.main.id
  subnet_id      = var.subnet_id
}
