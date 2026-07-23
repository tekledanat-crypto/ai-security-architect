// Key Vault: private-endpoint only, RBAC (not access policies), purge protection on.
// These are exactly the properties the product's own engine checks (CIS 8.1, 8.4).

param location string
param tags object
param appName string
param environmentName string
param uniqueSuffix string
param privateEndpointSubnetId string
param vnetId string
param deployerObjectId string
param backendIdentityPrincipalId string
param logAnalyticsWorkspaceId string

var keyVaultName = 'kv-${appName}-${take(uniqueSuffix, 8)}'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    // RBAC over access policies: auditable, consistent with the rest of Azure.
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: environmentName == 'prod' ? 90 : 7
    // Purge protection is irreversible once enabled — deliberate for prod only.
    enablePurgeProtection: environmentName == 'prod' ? true : null
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
  }
}

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2024-01-01' = {
  name: 'pe-${keyVaultName}'
  location: location
  tags: tags
  properties: {
    subnet: { id: privateEndpointSubnetId }
    privateLinkServiceConnections: [
      {
        name: 'plsc-${keyVaultName}'
        properties: {
          privateLinkServiceId: keyVault.id
          groupIds: ['vault']
        }
      }
    ]
  }
}

resource dnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.vaultcore.azure.net'
  location: 'global'
  tags: tags
}

resource dnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: dnsZone
  name: 'link-kv'
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
        name: 'vault-config'
        properties: { privateDnsZoneId: dnsZone.id }
      }
    ]
  }
}

// Built-in role IDs (stable GUIDs).
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'
var keyVaultAdminRoleId = '00482a5a-887f-4fb3-b363-3b7fe8e74483'

// The backend reads secrets; it does not manage them.
resource backendSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: keyVault
  name: guid(keyVault.id, backendIdentityPrincipalId, keyVaultSecretsUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: backendIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Bootstrap only: lets the deploying principal seed secrets. Optional by design.
resource deployerAdmin 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerObjectId)) {
  scope: keyVault
  name: guid(keyVault.id, deployerObjectId, keyVaultAdminRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultAdminRoleId)
    principalId: deployerObjectId
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: keyVault
  name: 'diag-${keyVaultName}'
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        categoryGroup: 'audit'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

output keyVaultName string = keyVault.name
output keyVaultId string = keyVault.id
output keyVaultUri string = keyVault.properties.vaultUri
