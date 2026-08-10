#!/usr/bin/env sh
set -eu

test "$(id -u)" -eq 0 || { echo "run as root" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker Engine must be installed first" >&2; exit 1; }

id -u quizdeploy >/dev/null 2>&1 || useradd --create-home --shell /bin/bash quizdeploy
test -s /home/quizdeploy/.ssh/authorized_keys || { echo "install and verify a quizdeploy SSH public key before hardening sshd" >&2; exit 1; }
usermod -aG docker quizdeploy
install -d -m 0750 -o quizdeploy -g quizdeploy /opt/quiz-battle
install -d -m 0700 -o quizdeploy -g quizdeploy /opt/quiz-battle/backups
apt-get update
apt-get install -y --no-install-recommends curl ca-certificates ufw postgresql-client
ufw default deny incoming
ufw default allow outgoing
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow OpenSSH
ufw --force enable
sed -i -E 's/^#?PasswordAuthentication .*/PasswordAuthentication no/; s/^#?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl reload ssh || systemctl reload sshd
echo "host preparation completed"
