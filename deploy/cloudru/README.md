# Cloud.ru infrastructure

This directory creates the bounded public VM layer for `quiz.chatbot24.su`: one
2 vCPU / 4 GiB low-cost VM, one 30 GiB SSD boot disk, one public IPv4 address,
an isolated subnet in the existing VPC, and a security group. SSH is limited to
one operator `/32`; only HTTP and HTTPS are public.

Secrets are never stored in this directory. Supply `TF_VAR_auth_key_id` and
`TF_VAR_auth_secret` in the process environment. Also supply `TF_VAR_project_id`,
`TF_VAR_vpc_id`, and the current `TF_VAR_operator_ip_cidr`.

Install the official Cloud.ru provider binary as described in the Cloud.ru
quick start, then run `terraform init -plugin-dir="$HOME/.terraform.d/plugins"`,
`terraform validate`, and `terraform plan -out=quiz.tfplan`.
Review the plan and the current Cloud.ru balance/grant before `terraform apply`.
Terraform state and plans contain infrastructure metadata and must remain local.

After apply, create an A record for `quiz.chatbot24.su` in Yandex DNS using the
`external_ip` output. Wait for DNS propagation before starting Caddy so ACME can
issue the certificate.
