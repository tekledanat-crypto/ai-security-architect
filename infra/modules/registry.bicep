// Azure Container Registry.
// Admin user disabled: images are pulled with managed identity, so there is no
// registry password to leak (CIS 9.5-equivalent for ACR; MCSB IM-1).

param location string
param tags object
param appName string
param uniqueSuffix string
param backendIdentityPrincipalId string
param mcpIdentityPrincipalId string
param frontendIdentityPrincipalId string
param logAnalyticsWorkspaceId string

var registryName = 'cr${appName}${take(uniqueSuffix, 8)}'

resource registry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: registryName
  location: location
  tags: tags
  sku: { name: 'Standard' }
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
    publicNetworkAccess: 'Enabled'
    policies: {
      quarantinePolicy: { status: 'disabled' }
      trustPolicy: { type: 'Notary', status: 'disabled' }
      retentionPolicy: { days: 30, status: 'enabled' }
    }
  }
}

var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource backendPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: registry
  name: guid(registry.id, backendIdentityPrincipalId, acrPullRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: backendIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource mcpPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: registry
  name: guid(registry.id, mcpIdentityPrincipalId, acrPullRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: mcpIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource frontendPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: registry
  name: guid(registry.id, frontendIdentityPrincipalId, acrPullRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: frontendIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: registry
  name: 'diag-${registryName}'
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      { categoryGroup: 'audit', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

output registryName string = registry.name
output loginServer string = registry.properties.loginServer
