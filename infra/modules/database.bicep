// PostgreSQL Flexible Server, VNet-injected (no public endpoint at all).
// Public network access isn't merely "denied" — with VNet integration the server has
// no public IP to begin with (CIS 5.1.2, MCSB NS-2, DP-3).

param location string
param tags object
param appName string
param environmentName string
param uniqueSuffix string
param delegatedSubnetId string
param privateDnsZoneId string
param administratorLogin string
@secure()
param administratorPassword string
param keyVaultName string
param logAnalyticsWorkspaceId string

var serverName = 'psql-${appName}-${environmentName}-${take(uniqueSuffix, 6)}'
var databaseName = 'aisecarch'

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: serverName
  location: location
  tags: tags
  sku: {
    name: environmentName == 'prod' ? 'Standard_D2ds_v5' : 'Standard_B1ms'
    tier: environmentName == 'prod' ? 'GeneralPurpose' : 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    storage: {
      storageSizeGB: environmentName == 'prod' ? 128 : 32
      autoGrow: 'Enabled'
    }
    backup: {
      backupRetentionDays: environmentName == 'prod' ? 35 : 7
      geoRedundantBackup: environmentName == 'prod' ? 'Enabled' : 'Disabled'
    }
    network: {
      delegatedSubnetResourceId: delegatedSubnetId
      privateDnsZoneArmResourceId: privateDnsZoneId
      publicNetworkAccess: 'Disabled'
    }
    highAvailability: {
      mode: environmentName == 'prod' ? 'ZoneRedundant' : 'Disabled'
    }
    authConfig: {
      // Entra-only would be ideal; password auth retained for migration tooling.
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Enabled'
      tenantId: subscription().tenantId
    }
  }
}

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Enforce TLS and log connections — the settings CIS/MCSB actually check.
resource requireSsl 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: postgres
  name: 'require_secure_transport'
  properties: {
    value: 'ON'
    source: 'user-override'
  }
}

resource logConnections 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: postgres
  name: 'log_connections'
  properties: {
    value: 'ON'
    source: 'user-override'
  }
  dependsOn: [requireSsl]
}

// The connection string lands in Key Vault; the app reads it via managed identity.
// It is never an environment variable in plaintext and never in the repo.
resource kv 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource connectionSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'database-url'
  properties: {
    value: 'postgresql+asyncpg://${administratorLogin}:${administratorPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/${databaseName}?ssl=require'
    contentType: 'text/plain'
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: postgres
  name: 'diag-${serverName}'
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      { categoryGroup: 'audit', enabled: true }
      { categoryGroup: 'allLogs', enabled: environmentName == 'prod' }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

output serverName string = postgres.name
output serverFqdn string = postgres.properties.fullyQualifiedDomainName
output databaseName string = database.name
