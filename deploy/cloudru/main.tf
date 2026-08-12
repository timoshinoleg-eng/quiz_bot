data "cloudru_evolution_compute_image_collection" "ubuntu" {
  project_id = var.project_id
  page_size  = 100
}

data "cloudru_evolution_compute_flavor_collection" "available" {
  project_id = var.project_id
  page_size  = 100
}

locals {
  ubuntu_image_id = one([
    for image in data.cloudru_evolution_compute_image_collection.ubuntu.images : image.id
    if image.name == "ubuntu-22.04"
  ])

  selected_flavor = one([
    for flavor in data.cloudru_evolution_compute_flavor_collection.available.flavors : flavor
    if flavor.name == var.flavor
  ])

  cloud_config = templatefile("${path.module}/cloud-init.yaml.tpl", {
    ssh_public_key = trimspace(file(pathexpand(var.ssh_public_key_path)))
    vm_name        = var.vm_name
  })
}

resource "cloudru_evolution_compute_subnet" "quiz" {
  project_id = var.project_id
  name       = "quiz-battle-subnet"

  zone_identifier = {
    name = var.zone
  }

  description    = "Private subnet for Quiz Battle beta"
  subnet_address = var.subnet_address
  routed_network = true
  # Cloud.ru requires the first subnet in a new VDC to be its default subnet.
  default = true
  vpc_id  = var.vpc_id

  dns_servers = {
    value = ["1.1.1.1", "8.8.8.8"]
  }
}

resource "cloudru_evolution_compute_security_group" "web" {
  project_id = var.project_id
  name       = "quiz-battle-web"

  zone_identifier = {
    name = var.zone
  }

  description = "Least-privilege ingress for Quiz Battle HTTPS host"
}

resource "cloudru_evolution_compute_security_group_rule" "ssh" {
  security_group_id = cloudru_evolution_compute_security_group.web.id
  direction         = "TRAFFIC_DIRECTION_INGRESS"
  ether_type        = "ETHER_TYPE_IPV4"
  ip_protocol       = "IP_PROTOCOL_TCP"
  port_range        = "22:22"
  remote_ip_prefix  = var.operator_ip_cidr
  description       = "SSH from the current operator IP only"
}

resource "cloudru_evolution_compute_security_group_rule" "http" {
  security_group_id = cloudru_evolution_compute_security_group.web.id
  direction         = "TRAFFIC_DIRECTION_INGRESS"
  ether_type        = "ETHER_TYPE_IPV4"
  ip_protocol       = "IP_PROTOCOL_TCP"
  port_range        = "80:80"
  remote_ip_prefix  = "0.0.0.0/0"
  description       = "HTTP for ACME redirect and certificate validation"
}

resource "cloudru_evolution_compute_security_group_rule" "https" {
  security_group_id = cloudru_evolution_compute_security_group.web.id
  direction         = "TRAFFIC_DIRECTION_INGRESS"
  ether_type        = "ETHER_TYPE_IPV4"
  ip_protocol       = "IP_PROTOCOL_TCP"
  port_range        = "443:443"
  remote_ip_prefix  = "0.0.0.0/0"
  description       = "Public HTTPS"
}

resource "cloudru_evolution_compute_security_group_rule" "egress_tcp" {
  security_group_id = cloudru_evolution_compute_security_group.web.id
  direction         = "TRAFFIC_DIRECTION_EGRESS"
  ether_type        = "ETHER_TYPE_IPV4"
  ip_protocol       = "IP_PROTOCOL_TCP"
  port_range        = "1:65535"
  remote_ip_prefix  = "0.0.0.0/0"
  description       = "Outbound TCP for APIs, image pulls and updates"
}

resource "cloudru_evolution_compute_security_group_rule" "egress_udp" {
  security_group_id = cloudru_evolution_compute_security_group.web.id
  direction         = "TRAFFIC_DIRECTION_EGRESS"
  ether_type        = "ETHER_TYPE_IPV4"
  ip_protocol       = "IP_PROTOCOL_UDP"
  port_range        = "1:65535"
  remote_ip_prefix  = "0.0.0.0/0"
  description       = "Outbound UDP for DNS and time synchronization"
}

resource "cloudru_evolution_compute_disk" "boot" {
  project_id = var.project_id
  name       = "quiz-battle-web-1-boot"
  size       = var.disk_size

  zone_identifier = {
    name = var.zone
  }

  disk_type_identifier = {
    name = "SSD"
  }

  description = "Quiz Battle Ubuntu boot disk"
  bootable    = true
  image_id    = local.ubuntu_image_id
  encrypted   = false
  readonly    = false
  shared      = false
}

resource "cloudru_evolution_compute_interface" "web" {
  project_id = var.project_id
  name       = "quiz-battle-web-1-nic"

  zone_identifier = {
    name = var.zone
  }

  description                = "Quiz Battle public interface"
  subnet_id                  = cloudru_evolution_compute_subnet.quiz.id
  interface_security_enabled = true

  security_groups_identifiers = {
    value = [{ id = cloudru_evolution_compute_security_group.web.id }]
  }

  external_ip_specs = {
    new_external_ip = true
  }

  type = "INTERFACE_TYPE_REGULAR"
}

resource "cloudru_evolution_compute_vm" "web" {
  project_id = var.project_id
  name       = var.vm_name

  zone_identifier = {
    name = var.zone
  }

  flavor_identifier = {
    name = local.selected_flavor.name
  }

  description = "Quiz Battle MAX Mini App beta host"

  disk_identifiers = [{
    disk_id = cloudru_evolution_compute_disk.boot.id
  }]

  network_interfaces = [{
    interface_id = cloudru_evolution_compute_interface.web.id
  }]

  cloud_init_userdata = base64encode(local.cloud_config)
}
