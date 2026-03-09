# Infrastructure-Aware Feature Flags

The FastAPI backend can enable optional API modules based on environment variables. This allows OpenTofu (or Helm) to inject feature flags and configuration when provisioning infrastructure, so the same application image behaves differently per environment without code changes.

## Environment variable convention

- **Feature flag:** `FEATURE_<NAME>_ENABLED` — set to `true`, `1`, `yes`, or `on` to enable the module. Any other value (or unset) disables it.
- **Module-specific config:** Each module may require additional env vars (e.g. `KEYCLOAK_URL`, `KEYCLOAK_REALM`). See the module section below.

Examples:

- `FEATURE_KEYCLOAK_ENABLED=true` — enable Keycloak auth integration.
- `FEATURE_ELASTICACHE_ENABLED=false` — leave advanced cache routes disabled.

## Backend behaviour

- At startup, the backend checks each known feature flag. If enabled, it imports the corresponding router from `src/backend/modules/` and mounts it under a fixed prefix (e.g. `/api/auth/keycloak`).
- If the module import fails (e.g. optional dependency not installed), the app logs a warning and continues; the rest of the API remains available.
- The frontend can discover enabled features via `GET /api/capabilities`, which returns a `features` object (e.g. `{ "keycloak": true }`).

## Helm: passing env to the API container

The Helm chart already supports arbitrary env vars for the API via `api.env` (list of `name`/`value`). See [platform/deploy/helm/qasic/values.yaml](../../platform/deploy/helm/qasic/values.yaml) (`api.env: []`).

**Example: enable Keycloak and set its URL**

Using `--set`:

```bash
helm upgrade --install qasic platform/deploy/helm/qasic -n qasic --create-namespace \
  --set image.registry=your-registry/ \
  --set api.env[0].name=FEATURE_KEYCLOAK_ENABLED \
  --set api.env[0].value=true \
  --set api.env[1].name=KEYCLOAK_URL \
  --set api.env[1].value=https://auth.example.com/realms/qasic \
  --set api.env[2].name=KEYCLOAK_REALM \
  --set api.env[2].value=qasic
```

Or in a custom values file:

```yaml
api:
  env:
    - name: FEATURE_KEYCLOAK_ENABLED
      value: "true"
    - name: KEYCLOAK_URL
      value: "https://auth.example.com/realms/qasic"
    - name: KEYCLOAK_REALM
      value: "qasic"
    - name: KEYCLOAK_CLIENT_ID
      value: "qasic-frontend"
```

Then: `helm upgrade --install qasic ... -f my-values.yaml`

## OpenTofu: wiring when using a Helm release

When you add a `helm_release` resource (or equivalent) in OpenTofu to deploy the QASIC Helm chart, pass feature flags and module config from Tofu outputs.

Example (hypothetical Keycloak module):

```hcl
# When a Keycloak module exists and is conditionally created:
module "aws_keycloak" {
  count  = var.create_keycloak ? 1 : 0
  source = "./modules/aws_keycloak"
  # ...
}

resource "helm_release" "qasic" {
  # ...
  set {
    name  = "api.env.FEATURE_KEYCLOAK_ENABLED"
    value = var.create_keycloak ? "true" : "false"
  }
  set {
    name  = "api.env.KEYCLOAK_URL"
    value = var.create_keycloak ? module.aws_keycloak[0].url : ""
  }
  set {
    name  = "api.env.KEYCLOAK_REALM"
    value = var.create_keycloak ? module.aws_keycloak[0].realm : "qasic"
  }
}
```

The exact `set` syntax depends on how your Helm chart exposes nested values (e.g. `api.env` as a list may require `dynamic "set"` blocks or a generated values file). The contract is: the API container must receive `FEATURE_*_ENABLED` and any module-specific vars so the backend can enable the right routes.

## Available modules

| Feature name | Env flag | Module-specific env | Mounted at |
|--------------|----------|---------------------|------------|
| Keycloak     | `FEATURE_KEYCLOAK_ENABLED` | `KEYCLOAK_URL` (required), `KEYCLOAK_REALM` (default `qasic`), `KEYCLOAK_CLIENT_ID` (default `qasic-frontend`) | `/api/auth/keycloak` |

When Keycloak is enabled, the frontend can call `GET /api/auth/keycloak/config` to obtain `{ "url", "realm", "client_id" }` and initialize its auth client.
