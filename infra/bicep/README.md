# Infrastructure (Bicep)

Deploys the Task API to **Azure Container Apps** (consumption plan).

## What gets created

- Log Analytics workspace (`<env>-logs`, 30-day retention)
- Container Apps managed environment (wired to Log Analytics)
- Container App `tasks-api` with external HTTPS ingress, liveness/readiness
  probes, and HTTP-concurrency autoscaling (0–3 replicas)

## Deploy

```bash
# 1. Log in and pick the subscription
az login
az account set --subscription "<subscription-id>"

# 2. Create the resource group (or reuse one)
az group create --name rg-tasks-api --location centralindia

# 3. Deploy
az deployment group create \
  --resource-group rg-tasks-api \
  --template-file main.bicep \
  --parameters main.bicepparam

# 4. Deploy a real image tag (immutable tags for releases)
az deployment group create \
  --resource-group rg-tasks-api \
  --template-file main.bicep \
  --parameters main.bicepparam \
  --parameters containerImage=docker.io/giriboinar/azure-container-apps-api:sha-<sha>
```

The deployment outputs the public `fqdn` — smoke-test it:

```bash
curl -s "https://<fqdn>/health"
```

## Cost notes

- Container Apps **consumption** = pay per vCPU-second / GiB-second actually
  used. With `minReplicas: 0` an idle API costs ~nothing.
- Log Analytics Pay-As-You-Go ingestion applies; 30-day retention is the
  workspace default here.
- Check the Azure pricing calculator for your region before deploying.
  Nothing is deployed by CI — deployment is always a deliberate manual step.
