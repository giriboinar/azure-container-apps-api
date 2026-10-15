// Azure Container Apps deployment for the Task API.
// Target scope: resource group. Deploy with:
//   az deployment group create \
//     --resource-group <rg> \
//     --template-file main.bicep \
//     --parameters main.bicepparam
// Nothing in this template provisions paid resources beyond the
// Container Apps consumption workload itself (pay-per-use, scale-to-zero).
// Review costs in the Azure pricing calculator before deploying.

targetScope = 'resourceGroup'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Name of the Container Apps environment.')
param environmentName string = 'aca-env-tasks'

@description('Name of the container app.')
param containerAppName string = 'tasks-api'

@description('Full container image reference, e.g. docker.io/giriboinar/azure-container-apps-api:<tag>. Use an immutable tag for releases.')
param containerImage string = 'docker.io/giriboinar/azure-container-apps-api:latest'

@description('Port the API listens on inside the container.')
param containerPort int = 8000

@description('Minimum replicas. 0 allows scale-to-zero (consumption).')
@minValue(0)
@maxValue(30)
param minReplicas int = 0

@description('Maximum replicas.')
@minValue(1)
@maxValue(30)
param maxReplicas int = 3

// ---- Log Analytics: sink for container logs (30-day retention) ----
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${environmentName}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ---- Container Apps managed environment ----
resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ---- The API itself ----
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        external: true
        targetPort: containerPort
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          name: containerAppName
          image: containerImage
          env: [
            {
              name: 'PORT'
              value: string(containerPort)
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          // Liveness: restart the replica if the process is wedged.
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: containerPort
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              failureThreshold: 3
            }
            // Readiness: pull the replica out of rotation until it can serve.
            {
              type: 'Readiness'
              httpGet: {
                path: '/ready'
                port: containerPort
              }
              initialDelaySeconds: 3
              periodSeconds: 5
              failureThreshold: 3
            }
          ]
        }
      ]
      // Scale on concurrent HTTP requests per replica.
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-concurrency'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

@description('Public URL of the deployed API.')
output fqdn string = containerApp.properties.configuration.ingress.fqdn
