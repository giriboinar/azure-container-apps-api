using './main.bicep'

// Example parameters. Override containerImage with the immutable tag
// published by CI, e.g.:
//   --parameters containerImage=docker.io/giriboinar/azure-container-apps-api:sha-abc1234
param environmentName = 'aca-env-tasks'
param containerAppName = 'tasks-api'
param containerImage = 'docker.io/giriboinar/azure-container-apps-api:latest'
param containerPort = 8000
param minReplicas = 0
param maxReplicas = 3
