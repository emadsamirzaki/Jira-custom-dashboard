# Azure Deployment Guide - Jira Dashboard

## Overview
This guide covers deploying the Jira Dashboard to Microsoft Azure. Choose the option that best fits your needs and infrastructure.

---

## 📋 Prerequisites

- Azure subscription (free tier available)
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) installed
- Docker (for local testing)
- Your Jira credentials ready:
  - Jira URL: `https://your-domain.atlassian.net`
  - Email
  - API Token

---

## 🎯 Deployment Options (Complexity → Recommended)

| Option | Complexity | Cost | Uptime | Best For |
|--------|-----------|------|--------|----------|
| **Azure Container Instances** | ⭐ Easy | Low | 99.9% | Testing, demo, small team |
| **Azure App Service** | ⭐⭐ Medium | Low-Medium | 99.95% | Production, auto-scaling |
| **Azure Container Registry + AKS** | ⭐⭐⭐ Advanced | Medium-High | 99.99% | Enterprise, multi-replica |

---

## 🟦 Option 1: Azure Container Instances (Easiest)

**Best for:** Quick deployment, testing, small teams
**Time:** ~10 minutes
**Cost:** ~$10-20/month

### Step 1: Create Resource Group
```bash
az group create \
  --name jira-dashboard-rg \
  --location eastus
```

### Step 2: Create Container Instance
```bash
az container create \
  --resource-group jira-dashboard-rg \
  --name jira-dashboard \
  --image mcr.microsoft.com/azuredocs/aci-helloworld \
  --dns-name-label jira-dashboard-001 \
  --ports 8501 \
  --environment-variables \
    JIRA_URL="https://your-domain.atlassian.net" \
    JIRA_EMAIL="your-email@example.com" \
    JIRA_TOKEN="your-api-token-here" \
    JIRA_PROJECT_KEY="ESP" \
    JIRA_BOARD_ID="81" \
    LOG_LEVEL="WARNING" \
  --restart-policy Always \
  --memory 1.5 \
  --cpu 1
```

### Step 3: Verify Deployment
```bash
# Check status
az container show \
  --resource-group jira-dashboard-rg \
  --name jira-dashboard \
  --query instanceView.state

# View logs
az container logs \
  --resource-group jira-dashboard-rg \
  --name jira-dashboard

# Get public IP
az container show \
  --resource-group jira-dashboard-rg \
  --name jira-dashboard \
  --query ipAddress.fqdn
```

### Step 4: Access Dashboard
```
http://jira-dashboard-001.eastus.azurecontainer.io:8501
```

### Stop & Delete (when done)
```bash
az container delete \
  --resource-group jira-dashboard-rg \
  --name jira-dashboard \
  --yes
```

---

## 🟨 Option 2: Azure App Service (Recommended for Production)

**Best for:** Production deployment, auto-scaling, custom domains
**Time:** ~15 minutes
**Cost:** ~$50-100/month (depends on tier)

### Step 1: Create Resource Group & App Service Plan
```bash
# Create resource group
az group create \
  --name jira-dashboard-prod \
  --location eastus

# Create App Service Plan (Linux, Docker capable)
az appservice plan create \
  --name jira-dashboard-plan \
  --resource-group jira-dashboard-prod \
  --sku B2 \
  --is-linux
```

### Step 2: Create Web App
```bash
az webapp create \
  --resource-group jira-dashboard-prod \
  --plan jira-dashboard-plan \
  --name jira-dashboard-app \
  --runtime "DOCKER|mcr.microsoft.com/appsvc/staticsite:latest"
```

### Step 3: Configure Docker Container
```bash
# Set Docker image (from public Docker Hub)
# First, you need to push your image to Docker Hub or Azure Container Registry

# For Docker Hub:
az webapp config container set \
  --name jira-dashboard-app \
  --resource-group jira-dashboard-prod \
  --docker-custom-image-name "your-dockerhub-username/jira-dashboard:latest" \
  --docker-registry-server-url "https://index.docker.io" \
  --docker-registry-server-user "your-dockerhub-username" \
  --docker-registry-server-password "your-dockerhub-password"
```

