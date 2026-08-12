# Cloud.ru beta cost baseline

The beta topology is deliberately small: one public 2 vCPU / 4 GiB / 40 GiB VM, one private PostgreSQL 16 Single instance, a public IPv4 address, VPC traffic and a container registry. It has no production Redis, CDN, load balancer or second availability zone.

The Cloud.ru project and current price sheet were verified on 2026-08-12. The service account can read project consumption but cannot read agreement balance or grant details. Project consumption for the preceding 30 days was 0 RUB. Before provisioning, the owner must still confirm the visible balance or applicable grant and authorize the monthly limit.

| Cost driver | Baseline | Control |
| --- | --- | --- |
| VM compute | 2 vCPU / 4 GiB | stop or delete after a closed test window if the beta is paused |
| VM disk | 30 GiB SSD | keep backups outside the VM disk budget |
| Managed PostgreSQL | one private Single instance | start with the smallest supported disk and retain a tested restore |
| Network | one public IP, certificate and normal webhook traffic | set a billing alert before inviting testers |
| Registry | one application repository | expire unaccepted image tags after rollback window |

| Projection | Status |
| --- | --- |
| Grant coverage | UNVERIFIED: agreement-level billing access is not granted to the service account |
| Projected 30-day cost | About 1,355 RUB for VM, 30 GiB SSD and public IP before outbound traffic and Managed PostgreSQL |
| Projected 45-day cost | About 2,033 RUB for VM, 30 GiB SSD and public IP before outbound traffic and Managed PostgreSQL |
| Remaining reserve | UNVERIFIED: depends on the three values above |

The owner must confirm the available Cloud.ru grant/credit and set 25%, 50%, 75% and 90% budget alerts in the console before resource creation. At days 30–40, review average VM CPU/RAM, disk, database size and traffic to decide whether to retain, reduce or increase the baseline. This is a launch gate, not a runtime configuration value.
