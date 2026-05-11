targetScope = 'resourceGroup'

@description('Primary Azure region')
param location string = 'canadacentral'

@description('Prefix used to name all resources')
param namePrefix string = 'neolore-queue'

@description('Initial placeholder image for the Container Apps Job (replaced by CI/CD)')
param containerJobImage string = 'mcr.microsoft.com/k8se/quickstart-jobs:latest'

@secure()
@description('MotherDuck read-write token')
param motherduckTokenRw string

@secure()
@description('Versature OAuth client id')
param versatureClientId string

@secure()
@description('Versature OAuth client secret')
param versatureClientSecret string

@secure()
@description('Admin API key for the manual-trigger Function')
param adminApiKey string

@description('Queue IDs (non-secret config) - order: english, french, ai_overflow_en, ai_overflow_fr')
param queueEnglish string = '8020'
param queueFrench string = '8021'
param queueAiOverflowEn string = '8030'
param queueAiOverflowFr string = '8031'
param dnisPrimary string = '16135949199'
param dnisSecondary string = '6135949199'
param motherduckDatabase string = 'csh_analytics_v2'
param timezone string = 'America/Toronto'

var resourceSuffix = uniqueString(resourceGroup().id)
var storageAccountName = take(replace('${namePrefix}st${resourceSuffix}', '-', ''), 24)
var keyVaultName = take('${namePrefix}-kv-${resourceSuffix}', 24)
var acrName = take(replace('${namePrefix}acr${resourceSuffix}', '-', ''), 50)
var logAnalyticsName = '${namePrefix}-law'
var appInsightsName = '${namePrefix}-ai'
var containerAppsEnvName = '${namePrefix}-cae'
var containerAppJobName = '${namePrefix}-pipeline-job'
var functionAppName = '${namePrefix}-fn'
var functionStorageName = take(replace('${namePrefix}fn${resourceSuffix}', '-', ''), 24)
var swaName = '${namePrefix}-dashboard'
var pipelineIdentityName = 'id-${namePrefix}-pipeline'
var functionIdentityName = 'id-${namePrefix}-function'

// ---------- User-assigned managed identities ----------

resource pipelineIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-07-31-preview' = {
  name: pipelineIdentityName
  location: location
}

resource functionIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-07-31-preview' = {
  name: functionIdentityName
  location: location
}

// ---------- Key Vault + secrets ----------

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enabledForDeployment: false
    enabledForTemplateDeployment: false
    enabledForDiskEncryption: false
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

resource secretMotherduckTokenRw 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'motherduck-token-rw'
  properties: { value: motherduckTokenRw }
}

resource secretVersatureClientId 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'versature-client-id'
  properties: { value: versatureClientId }
}

resource secretVersatureClientSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'versature-client-secret'
  properties: { value: versatureClientSecret }
}

resource secretAdminApiKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'admin-api-key'
  properties: { value: adminApiKey }
}

// ---------- Log Analytics + App Insights ----------

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ---------- Storage account + reports container ----------

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    allowBlobPublicAccess: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    cors: {
      corsRules: [
        {
          allowedOrigins: [ 'https://*.azurestaticapps.net' ]
          allowedMethods: [ 'GET', 'HEAD' ]
          allowedHeaders: [ '*' ]
          exposedHeaders: [ '*' ]
          maxAgeInSeconds: 3600
        }
      ]
    }
  }
}

resource reportsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'reports'
  properties: {
    publicAccess: 'Blob'
  }
}

resource blobDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: blobService
  name: 'blob-to-law'
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      { category: 'StorageWrite', enabled: true }
      { category: 'StorageDelete', enabled: true }
    ]
  }
}

var roleStorageBlobDataContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource pipelineBlobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: reportsContainer
  name: guid(reportsContainer.id, pipelineIdentity.id, roleStorageBlobDataContributor)
  properties: {
    principalId: pipelineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleStorageBlobDataContributor)
  }
}

var roleKeyVaultSecretsUser = '4633458b-17de-408a-b874-0445c86b69e6'

resource pipelineKvMd 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: secretMotherduckTokenRw
  name: guid(secretMotherduckTokenRw.id, pipelineIdentity.id)
  properties: {
    principalId: pipelineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleKeyVaultSecretsUser)
  }
}

resource pipelineKvVersId 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: secretVersatureClientId
  name: guid(secretVersatureClientId.id, pipelineIdentity.id)
  properties: {
    principalId: pipelineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleKeyVaultSecretsUser)
  }
}

