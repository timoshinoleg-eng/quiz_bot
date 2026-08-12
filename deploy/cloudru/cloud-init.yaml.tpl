#cloud-config
hostname: ${vm_name}
manage_etc_hosts: true
ssh_pwauth: false
disable_root: true

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

package_update: true
package_upgrade: true
packages:
  - ca-certificates
  - curl

runcmd:
  - [install, -d, -m, "0755", -o, quizdeploy, -g, quizdeploy, /opt/quiz-battle]
