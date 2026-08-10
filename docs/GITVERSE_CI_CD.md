# GitVerse CI/CD for the production beta

The repository has two GitVerse workflows:

| Workflow | Trigger | Result |
| --- | --- | --- |
| `.gitverse/workflows/ci.yml` | pull request, push to `main`, manual | backend tests, content bootstrap/audit, Mini App typecheck/test/build, production image import check |
| `.gitverse/workflows/deploy-production.yml` | manual on `main` only | builds one immutable image, pushes it to Cloud.ru registry, then invokes the VM deploy script |

Enable CI/CD in the private GitVerse repository settings after the first push. GitVerse documents its workflow model and activation in its [CI/CD documentation](https://gitverse.ru/docs/cicd/). A mirrored repository cannot be used as the production deployment source; use a native private repository.

## Repository variables

Create these non-secret GitVerse variables exactly:

| Variable | Meaning |
| --- | --- |
| `CLOUD_RU_REGISTRY_URI` | full image repository without a tag |
| `CLOUD_RU_REGISTRY_HOST` | registry host accepted by `docker login` |
| `DEPLOY_HOST` | VM public DNS name or IP |
| `DEPLOY_USER` | `quizdeploy` |
| `PUBLIC_HOST` | public DNS hostname, without `https://` |
| `ACME_EMAIL` | certificate expiry contact |

## Protected secrets

Create these protected, production-environment secrets:

| Secret | Purpose |
| --- | --- |
| `CLOUD_RU_REGISTRY_USERNAME` / `CLOUD_RU_REGISTRY_PASSWORD` | push and VM pull from the Cloud.ru container registry |
| `DEPLOY_SSH_PRIVATE_KEY` | private half of the dedicated `quizdeploy` key |
| `DEPLOY_SSH_KNOWN_HOSTS` | pinned host-key line obtained during VM creation |

The VM runtime `.env`, bot tokens, database password and webhook secrets do not belong in GitVerse variables or GitVerse secrets: they are installed once on the VM and never transmitted by a workflow.

## First run acceptance

1. Push the committed source to the private GitVerse repository using Credential Manager authentication.
2. Confirm the CI workflow is enabled and wait for its three jobs to finish.
3. Create the Cloud.ru registry repository, VM and runtime `.env`; establish a fresh SSH connection that verifies the pinned host key.
4. Add the variables/secrets above, manually run `Deploy production beta` from `main`, and record the immutable `IMAGE_REF` from the job log.
5. Require `/health`, `/ready`, platform webhook verification and two-user smoke before enabling any public promotion.

The workflow uses an explicitly supplied known-host key and never runs `ssh-keyscan`; a changed host key is a deployment failure requiring investigation.