resource pipelineKvVersSecret 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: secretVersatureClientSecret
  name: guid(secretVersatureClientSecret.id, pipelineIdentity.id)
  properties: {
    principalId: pipelineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleKeyVaultSecretsUser)
  }
}

resource functionKvAdmin 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: secretAdminApiKey
  name: guid(secretAdminApiKey.id, functionIdentity.id)
  properties: {
    principalId: functionIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleKeyVaultSecretsUser)
  }
}

// ---------- Azure Container Registry ----------

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

var roleAcrPull = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource pipelineAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, pipelineIdentity.id, roleAcrPull)
  properties: {
    principalId: pipelineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleAcrPull)
  }
}

// ---------- Container Apps Environment ----------

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppsEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: listKeys(logAnalytics.id, '2023-09-01').primarySharedKey
      }
    }
  }
}

// ---------- Container Apps Job ----------

resource containerAppJob 'Microsoft.App/jobs@2024-03-01' = {
  name: containerAppJobName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${pipelineIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerAppsEnv.id
    configuration: {
      triggerType: 'Schedule'
      replicaTimeout: 3600
      replicaRetryLimit: 0
      scheduleTriggerConfig: {
        cronExpression: '0 9 1 * *'
        parallelism: 1
        replicaCompletionCount: 1
      }
      registries: [
        {
          server: '${acr.name}.azurecr.io'
          identity: pipelineIdentity.id
        }
      ]
      secrets: [
        { name: 'motherduck-token-rw', identity: pipelineIdentity.id, keyVaultUrl: '${keyVault.properties.vaultUri}secrets/motherduck-token-rw' }
        { name: 'versature-client-id', identity: pipelineIdentity.id, keyVaultUrl: '${keyVault.properties.vaultUri}secrets/versature-client-id' }
        { name: 'versature-client-secret', identity: pipelineIdentity.id, keyVaultUrl: '${keyVault.properties.vaultUri}secrets/versature-client-secret' }
      ]
    }
    template: {
      containers: [
        {
          name: 'pipeline'
          image: containerJobImage
          resources: { cpu: 1, memory: '2Gi' }
          env: [
            { name: 'PERIOD_MODE', value: 'previous-month' }
            { name: 'PERIOD_TYPE', value: 'month' }
            { name: 'API_CACHE_MODE', value: 'auto' }
            { name: 'WRITE_STORE', value: '1' }
            { name: 'SOURCE', value: 'api' }
            { name: 'DATA_DIR', value: '/data' }
            { name: 'TIMEZONE', value: timezone }
            { name: 'MOTHERDUCK_DATABASE', value: motherduckDatabase }
            { name: 'QUEUE_ENGLISH', value: queueEnglish }
            { name: 'QUEUE_FRENCH', value: queueFrench }
            { name: 'QUEUE_AI_OVERFLOW_EN', value: queueAiOverflowEn }
            { name: 'QUEUE_AI_OVERFLOW_FR', value: queueAiOverflowFr }
            { name: 'DNIS_PRIMARY', value: dnisPrimary }
            { name: 'DNIS_SECONDARY', value: dnisSecondary }
            { name: 'AZURE_CLIENT_ID', value: pipelineIdentity.properties.clientId }
            { name: 'REPORTS_STORAGE_ACCOUNT_URL', value: 'https://${storage.name}.blob.${environment().suffixes.storage}' }
            { name: 'REPORTS_CONTAINER', value: 'reports' }
            { name: 'MOTHERDUCK_TOKEN_RW', secretRef: 'motherduck-token-rw' }
            { name: 'VERSATURE_CLIENT_ID', secretRef: 'versature-client-id' }
            { name: 'VERSATURE_CLIENT_SECRET', secretRef: 'versature-client-secret' }
          ]
        }
      ]
    }
  }
}

// Container Apps Jobs Operator: grants jobs/start/action, jobs/stop/action, read.
var roleContainerAppJobsOperator = 'b9a307c4-5aa3-4b52-ba60-2b17c136cd7b'

resource functionJobsOperator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: containerAppJob
  name: guid(containerAppJob.id, functionIdentity.id, roleContainerAppJobsOperator)
  properties: {
    principalId: functionIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleContainerAppJobsOperator)
  }
}

output pipelineIdentityResourceId string = pipelineIdentity.id
output functionIdentityResourceId string = functionIdentity.id
output keyVaultUri string = keyVault.properties.vaultUri
output containerAppJobName string = containerAppJob.name
output acrLoginServer string = '${acr.name}.azurecr.io'
output storageAccountName string = storage.name
output reportsBaseUrl string = '${storage.properties.primaryEndpoints.blob}reports'
