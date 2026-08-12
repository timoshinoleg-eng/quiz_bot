#cloud-config
hostname: ${vm_name}
manage_etc_hosts: true
ssh_pwauth: false
disable_root: true
ssh_deletekeys: false

users:
  - default
  - name: quizdeploy
    gecos: Quiz Battle deployment user
    groups: [sudo]
    shell: /bin/bash
    sudo: ["ALL=(ALL) NOPASSWD:ALL"]
    lock_passwd: true
    ssh_authorized_keys:
      - ${ssh_public_key}

package_update: false
package_upgrade: false
packages:
  - ca-certificates
  - curl
  - openssh-server
  - qemu-guest-agent

bootcmd:
  - [systemctl, enable, ssh]
  - [systemctl, start, ssh]

runcmd:
  - [install, -d, -m, "0755", -o, quizdeploy, -g, quizdeploy, /opt/quiz-battle]
  - [systemctl, enable, --now, qemu-guest-agent]
  - [systemctl, restart, ssh]
