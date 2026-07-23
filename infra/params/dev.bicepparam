using '../main.bicep'

param environmentName = 'dev'
param location = 'westeurope'
param appName = 'aisecarch'
param imageTag = 'latest'

// Azure OpenAI quota is not always available on trial subscriptions. With this false
// the app runs on its fake provider — the deterministic engine needs no model, so the
// product is still fully demonstrable (ADR-0001).
param deployOpenAI = false

// Supplied at deploy time: az deployment ... --parameters postgresAdminPassword=...
// Never committed. CI passes it from an environment secret.
param postgresAdminPassword = ''
