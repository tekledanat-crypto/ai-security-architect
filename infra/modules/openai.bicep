// Azure OpenAI: private endpoint only, local (key) auth disabled.
//
// disableLocalAuth means there is no API key to steal — access is via managed
// identity and Entra RBAC only. This is what "keyless" in ADR-0001 actually buys.

param location string
param tags object
param appName string
param environmentName string
param uniqueSuffix string
param privateEndpointSubnetId string
param vnetId string
param backendIdentityPrincipalId string
param logAnalyticsWorkspaceId string

@description('Model deployment name the application requests.')
param deploymentName string = 'gpt-4o'

@description('Model version to deploy.')
param modelName string = 'gpt-4o'
param modelVersion string = '2024-08-06'

@description('Tokens-per-minute quota (thousands). Also the cost guardrail (OWASP LLM10).')
param capacity int = 30

var accountName = 'oai-${appName}-${environmentName}-${take(uniqueSuffix, 6)}'

resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: accountName
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: accountName
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
    // No API keys. Entra identity only.
    disableLocalAuth: true
  }
}

resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: deploymentName
  sku: {
    name: 'Standard'
    capacity: capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2024-01-01' = {
  name: 'pe-${accountName}'
  location: location
  tags: tags
  properties: {
    subnet: { id: privateEndpointSubnetId }
    privateLinkServiceConnections: [
      {
        name: 'plsc-${accountName}'
        properties: {
          privateLinkServiceId: openai.id
          groupIds: ['account']
        }
      }
    ]
  }
}

resource dnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.openai.azure.com'
  location: 'global'
  tags: tags
}

resource dnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: dnsZone
  name: 'link-oai'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnetId }
  }
}

resource dnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-01-01' = {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'openai-config'
        properties: { privateDnsZoneId: dnsZone.id }
      }
    ]
  }
}

// Cognitive Services OpenAI User: inference only, no management rights.
var openAiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource backendOpenAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: openai
  name: guid(openai.id, backendIdentityPrincipalId, openAiUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUserRoleId)
    principalId: backendIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: openai
  name: 'diag-${accountName}'
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      { categoryGroup: 'audit', enabled: true }
      { categoryGroup: 'allLogs', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

output accountName string = openai.name
output endpoint string = openai.properties.endpoint
output deploymentName string = deployment.name
