# Cloud.ru beta cost baseline

The beta topology is deliberately small: one public 2 vCPU / 4 GiB / 40 GiB VM, one private PostgreSQL 16 Single instance, a public IPv4 address, VPC traffic and a container registry. It has no production Redis, CDN, load balancer or second availability zone.

The current Cloud.ru account, project, grant and price sheet were not authenticated during the local implementation, so no rouble amount is claimed here. Before provisioning, price the exact region and billing period in the Cloud.ru console and record the result in the launch evidence.

| Cost driver | Baseline | Control |
| --- | --- | --- |
| VM compute | 2 vCPU / 4 GiB | stop or delete after a closed test window if the beta is paused |
| VM disk | 40 GiB SSD | keep backups outside the VM disk budget |
| Managed PostgreSQL | one private Single instance | start with the smallest supported disk and retain a tested restore |
| Network | one public IP, certificate and normal webhook traffic | set a billing alert before inviting testers |
| Registry | one application repository | expire unaccepted image tags after rollback window |

| Projection | Status |
| --- | --- |
| Grant coverage | UNVERIFIED: console/API login was not established |
| Projected 30-day cost | UNVERIFIED: requires current region price sheet and grant scope |
| Projected 45-day cost | UNVERIFIED: requires current region price sheet and grant scope |
| Remaining reserve | UNVERIFIED: depends on the three values above |

The owner must confirm the available Cloud.ru grant/credit and set 25%, 50%, 75% and 90% budget alerts in the console before resource creation. At days 30–40, review average VM CPU/RAM, disk, database size and traffic to decide whether to retain, reduce or increase the baseline. This is a launch gate, not a runtime configuration value.
