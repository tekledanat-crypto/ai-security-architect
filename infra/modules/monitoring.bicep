// Log Analytics + Application Insights.
// Deployed first so every other resource can send diagnostics here from creation
// (CIS 5.1.1 auditing, MCSB LT-1/LT-3, NIST AU-2).

param location string
param tags object
param appName string
param environmentName string
param uniqueSuffix string

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${appName}-${environmentName}-${uniqueSuffix}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: environmentName == 'prod' ? 90 : 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${appName}-${environmentName}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
    IngestionMode: 'LogAnalytics'
    DisableLocalAuth: false
  }
}

output workspaceId string = workspace.id
output customerId string = workspace.properties.customerId
#disable-next-line outputs-should-not-contain-secrets
output sharedKey string = workspace.listKeys().primarySharedKey
output appInsightsConnectionString string = appInsights.properties.ConnectionString
