# Azure Deployment Guide

This guide covers deploying jira2solidtime to Azure App Service using both Azure CLI (imperative) and Terraform (declarative/Infrastructure as Code).

## Prerequisites

Before you begin, ensure you have:

- **Azure Subscription**: Active Azure account
- **Azure CLI**: Version 2.50+ installed ([Install Guide](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli))
- **Terraform**: Version 1.5+ installed ([Install Guide](https://developer.hashicorp.com/terraform/install)) - for IaC approach
- **Docker Hub Account**: For custom images (optional)
- **Configuration File**: Your `config.json` with API credentials

### Login to Azure

```bash
# Login to Azure
az login

# Set default subscription (if you have multiple)
az account set --subscription "Your Subscription Name"

# Verify login
az account show
```

## Architecture Overview

The deployment creates the following Azure resources:

- **Resource Group**: Logical container for all resources
- **App Service Plan**: Compute resources (Linux, B1 SKU)
- **App Service**: Web app running the Docker container
- **Storage Account**: For persistent data (worklog mappings, sync history)
- **File Share**: Mounted to `/app/data` in the container

**Estimated Cost**: ~12€/month for B1 tier

---

## Option 1: Azure CLI Deployment

### Step 1: Create Resource Group

```bash
# Variables
RESOURCE_GROUP="rg-jira2solidtime"
LOCATION="westeurope"
APP_NAME="jira2solidtime-app"  # Must be globally unique!
PLAN_NAME="plan-jira2solidtime"
STORAGE_ACCOUNT="stjira2solidtime"  # Must be globally unique, lowercase, no hyphens

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### Step 2: Create Storage Account for Persistent Data

```bash
# Create storage account
az storage account create \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2

# Get storage account key
STORAGE_KEY=$(az storage account keys list \
  --resource-group $RESOURCE_GROUP \
  --account-name $STORAGE_ACCOUNT \
  --query '[0].value' \
  --output tsv)

# Create file share for data persistence
az storage share create \
  --name jira2solidtime-data \
  --account-name $STORAGE_ACCOUNT \
  --account-key $STORAGE_KEY \
  --quota 5
```

### Step 3: Create App Service Plan

```bash
# Create Linux App Service Plan (B1 tier)
az appservice plan create \
  --name $PLAN_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --is-linux \
  --sku B1
```

### Step 4: Create Web App

```bash
# Create web app with container
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $PLAN_NAME \
  --name $APP_NAME \
  --deployment-container-image-name cddsab/jira2solidtime:0.1.0

# Configure container settings
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --settings \
    WEBSITES_PORT=8080 \
    DOCKER_REGISTRY_SERVER_URL=https://index.docker.io \
    WEBSITES_ENABLE_APP_SERVICE_STORAGE=false
```

### Step 5: Mount Storage for Persistent Data

```bash
# Mount Azure Files to /app/data
az webapp config storage-account add \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --custom-id data \
  --storage-type AzureFiles \
  --account-name $STORAGE_ACCOUNT \
  --share-name jira2solidtime-data \
  --access-key $STORAGE_KEY \
  --mount-path /app/data
```

### Step 6: Upload Configuration

You need to provide your `config.json`. Options:

#### Option A: Upload via Azure Files

```bash
# Upload config.json to file share
az storage file upload \
  --share-name jira2solidtime-data \
  --source ./config.json \
  --account-name $STORAGE_ACCOUNT \
  --account-key $STORAGE_KEY

# Update mount to include config
az webapp config storage-account add \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --custom-id config \
  --storage-type AzureFiles \
  --account-name $STORAGE_ACCOUNT \
  --share-name jira2solidtime-data \
  --access-key $STORAGE_KEY \
  --mount-path /app/config.json
```

#### Option B: Use App Settings (Environment Variables)

⚠️ **Not recommended** for this app as it uses `config.json`. Consider extending the app to support env vars if needed.

### Step 7: Restart and Verify

```bash
# Restart web app
az webapp restart \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME

# Get app URL
APP_URL=$(az webapp show \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --query defaultHostName \
  --output tsv)

echo "Application URL: https://${APP_URL}"

# Test health
curl -I "https://${APP_URL}/"
```

### Step 8: View Logs

```bash
# Stream live logs
az webapp log tail \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME

# Download logs
az webapp log download \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --log-file webapp-logs.zip
```

---

## Option 2: Terraform Deployment

For reproducible, version-controlled infrastructure, use Terraform.

### Directory Structure

The Terraform configuration is located in `examples/terraform/azure-app-service/`:

```
examples/terraform/azure-app-service/
├── main.tf                  # Main infrastructure definition
├── variables.tf             # Input variables
├── outputs.tf               # Output values
├── terraform.tfvars.example # Example configuration
└── README.md               # Terraform-specific docs
```

### Step 1: Prepare Configuration

```bash
# Navigate to Terraform directory
cd examples/terraform/azure-app-service/

# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit configuration
nano terraform.tfvars
```

**terraform.tfvars:**
```hcl
resource_group_name    = "rg-jira2solidtime"
location               = "westeurope"
app_service_plan_name  = "plan-jira2solidtime"
app_name               = "jira2solidtime-app"  # Must be globally unique
storage_account_name   = "stjira2solidtime"     # Must be globally unique
docker_image           = "cddsab/jira2solidtime:0.1.0"
sku_name               = "B1"
```

### Step 2: Initialize Terraform

```bash
# Initialize Terraform (downloads providers)
terraform init

# Validate configuration
terraform validate

# Preview changes
terraform plan
```

### Step 3: Deploy Infrastructure

```bash
# Apply configuration
terraform apply

# Confirm with 'yes' when prompted
```

Terraform will create all resources and output the application URL.

### Step 4: Upload Configuration File

After infrastructure is created, upload `config.json`:

```bash
# Get storage account details from Terraform output
STORAGE_ACCOUNT=$(terraform output -raw storage_account_name)
STORAGE_KEY=$(terraform output -raw storage_account_key)

# Upload config
az storage file upload \
  --share-name jira2solidtime-data \
  --source ../../config.json \
  --account-name $STORAGE_ACCOUNT \
  --account-key $STORAGE_KEY
```

### Step 5: Verify Deployment

```bash
# Get app URL
APP_URL=$(terraform output -raw app_url)

# Test application
curl -I "$APP_URL"

# Open in browser
open "$APP_URL"
```

### Managing Infrastructure

```bash
# View current state
terraform show

# Update infrastructure (after changing variables)
terraform apply

# Destroy all resources
terraform destroy
```

---

## Configuration Management in Azure

### App Settings

For non-sensitive configuration, use App Settings:

```bash
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --settings \
    SYNC_SCHEDULE="0 8 * * *" \
    SYNC_DAYS_BACK=30
```

### Azure Key Vault (Recommended for Secrets)

For sensitive credentials:

```bash
# Create Key Vault
az keyvault create \
  --name kv-jira2solidtime \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Store secrets
az keyvault secret set \
  --vault-name kv-jira2solidtime \
  --name jira-api-token \
  --value "your-secret-token"

# Grant web app access
az webapp identity assign \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME

# Get managed identity principal ID
PRINCIPAL_ID=$(az webapp identity show \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --query principalId \
  --output tsv)

# Grant Key Vault access
az keyvault set-policy \
  --name kv-jira2solidtime \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get list
```

**Note:** You'll need to modify the app to read from Key Vault.

---

## Monitoring and Diagnostics

### Application Insights (Recommended)

Enable built-in monitoring:

```bash
# Create Application Insights
az monitor app-insights component create \
  --app jira2solidtime-insights \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --application-type web

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app jira2solidtime-insights \
  --resource-group $RESOURCE_GROUP \
  --query instrumentationKey \
  --output tsv)

# Link to web app
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --settings \
    APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY
```

### Log Analytics

View metrics and logs in Azure Portal:

1. Navigate to App Service → Monitoring → Logs
2. Use Kusto Query Language (KQL) for advanced queries

**Example query:**
```kql
AppServiceConsoleLogs
| where TimeGenerated > ago(1h)
| where ResultDescription contains "sync"
| order by TimeGenerated desc
```

### Alerts

Create alerts for critical events:

```bash
# Alert on high CPU usage
az monitor metrics alert create \
  --name "High CPU Alert" \
  --resource-group $RESOURCE_GROUP \
  --scopes $(az webapp show --resource-group $RESOURCE_GROUP --name $APP_NAME --query id --output tsv) \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m \
  --evaluation-frequency 1m
```

---

## Scaling

### Vertical Scaling (Change SKU)

```bash
# Upgrade to S1 (more CPU/memory)
az appservice plan update \
  --name $PLAN_NAME \
  --resource-group $RESOURCE_GROUP \
  --sku S1
```

### Horizontal Scaling (Multiple Instances)

```bash
# Scale out to 2 instances
az appservice plan update \
  --name $PLAN_NAME \
  --resource-group $RESOURCE_GROUP \
  --number-of-workers 2
```

⚠️ **Note:** This app maintains state in SQLite. For multi-instance, consider:
- Using Azure Database for PostgreSQL instead of SQLite
- Implementing distributed locking for sync operations

---

## Security Hardening

### IP Restrictions

Restrict access to specific IPs:

```bash
# Allow only your office IP
az webapp config access-restriction add \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --rule-name "AllowOffice" \
  --action Allow \
  --ip-address "203.0.113.0/24" \
  --priority 100

# Deny all other traffic
az webapp config access-restriction add \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --rule-name "DenyAll" \
  --action Deny \
  --ip-address "0.0.0.0/0" \
  --priority 200
```

### HTTPS Only

```bash
# Enforce HTTPS
az webapp update \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --https-only true
```

### Custom Domain and SSL

```bash
# Add custom domain
az webapp config hostname add \
  --resource-group $RESOURCE_GROUP \
  --webapp-name $APP_NAME \
  --hostname jira2solidtime.yourdomain.com

# Bind SSL certificate (free managed certificate)
az webapp config ssl bind \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --certificate-thumbprint <thumbprint> \
  --ssl-type SNI
```

---

## Backup and Disaster Recovery

### Automated Backups

Enable automatic backups:

```bash
# Create backup storage
az storage account create \
  --name stbackupjira2solidtime \
  --resource-group $RESOURCE_GROUP \
  --sku Standard_LRS

# Configure backup
az webapp config backup create \
  --resource-group $RESOURCE_GROUP \
  --webapp-name $APP_NAME \
  --backup-name daily-backup \
  --container-url "https://stbackupjira2solidtime.blob.core.windows.net/backups"
```

### Manual Backup

```bash
# Backup data file share
az storage file download-batch \
  --account-name $STORAGE_ACCOUNT \
  --source jira2solidtime-data \
  --destination ./backup/$(date +%Y%m%d)
```

---

## Cost Optimization

### Current Cost Breakdown (B1 SKU)

| Resource            | Monthly Cost |
|---------------------|--------------|
| App Service Plan B1 | ~10€         |
| Storage Account     | ~0.50€       |
| Bandwidth (estimated) | ~1€        |
| **Total**           | **~12€**     |

### Optimization Tips

1. **Use Free Tier for Testing**: F1 SKU is free but limited
2. **Stop non-production environments**:
   ```bash
   az webapp stop --resource-group $RESOURCE_GROUP --name $APP_NAME
   ```
3. **Use Reserved Instances**: 1-3 year commitments save 30-50%
4. **Optimize sync frequency**: Reduce API calls by adjusting cron schedule

---

## Troubleshooting

### Common Issues

#### 1. App Won't Start

**Symptoms:** HTTP 500 errors, app not accessible

**Debug:**
```bash
# View logs
az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_NAME

# Check container status
az webapp show \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --query state
```

**Common causes:**
- Missing `config.json` in file share
- Incorrect `WEBSITES_PORT` setting
- Docker image pull failures

#### 2. Persistent Data Not Working

**Symptoms:** Sync history lost on restart

**Verify mount:**
```bash
# List storage mounts
az webapp config storage-account list \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME
```

#### 3. High Costs

**Analyze costs:**
```bash
# View cost analysis
az consumption usage list --start-date 2025-10-01 --end-date 2025-10-31
```

### Getting Help

- **Azure Support**: [Azure Portal](https://portal.azure.com) → Support + Troubleshooting
- **App Issues**: [GitHub Issues](https://github.com/cdds-ab/jira2solidtime/issues)
- **Terraform**: [Terraform Registry](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)

---

## Cleanup

### Delete All Resources

**Azure CLI:**
```bash
# Delete entire resource group (removes all resources)
az group delete --name $RESOURCE_GROUP --yes --no-wait
```

**Terraform:**
```bash
terraform destroy
```

⚠️ **Warning:** This permanently deletes all data!

---

## Next Steps

- **Enable CI/CD**: Automate deployments from GitHub
- **Set up monitoring**: Application Insights dashboards
- **Implement high availability**: Multi-region deployment
- **Security audit**: Azure Security Center recommendations

## Additional Resources

- [Azure App Service Documentation](https://learn.microsoft.com/en-us/azure/app-service/)
- [Terraform AzureRM Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/)
- [Local Deployment Guide](deployment-local.md)
