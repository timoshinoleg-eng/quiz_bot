# GitVerse CI/CD

The authoritative GitVerse workflow and secret contract are maintained in [GITVERSE_CI_CD.md](GITVERSE_CI_CD.md). This compatibility filename exists because the production acceptance contract names `GITVERSE_CICD.md` explicitly.

The deployment workflow builds an immutable SHA-tagged Linux image only from `main`, pushes it to the configured Cloud.ru registry, then connects to the pinned SSH host key and invokes the VM deployment script. It never sends bot tokens, database credentials or the VM runtime `.env` through CI.
