# TeamCity Migration Design

## Goal

Move CI/CD ownership for NeoLore Queue Analytics from GitHub Actions to TeamCity while preserving the current Azure runtime architecture: Container Apps Job for the pipeline, Azure Function App for manual execution, Blob Storage for report bundles, and Azure Static Web Apps for the dashboard.

## Architecture

TeamCity owns the build graph through versioned Kotlin DSL committed under `.teamcity/`. The project defines one CI configuration and four deployment configurations:

- `CI` runs root Python tests, Function tests, dashboard tests, and a Docker image build.
- `Deploy Pipeline Image` builds and pushes `neolore-pipeline:<revision>` and `:latest` to ACR, then updates the Container Apps Job image.
- `Deploy Function` vendors Function dependencies, zips the Function App, uploads it to the existing release blob container, updates `WEBSITE_RUN_FROM_PACKAGE`, and syncs triggers.
- `Deploy Dashboard` builds `dashboard/dist` and deploys it to Azure Static Web Apps.
- `Deploy All` chains the three deployment configurations at the same VCS revision.

The TeamCity Python runner is intentionally avoided because TeamCity build #1 failed when the runner attempted `pip install teamcity-messages --user` on an Ubuntu 24.04 agent governed by PEP 668. Script steps create virtual environments explicitly.

## Authentication

GitHub Actions used Azure OIDC. TeamCity will use a service principal stored in TeamCity secure parameters:

- `env.AZURE_CLIENT_ID`
- `env.AZURE_CLIENT_SECRET`
- `env.AZURE_TENANT_ID`
- `env.AZURE_SUBSCRIPTION_ID`

The service principal needs permission to push to ACR, update the Container Apps Job, upload to the Function release blob container, update Function App settings, and invoke `syncfunctiontriggers`.

Additional TeamCity parameters:

- `env.AZURE_RESOURCE_GROUP`
- `env.ACR_NAME`
- `env.CONTAINER_APP_JOB_NAME`
- `env.FUNCTION_APP_NAME`
- `env.FUNCTION_STORAGE_ACCOUNT`
- `env.FUNCTION_RELEASE_CONTAINER` optional, defaults to `scm-releases`
- `env.VITE_REPORTS_BASE_URL`
- `env.SWA_DEPLOYMENT_TOKEN`

## Cutover

GitHub workflow files remain as manual fallback jobs only. Automatic push deployment is removed from GitHub Actions so TeamCity is the single push-based deploy owner.