### Step 4: Set Environment Variables
```bash
az webapp config appsettings set \
  --resource-group jira-dashboard-prod \
  --name jira-dashboard-app \
  --settings \
    JIRA_URL="https://your-domain.atlassian.net" \
    JIRA_EMAIL="your-email@example.com" \
    JIRA_TOKEN="your-api-token-here" \
    JIRA_PROJECT_KEY="ESP" \
    JIRA_BOARD_ID="81" \
    LOG_LEVEL="WARNING" \
    WEBSITES_PORT=8501 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS="0.0.0.0"
```

### Step 5: Configure Startup Command
```bash
az webapp config set \
  --resource-group jira-dashboard-prod \
  --name jira-dashboard-app \
  --startup-file "streamlit run app.py --logger.level=warning --server.port=8501 --server.address=0.0.0.0"
```

### Step 6: Enable Continuous Deployment (Optional)
```bash
# Configure GitHub Actions or container registry webhook
az webapp deployment github-actions add \
  --repo "your-github-username/Jira-custom-dashboard" \
  --resource-group jira-dashboard-prod \
  --name jira-dashboard-app \
  --branch master \
  --runtime "docker"
```

### Access Your App
```
https://jira-dashboard-app.azurewebsites.net
```

### View Logs
```bash
az webapp log tail \
  --resource-group jira-dashboard-prod \
  --name jira-dashboard-app
```

---

## 🟦 Option 3: Azure Container Registry + App Service (Best Practice)

**Best for:** Enterprise, security-focused, private images
**Time:** ~20 minutes
**Cost:** ~$80-200/month

### Step 1: Create Container Registry
```bash
az acr create \
  --resource-group jira-dashboard-prod \
  --name jiradashboard \
  --sku Basic \
  --location eastus
```

### Step 2: Build and Push Image
```bash
# Get ACR login credentials
az acr login --name jiradashboard

# Get ACR URL
ACR_URL=$(az acr show \
  --name jiradashboard \
  --query loginServer \
  --output tsv)

# Build image from your repo
git clone https://github.com/emadsamirzaki/Jira-custom-dashboard.git
cd Jira-custom-dashboard

# Build and push to ACR
az acr build \
  --registry jiradashboard \
  --image jira-dashboard:latest \
  .
```

### Step 3: Create App Service
```bash
# Create App Service Plan
az appservice plan create \
  --name jira-dashboard-plan \
  --resource-group jira-dashboard-prod \
  --sku B2 \
  --is-linux

# Create Web App
az webapp create \
  --resource-group jira-dashboard-prod \
  --plan jira-dashboard-plan \
  --name jira-dashboard-app \
  --deployment-container-image-name "${ACR_URL}/jira-dashboard:latest"
```

### Step 4: Configure ACR Integration
```bash
# Get ACR credentials
ACR_USER=$(az acr credential show \
  --name jiradashboard \
  --query "username" \
  --output tsv)

ACR_PASSWORD=$(az acr credential show \
  --name jiradashboard \
  --query "passwords[0].value" \
  --output tsv)

# Configure web app to pull from ACR
az webapp config container set \
  --resource-group jira-dashboard-prod \
  --name jira-dashboard-app \
  --docker-custom-image-name "${ACR_URL}/jira-dashboard:latest" \
  --docker-registry-server-url "https://${ACR_URL}" \
  --docker-registry-server-user "${ACR_USER}" \
  --docker-registry-server-password "${ACR_PASSWORD}"
```

