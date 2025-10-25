# Terraform Azure App Service Deployment

This Terraform module deploys jira2solidtime to Azure App Service with persistent storage.

## Prerequisites

- [Terraform](https://www.terraform.io/downloads) >= 1.5
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
- Active Azure subscription

## Quick Start

### 1. Login to Azure

```bash
az login
az account set --subscription "Your Subscription Name"
```

### 2. Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Edit with your values
```

**Important:** Change these to be globally unique:
- `app_name` - Must be unique across all Azure
- `storage_account_name` - Must be unique, lowercase, no hyphens

### 3. Initialize Terraform

```bash
terraform init
```

### 4. Plan Deployment

```bash
terraform plan
```

Review the plan to ensure correct resources will be created.

### 5. Deploy

```bash
terraform apply
```

Type `yes` when prompted.

### 6. Upload Configuration

After deployment, upload your `config.json`:

```bash
# Get outputs
STORAGE_ACCOUNT=$(terraform output -raw storage_account_name)
STORAGE_KEY=$(terraform output -raw storage_account_key)

# Upload config
az storage file upload \
  --share-name jira2solidtime-data \
  --source ../../../config.json \
  --account-name $STORAGE_ACCOUNT \
  --account-key $STORAGE_KEY
```

### 7. Access Application

```bash
APP_URL=$(terraform output -raw app_url)
echo "Application URL: $APP_URL"
open $APP_URL
```

## Resources Created

This module creates the following Azure resources:

- **Resource Group**: Container for all resources
- **App Service Plan**: Linux-based compute (B1 SKU by default)
- **App Service**: Web app running Docker container
- **Storage Account**: For persistent data
- **File Share**: Mounted to `/app/data` in container
- **Application Insights** (optional): Monitoring and diagnostics
- **Log Analytics Workspace** (optional): For Application Insights

## Configuration Options

### Basic Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `app_name` | Web app name (globally unique) | Required |
| `storage_account_name` | Storage account name | Required |
| `location` | Azure region | `westeurope` |
| `sku_name` | App Service Plan tier | `B1` |
| `docker_image` | Docker image to deploy | `cddsab/jira2solidtime:0.1.0` |

### Advanced Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `enable_monitoring` | Enable Application Insights | `false` |
| `enable_vnet_integration` | Enable VNet integration | `false` |
| `allowed_ip_addresses` | IP whitelist (CIDR blocks) | `[]` |
| `data_share_quota_gb` | File share size in GB | `5` |

### SKU Options

Available App Service Plan SKUs:

- **F1**: Free (limited, for testing only)
- **B1**: Basic (~10€/month) - Recommended minimum
- **B2/B3**: Basic with more resources
- **S1/S2/S3**: Standard (auto-scaling, staging slots)
- **P1V2/P2V2/P3V2**: Premium (high performance)

## Examples

### Minimal Configuration

```hcl
# terraform.tfvars
app_name             = "my-jira2solidtime"
storage_account_name = "stmyjira2solidtime"
```

### Production Configuration with Monitoring

```hcl
# terraform.tfvars
app_name                = "jira2solidtime-prod"
storage_account_name    = "stjira2solidtimeprod"
location                = "westeurope"
sku_name                = "S1"
enable_monitoring       = true
allowed_ip_addresses    = ["203.0.113.0/24"]
data_share_quota_gb     = 10

tags = {
  Environment = "production"
  CostCenter  = "IT"
}
```

## Outputs

After successful deployment, Terraform outputs:

```bash
# View all outputs
terraform output

# Specific output
terraform output app_url
terraform output storage_account_key  # Sensitive, use -raw flag
```

## Updating the Deployment

### Update Docker Image

```hcl
# terraform.tfvars
docker_image = "cddsab/jira2solidtime:0.2.0"
```

```bash
terraform apply
```

### Scale Up/Down

```hcl
# terraform.tfvars
sku_name = "S1"  # Upgrade from B1 to S1
```

```bash
terraform apply
```

## State Management

### Local State (Default)

State is stored in `terraform.tfstate` (gitignored).

### Remote State (Recommended for Teams)

Use Azure Storage for shared state:

```hcl
# backend.tf
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "sttfstate"
    container_name       = "tfstate"
    key                  = "jira2solidtime.tfstate"
  }
}
```

## Monitoring

If `enable_monitoring = true`:

1. Navigate to Azure Portal → Application Insights
2. View:
   - Live Metrics
   - Failed Requests
   - Performance
   - Availability

Query logs with Kusto (KQL):

```kql
requests
| where timestamp > ago(1h)
| summarize count() by bin(timestamp, 5m)
```

## Troubleshooting

### Terraform Errors

**Invalid resource names:**
```
Error: names must be globally unique
```
→ Change `app_name` or `storage_account_name` to unique values

**Insufficient permissions:**
```
Error: authorization failed
```
→ Ensure Azure account has Contributor role

### Deployment Issues

**App not starting:**

```bash
# View logs
az webapp log tail \
  --resource-group $(terraform output -raw resource_group_name) \
  --name $(terraform output -raw app_name)
```

**Missing config.json:**

Upload it manually:
```bash
STORAGE_ACCOUNT=$(terraform output -raw storage_account_name)
STORAGE_KEY=$(terraform output -raw storage_account_key)

az storage file upload \
  --share-name jira2solidtime-data \
  --source ./config.json \
  --account-name $STORAGE_ACCOUNT \
  --account-key $STORAGE_KEY
```

## Cost Optimization

### Estimated Monthly Costs

| Configuration | Monthly Cost |
|---------------|--------------|
| B1 + Storage | ~12€ |
| S1 + Monitoring | ~60€ |
| P1V2 | ~150€ |

### Reduce Costs

1. **Stop when not in use:**
   ```bash
   az webapp stop \
     --resource-group $(terraform output -raw resource_group_name) \
     --name $(terraform output -raw app_name)
   ```

2. **Use F1 tier for dev/test** (⚠️ limited resources)

3. **Delete when not needed:**
   ```bash
   terraform destroy
   ```

## Cleanup

### Destroy All Resources

```bash
terraform destroy
```

⚠️ **Warning:** This deletes all data permanently!

### Backup Before Destroy

```bash
# Backup data
STORAGE_ACCOUNT=$(terraform output -raw storage_account_name)
STORAGE_KEY=$(terraform output -raw storage_account_key)

az storage file download-batch \
  --account-name $STORAGE_ACCOUNT \
  --account-key $STORAGE_KEY \
  --source jira2solidtime-data \
  --destination ./backup/
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Azure

on:
  push:
    branches: [main]

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Terraform Init
        run: terraform init
        working-directory: ./examples/terraform/azure-app-service

      - name: Terraform Apply
        run: terraform apply -auto-approve
        working-directory: ./examples/terraform/azure-app-service
```

## Additional Resources

- [Terraform AzureRM Provider Docs](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Azure App Service Docs](https://learn.microsoft.com/en-us/azure/app-service/)
- [Parent Deployment Guide](../../../docs/deployment-azure.md)
- [Local Deployment](../../../docs/deployment-local.md)

## Support

- Issues: [GitHub Issues](https://github.com/cdds-ab/jira2solidtime/issues)
- Terraform: [Terraform Community](https://discuss.hashicorp.com/)
- Azure: [Azure Support](https://azure.microsoft.com/en-us/support/options/)
