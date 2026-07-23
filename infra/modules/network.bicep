// Virtual network with segregated subnets and private DNS zones.
// Data services are reachable only from inside this network — the single most
// impactful control in the whole design (CIS 4.1.1, 5.1.2; MCSB NS-1, NS-2).

param location string
param tags object
param appName string
param environmentName string

var vnetName = 'vnet-${appName}-${environmentName}'

resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: ['10.20.0.0/16']
    }
    subnets: [
      {
        // Container Apps requires a dedicated, delegated subnet (/23 minimum).
        name: 'snet-container-apps'
        properties: {
          addressPrefix: '10.20.0.0/23'
          delegations: [
            {
              name: 'container-apps-delegation'
              properties: { serviceName: 'Microsoft.App/environments' }
            }
          ]
          networkSecurityGroup: { id: nsgContainerApps.id }
          privateEndpointNetworkPolicies: 'Enabled'
        }
      }
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: '10.20.2.0/24'
          networkSecurityGroup: { id: nsgPrivateEndpoints.id }
          // Must be Disabled for private endpoints to attach.
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      {
        name: 'snet-postgres'
        properties: {
          addressPrefix: '10.20.3.0/24'
          delegations: [
            {
              name: 'postgres-delegation'
              properties: { serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers' }
            }
          ]
          networkSecurityGroup: { id: nsgPostgres.id }
        }
      }
    ]
  }
}

// Deny-by-default posture: NSGs carry only the rules each tier needs.
resource nsgContainerApps 'Microsoft.Network/networkSecurityGroups@2024-01-01' = {
  name: 'nsg-${appName}-${environmentName}-aca'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowHttpsInbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '443'
        }
      }
      {
        name: 'DenyAllInbound'
        properties: {
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}

resource nsgPrivateEndpoints 'Microsoft.Network/networkSecurityGroups@2024-01-01' = {
  name: 'nsg-${appName}-${environmentName}-pe'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowVnetInbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          destinationPortRange: '*'
        }
      }
      {
        name: 'DenyInternetInbound'
        properties: {
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}

resource nsgPostgres 'Microsoft.Network/networkSecurityGroups@2024-01-01' = {
  name: 'nsg-${appName}-${environmentName}-pg'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowVnetPostgres'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '5432'
        }
      }
      {
        name: 'DenyAllInbound'
        properties: {
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}

// Private DNS zones: without these, private endpoints resolve to public IPs and the
// whole private-plane design silently does nothing.
resource postgresDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.postgres.database.azure.com'
  location: 'global'
  tags: tags
}

resource postgresDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: postgresDnsZone
  name: 'link-${vnetName}'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnet.id }
  }
}

output vnetId string = vnet.id
output vnetName string = vnet.name
output containerAppsSubnetId string = vnet.properties.subnets[0].id
output privateEndpointSubnetId string = vnet.properties.subnets[1].id
output postgresSubnetId string = vnet.properties.subnets[2].id
output postgresPrivateDnsZoneId string = postgresDnsZone.id
