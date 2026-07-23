// One user-assigned managed identity per workload.
//
// Separate identities rather than one shared: least privilege is only meaningful if
// the backend's Key Vault access doesn't implicitly grant the frontend the same.
// (CIS 9.5, MCSB IM-1/PA-7.)

param location string
param tags object
param appName string
param environmentName string

resource backendIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${appName}-${environmentName}-backend'
  location: location
  tags: tags
}

resource mcpIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${appName}-${environmentName}-mcp'
  location: location
  tags: tags
}

resource frontendIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${appName}-${environmentName}-frontend'
  location: location
  tags: tags
}

output backendIdentityId string = backendIdentity.id
output backendPrincipalId string = backendIdentity.properties.principalId
output backendClientId string = backendIdentity.properties.clientId
output mcpIdentityId string = mcpIdentity.id
output mcpPrincipalId string = mcpIdentity.properties.principalId
output frontendIdentityId string = frontendIdentity.id
output frontendPrincipalId string = frontendIdentity.properties.principalId
