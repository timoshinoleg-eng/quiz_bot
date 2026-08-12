output "vm_id" {
  description = "Created VM identifier."
  value       = cloudru_evolution_compute_vm.web.id
}

output "vm_name" {
  description = "Created VM name."
  value       = cloudru_evolution_compute_vm.web.name
}

output "vm_internal_ip" {
  description = "VM private IPv4 address."
  value       = cloudru_evolution_compute_interface.web.ip_address
}

output "external_ip" {
  description = "VM public IPv4 address used for the DNS A record."
  value       = cloudru_evolution_compute_interface.web.external_ip.ip_address
}

output "selected_flavor" {
  description = "Validated compute shape selected from the current project catalog."
  value = {
    name             = local.selected_flavor.name
    cpu              = local.selected_flavor.cpu
    ram_gib          = local.selected_flavor.ram
    oversubscription = local.selected_flavor.oversubscription
  }
}