### Step 5: Set Environment Variables & Configure
```bash
az webapp config appsettings set \
  --resource-group jira-dashboard-prod \
  --name jira-dashboard-app \
  --settings \
    JIRA_URL="https://your-domain.atlassian.net" \
    JIRA_EMAIL="your-email@example.com" \
    JIRA_TOKEN="your-api-token-here" \
    JIRA_PROJECT_KEY="ESP" \
    JIRA_BOARD_ID="81" \
    LOG_LEVEL="WARNING" \
    WEBSITES_PORT=8501 \
    DOCKER_REGISTRY_SERVER_URL="https://${ACR_URL}" \
    DOCKER_REGISTRY_SERVER_USERNAME="${ACR_USER}" \
    DOCKER_REGISTRY_SERVER_PASSWORD="${ACR_PASSWORD}"

# Set startup command
az webapp config set \
  --resource-group jira-dashboard-prod \
  --name jira-dashboard-app \
  --startup-file "streamlit run app.py --logger.level=warning --server.port=8501"
```

---

## 🔐 Secure Secrets Management (Recommended)

Instead of storing secrets in environment variables, use **Azure Key Vault**:

### Step 1: Create Key Vault
```bash
az keyvault create \
  --name jira-dashboard-kv \
  --resource-group jira-dashboard-prod \
  --location eastus
```

### Step 2: Store Secrets
```bash
az keyvault secret set \
  --vault-name jira-dashboard-kv \
  --name "jira-url" \
  --value "https://your-domain.atlassian.net"

az keyvault secret set \
  --vault-name jira-dashboard-kv \
  --name "jira-email" \
  --value "your-email@example.com"

az keyvault secret set \
  --vault-name jira-dashboard-kv \
  --name "jira-token" \
  --value "your-api-token-here"
```

### Step 3: Grant Web App Access
```bash
# Get Web App identity
PRINCIPAL_ID=$(az webapp identity assign \
  --resource-group jira-dashboard-prod \
  --name jira-dashboard-app \
  --query principalId \
  --output tsv)

# Grant permissions
az keyvault set-policy \
  --name jira-dashboard-kv \
  --object-id ${PRINCIPAL_ID} \
  --secret-permissions get list
```

### Step 4: Update Web App Settings (Reference Key Vault)
```bash
az webapp config appsettings set \
  --resource-group jira-dashboard-prod \
  --name jira-dashboard-app \
  --settings \
    JIRA_URL="@Microsoft.KeyVault(SecretUri=https://jira-dashboard-kv.vault.azure.net/secrets/jira-url/)" \
    JIRA_EMAIL="@Microsoft.KeyVault(SecretUri=https://jira-dashboard-kv.vault.azure.net/secrets/jira-email/)" \
    JIRA_TOKEN="@Microsoft.KeyVault(SecretUri=https://jira-dashboard-kv.vault.azure.net/secrets/jira-token/)"
```

---

## 📊 Add Custom Domain (Optional)

```bash
# Add custom domain
az appservice web config hostname add \
  --resource-group jira-dashboard-prod \
  --name jira-dashboard-app \
  --hostname "jira-dashboard.yourdomain.com"

# Create SSL/TLS certificate
az appservice web config ssl bind \
  --resource-group jira-dashboard-prod \
  --name jira-dashboard-app \
  --certificate-name "your-certificate" \
  --ssl-type SNI
```

---

## 📈 Auto-Scaling (Production)

### Enable Auto-Scale
```bash
# Create auto-scale rule
az monitor autoscale create \
  --resource-group jira-dashboard-prod \
  --resource jira-dashboard-app \
  --resource-type "Microsoft.web/sites" \
  --name "jira-dashboard-autoscale" \
  --min-count 2 \
  --max-count 5 \
  --count 2

# Scale based on CPU
az monitor autoscale rule create \
  --resource-group jira-dashboard-prod \
  --autoscale-name "jira-dashboard-autoscale" \
  --condition "Percentage CPU > 70 avg 5m" \
  --scale out 1
```

---

## 🔄 Continuous Deployment (CI/CD)

### Option A: GitHub Actions
```yaml
# .github/workflows/azure-deploy.yml
name: Deploy to Azure

on:
  push:
    branches: [master]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Build Docker image
      run: docker build -t jiradashboard.azurecr.io/jira-dashboard:${{ github.sha }} .
    
    - name: Push to Azure Container Registry
      run: |
        docker login -u ${{ secrets.ACR_USERNAME }} -p ${{ secrets.ACR_PASSWORD }} jiradashboard.azurecr.io
        docker push jiradashboard.azurecr.io/jira-dashboard:${{ github.sha }}
    
    - name: Deploy to Azure App Service
      uses: azure/webapps-deploy@v2
      with:
        app-name: jira-dashboard-app
        images: jiradashboard.azurecr.io/jira-dashboard:${{ github.sha }}
```

