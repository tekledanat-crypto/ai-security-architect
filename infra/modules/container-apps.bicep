// Container Apps environment and the three workloads.
//
// Topology mirrors the trust zones the product itself teaches:
//   Internet → frontend (external ingress)
//            → backend  (internal ingress only)
//            → mcp      (internal ingress only)
// Only the frontend is reachable from outside. The MCP server — which holds the
// scoring engine — is not internet-addressable at all.

param location string
param tags object
param appName string
param environmentName string
param imageTag string
param infrastructureSubnetId string
param registryLoginServer string
param backendIdentityId string
param backendIdentityClientId string
param mcpIdentityId string
param frontendIdentityId string
param keyVaultName string
param postgresFqdn string
param postgresDatabaseName string
param postgresAdminLogin string
param openAiEndpoint string
param openAiDeploymentName string

@description('Entra tenant ID. Empty falls back to mock auth (non-production only).')
param entraTenantId string = ''

@description('Entra application (client) ID.')
param entraClientId string = ''
param logAnalyticsCustomerId string
@secure()
param logAnalyticsSharedKey string
param appInsightsConnectionString string

var envName = 'cae-${appName}-${environmentName}'
var isProd = environmentName == 'prod'

var frontendAppName = 'ca-${appName}-${environmentName}-frontend'
var backendAppName = 'ca-${appName}-${environmentName}-backend'
var mcpAppName = 'ca-${appName}-${environmentName}-mcp'

// Container Apps FQDNs are deterministic: <app>.<env default domain>. Composing them
// avoids a circular reference between the frontend and backend (each needs the
// other's URL), which would otherwise fail deployment.
var frontendFqdn = '${frontendAppName}.${environment.properties.defaultDomain}'
var backendFqdn = '${backendAppName}.${environment.properties.defaultDomain}'
var mcpFqdn = '${mcpAppName}.${environment.properties.defaultDomain}'

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: envName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: infrastructureSubnetId
      internal: false // frontend needs public ingress; internal apps stay internal
    }
    zoneRedundant: isProd
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

// ── MCP server: internal only. The engine is not on the internet. ──
resource mcpApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: mcpAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${mcpIdentityId}': {} }
  }
  properties: {
    managedEnvironmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 8100
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: registryLoginServer
          identity: mcpIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'mcp-server'
          image: '${registryLoginServer}/mcp-server:${imageTag}'
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'MCP_HTTP_PORT', value: '8100' }
            { name: 'LOG_LEVEL', value: isProd ? 'INFO' : 'DEBUG' }
          ]
          probes: [
            {
              type: 'Readiness'
              httpGet: { path: '/health', port: 8100 }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: isProd ? 1 : 0
        maxReplicas: isProd ? 5 : 2
      }
    }
  }
}

// ── Backend: internal only. Reached by the frontend, never directly. ──
resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: backendAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${backendIdentityId}': {} }
  }
  properties: {
    managedEnvironmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
        corsPolicy: {
          allowedOrigins: ['https://${frontendFqdn}']
          allowedMethods: ['GET', 'POST', 'OPTIONS']
          allowCredentials: true
        }
      }
      registries: [
        {
          server: registryLoginServer
          identity: backendIdentityId
        }
      ]
      // Secrets resolve from Key Vault via managed identity at runtime — the value
      // never appears in the template, the repo, or the deployment log.
      secrets: [
        {
          name: 'database-url'
          keyVaultUrl: 'https://${keyVaultName}${environment().suffixes.keyvaultDns}/secrets/database-url'
          identity: backendIdentityId
        }
        {
          name: 'session-secret'
          keyVaultUrl: 'https://${keyVaultName}${environment().suffixes.keyvaultDns}/secrets/session-secret'
          identity: backendIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: '${registryLoginServer}/backend:${imageTag}'
          resources: { cpu: json('1.0'), memory: '2Gi' }
          env: [
            { name: 'DATABASE_URL', secretRef: 'database-url' }
            { name: 'SESSION_SECRET', secretRef: 'session-secret' }
            { name: 'AI_PROVIDER', value: empty(openAiEndpoint) ? 'fake' : 'azure-openai' }
            { name: 'AZURE_OPENAI_ENDPOINT', value: openAiEndpoint }
            { name: 'AZURE_OPENAI_DEPLOYMENT', value: openAiDeploymentName }
            // Keyless: the SDK authenticates with this identity, no API key exists.
            { name: 'AZURE_CLIENT_ID', value: backendIdentityClientId }
            { name: 'MCP_TRANSPORT', value: 'http' }
            { name: 'MCP_HTTP_URL', value: 'https://${mcpFqdn}/mcp' }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
            { name: 'POSTGRES_HOST', value: postgresFqdn }
            { name: 'POSTGRES_DB', value: postgresDatabaseName }
            { name: 'POSTGRES_USER', value: postgresAdminLogin }
            { name: 'LOG_LEVEL', value: isProd ? 'INFO' : 'DEBUG' }
            { name: 'APP_ENV', value: isProd ? 'production' : 'development' }
            // Entra when configured; the app refuses to start with mock auth in prod.
            { name: 'AUTH_PROVIDER', value: empty(entraTenantId) ? 'mock' : 'entra' }
            { name: 'ENTRA_TENANT_ID', value: entraTenantId }
            { name: 'ENTRA_CLIENT_ID', value: entraClientId }
          ]
          probes: [
            {
              type: 'Readiness'
              httpGet: { path: '/api/health', port: 8000 }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
            {
              type: 'Liveness'
              httpGet: { path: '/api/health', port: 8000 }
              initialDelaySeconds: 20
              periodSeconds: 30
            }
          ]
        }
      ]
      scale: {
        minReplicas: isProd ? 2 : 0
        maxReplicas: isProd ? 10 : 3
        rules: [
          {
            name: 'http-scaling'
            http: { metadata: { concurrentRequests: '50' } }
          }
        ]
      }
    }
  }
}

// ── Frontend: the only public surface. ──
resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: frontendAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${frontendIdentityId}': {} }
  }
  properties: {
    managedEnvironmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 3000
        transport: 'http'
        allowInsecure: false // HTTPS only (CIS 9.2)
        traffic: [
          { latestRevision: true, weight: 100 }
        ]
      }
      registries: [
        {
          server: registryLoginServer
          identity: frontendIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: '${registryLoginServer}/frontend:${imageTag}'
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'BACKEND_URL', value: 'https://${backendFqdn}' }
            { name: 'NODE_ENV', value: 'production' }
          ]
          probes: [
            {
              type: 'Readiness'
              httpGet: { path: '/', port: 3000 }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: isProd ? 1 : 0
        maxReplicas: isProd ? 5 : 2
      }
    }
  }
  dependsOn: [backendApp]
}

output frontendUrl string = 'https://${frontendFqdn}'
output backendUrl string = 'https://${backendFqdn}'
output mcpUrl string = 'https://${mcpFqdn}'
