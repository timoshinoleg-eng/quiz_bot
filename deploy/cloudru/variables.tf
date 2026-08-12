variable "project_id" {
  description = "Cloud.ru Evolution project identifier."
  type        = string
}

variable "auth_key_id" {
  description = "Cloud.ru service-account access key identifier."
  type        = string
  sensitive   = true
}

variable "auth_secret" {
  description = "Cloud.ru service-account access key secret."
  type        = string
  sensitive   = true
}

variable "vpc_id" {
  description = "Existing Cloud.ru VPC identifier."
  type        = string
}

variable "operator_ip_cidr" {
  description = "Single trusted operator IPv4 CIDR allowed to reach SSH."
  type        = string

  validation {
    condition     = can(cidrhost(var.operator_ip_cidr, 0))
    error_message = "operator_ip_cidr must be a valid IPv4 CIDR. Use /32 for normal operation."
  }
}

variable "ssh_public_key_path" {
  description = "Dedicated deployment SSH public key."
  type        = string
  default     = "~/.ssh/quiz_cloud_ru_ed25519.pub"
}

variable "zone" {
  description = "Cloud.ru availability zone."
  type        = string
  default     = "ru.AZ-1"
}

variable "subnet_address" {
  description = "CIDR for the isolated quiz application subnet."
  type        = string
  default     = "10.24.0.0/24"
}

variable "vm_name" {
  description = "Cloud.ru VM name."
  type        = string
  default     = "quiz-battle-web-1"
}

variable "flavor" {
  description = "2 vCPU / 4 GiB / 10 percent guaranteed CPU flavor."
  type        = string
  default     = "lowcost10-2-4"
}

variable "disk_size" {
  description = "Boot disk size in GiB."
  type        = number
  default     = 30

  validation {
    condition     = var.disk_size >= 30 && var.disk_size <= 100
    error_message = "disk_size must remain between 30 and 100 GiB for this bounded beta deployment."
  }
}