### Option B: Azure DevOps
1. Create new Pipeline in Azure DevOps
2. Connect to your GitHub repository
3. Select Docker template
4. Configure registry and deployment steps

---

## 🆘 Troubleshooting

### Container won't start
```bash
# Check logs
az container logs \
  --resource-group jira-dashboard-rg \
  --name jira-dashboard

# Check container status
az container show \
  --resource-group jira-dashboard-rg \
  --name jira-dashboard \
  --query instanceView
```

### Connection to Jira fails
1. Verify Jira URL is accessible from Azure
2. Check API token is valid
3. Verify firewall allows outbound HTTPS (port 443)
4. Check environment variables are set correctly

### High memory usage
```bash
# Increase memory limit (Container Instances)
az container create ... --memory 2.0

# Increase App Service plan tier
az appservice plan update \
  --name jira-dashboard-plan \
  --resource-group jira-dashboard-prod \
  --sku S1
```

### 503 Bad Gateway errors
- Check if container is running: `az container show --resource-group ... --name ...`
- Verify port 8501 is exposed correctly
- Check logs for application errors

---

## 📊 Monitoring & Logging

### Application Insights (Recommended)
```bash
# Create Application Insights
az monitor app-insights component create \
  --app jira-dashboard-insights \
  --location eastus \
  --resource-group jira-dashboard-prod

# Link to Web App
az webapp config appsettings set \
  --resource-group jira-dashboard-prod \
  --name jira-dashboard-app \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY="your-key-here"
```

### View Logs
```bash
# Stream logs in real-time
az container logs --resource-group jira-dashboard-rg --name jira-dashboard -f

# App Service logs
az webapp log tail \
  --resource-group jira-dashboard-prod \
  --name jira-dashboard-app
```

---

## 💰 Cost Estimation

| Resource | Tier | Monthly Cost |
|----------|------|-------------|
| Container Instances | Always on | ~$15-20 |
| App Service Plan | B2 | ~$55 |
| Container Registry | Basic | ~$5 |
| Key Vault | Standard | ~$0.60 |
| Application Insights | Free tier | Free |
| **Total** | | **~$75-100** |

*Prices vary by region and actual usage*

---

## ✅ Deployment Checklist

- [ ] Azure subscription created
- [ ] Azure CLI installed and authenticated
- [ ] Jira credentials ready
- [ ] Docker image tested locally
- [ ] `.env` file NOT committed to git
- [ ] Resource group created
- [ ] Container/Web App deployed
- [ ] Environment variables configured
- [ ] Application accessible via FQDN
- [ ] HTTPS/SSL certificate configured
- [ ] Monitoring enabled
- [ ] Backup/disaster recovery plan

---

## 🚀 Quick Commands Reference

```bash
# List all resources
az resource list --resource-group jira-dashboard-prod

# Delete everything
az group delete --name jira-dashboard-prod --yes

# Check costs
az costmanagement query --resource-group jira-dashboard-prod

# Update container image
az webapp config container set \
  --name jira-dashboard-app \
  --resource-group jira-dashboard-prod \
  --docker-custom-image-name "your-image:latest"

# Restart app
az webapp restart \
  --name jira-dashboard-app \
  --resource-group jira-dashboard-prod
```

---

## 📚 Additional Resources

- [Azure Container Instances Documentation](https://docs.microsoft.com/en-us/azure/container-instances/)
- [Azure App Service Documentation](https://docs.microsoft.com/en-us/azure/app-service/)
- [Azure Key Vault Documentation](https://docs.microsoft.com/en-us/azure/key-vault/)
- [Streamlit Deployment Guide](https://docs.streamlit.io/library/advanced-features/configuration#deployment)

---

**Last Updated:** February 2026
