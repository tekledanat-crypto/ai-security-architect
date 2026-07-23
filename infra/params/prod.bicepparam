using '../main.bicep'

param environmentName = 'prod'
param location = 'westeurope'
param appName = 'aisecarch'
param imageTag = 'latest'
param deployOpenAI = true

// Supplied at deploy time from a secret store. Never committed.
param postgresAdminPassword = ''
