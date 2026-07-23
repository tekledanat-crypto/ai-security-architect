// AI Security Architect — Azure infrastructure
//
// This deploys the architecture the product itself would score well: private data
// plane, managed identity everywhere, no secrets in config, WAF at the edge,
// centralised logging. Shipping infrastructure that fails our own CIS checks would
// be indefensible.
//
// Deploy:
//   az deployment sub create -l westeurope -f infra/main.bicep -p infra/params/prod.bicepparam

targetScope = 'subscription'

@description('Environment name, used in resource naming (e.g. dev, prod).')
@allowed(['dev', 'prod'])
param environmentName string = 'dev'

@description('Azure region for all resources.')
param location string = 'westeurope'

@description('Short application identifier used in resource names.')
@maxLength(12)
param appName string = 'aisecarch'

@description('Container image tag to deploy (typically the git SHA).')
param imageTag string = 'latest'

@description('Object ID of the deploying principal, granted Key Vault admin for bootstrap.')
param deployerObjectId string = ''

@description('Administrator login for PostgreSQL Flexible Server.')
param postgresAdminLogin string = 'psqladmin'

@description('Administrator password for PostgreSQL. Supply via a secure parameter; never commit.')
@secure()
param postgresAdminPassword string

@description('Deploy Azure OpenAI. Set false where quota is unavailable; the app falls back to its fake provider.')
param deployOpenAI bool = true

@description('Entra tenant ID for authentication. Empty uses mock auth (non-production only).')
param entraTenantId string = ''

@description('Entra application (client) ID.')
param entraClientId string = ''

var tags = {
  application: 'ai-security-architect'
  environment: environmentName
  managedBy: 'bicep'
}

var resourceGroupName = 'rg-${appName}-${environmentName}'
var uniqueSuffix = uniqueString(subscription().subscriptionId, resourceGroupName)

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// ── Observability first: everything else diagnoses into it ──
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  scope: rg
  params: {
    location: location
    tags: tags
    appName: appName
    environmentName: environmentName
    uniqueSuffix: uniqueSuffix
  }
}

// ── Network: the private plane the data services live behind ──
module network 'modules/network.bicep' = {
  name: 'network'
  scope: rg
  params: {
    location: location
    tags: tags
    appName: appName
    environmentName: environmentName
  }
}

// ── Identity: one user-assigned identity per workload, no shared credentials ──
module identity 'modules/identity.bicep' = {
  name: 'identity'
  scope: rg
  params: {
    location: location
    tags: tags
    appName: appName
    environmentName: environmentName
  }
}

// ── Secret store ──
module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  scope: rg
  params: {
    location: location
    tags: tags
    appName: appName
    environmentName: environmentName
    uniqueSuffix: uniqueSuffix
    privateEndpointSubnetId: network.outputs.privateEndpointSubnetId
    vnetId: network.outputs.vnetId
    deployerObjectId: deployerObjectId
    backendIdentityPrincipalId: identity.outputs.backendPrincipalId
    logAnalyticsWorkspaceId: monitoring.outputs.workspaceId
  }
}

// ── Data: private-only Postgres ──
module database 'modules/database.bicep' = {
  name: 'database'
  scope: rg
  params: {
    location: location
    tags: tags
    appName: appName
    environmentName: environmentName
    uniqueSuffix: uniqueSuffix
    delegatedSubnetId: network.outputs.postgresSubnetId
    privateDnsZoneId: network.outputs.postgresPrivateDnsZoneId
    administratorLogin: postgresAdminLogin
    administratorPassword: postgresAdminPassword
    keyVaultName: keyVault.outputs.keyVaultName
    logAnalyticsWorkspaceId: monitoring.outputs.workspaceId
  }
}

// ── Container registry ──
module registry 'modules/registry.bicep' = {
  name: 'registry'
  scope: rg
  params: {
    location: location
    tags: tags
    appName: appName
    uniqueSuffix: uniqueSuffix
    backendIdentityPrincipalId: identity.outputs.backendPrincipalId
    mcpIdentityPrincipalId: identity.outputs.mcpPrincipalId
    frontendIdentityPrincipalId: identity.outputs.frontendPrincipalId
    logAnalyticsWorkspaceId: monitoring.outputs.workspaceId
  }
}

// ── AI: private-endpoint-only Azure OpenAI, keyless via managed identity ──
module openai 'modules/openai.bicep' = if (deployOpenAI) {
  name: 'openai'
  scope: rg
  params: {
    location: location
    tags: tags
    appName: appName
    environmentName: environmentName
    uniqueSuffix: uniqueSuffix
    privateEndpointSubnetId: network.outputs.privateEndpointSubnetId
    vnetId: network.outputs.vnetId
    backendIdentityPrincipalId: identity.outputs.backendPrincipalId
    logAnalyticsWorkspaceId: monitoring.outputs.workspaceId
  }
}

// ── Compute ──
module containerApps 'modules/container-apps.bicep' = {
  name: 'containerApps'
  scope: rg
  params: {
    location: location
    tags: tags
    appName: appName
    environmentName: environmentName
    imageTag: imageTag
    infrastructureSubnetId: network.outputs.containerAppsSubnetId
    registryLoginServer: registry.outputs.loginServer
    backendIdentityId: identity.outputs.backendIdentityId
    backendIdentityClientId: identity.outputs.backendClientId
    mcpIdentityId: identity.outputs.mcpIdentityId
    frontendIdentityId: identity.outputs.frontendIdentityId
    keyVaultName: keyVault.outputs.keyVaultName
    postgresFqdn: database.outputs.serverFqdn
    postgresDatabaseName: database.outputs.databaseName
    postgresAdminLogin: postgresAdminLogin
    openAiEndpoint: deployOpenAI ? openai.outputs.endpoint : ''
    openAiDeploymentName: deployOpenAI ? openai.outputs.deploymentName : ''
    entraTenantId: entraTenantId
    entraClientId: entraClientId
    logAnalyticsCustomerId: monitoring.outputs.customerId
    logAnalyticsSharedKey: monitoring.outputs.sharedKey
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
  }
}

output resourceGroupName string = rg.name
output frontendUrl string = containerApps.outputs.frontendUrl
output backendUrl string = containerApps.outputs.backendUrl
output registryLoginServer string = registry.outputs.loginServer
output keyVaultName string = keyVault.outputs.keyVaultName
