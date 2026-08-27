variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "region" {
  type        = string
  description = "GCP Region"
  default     = "europe-west3"
}

variable "cluster_name" {
  type        = string
  description = "Cluster identifier name"
  default     = "sovereign-global-mesh"
}

variable "vpc_cidr" {
  type        = string
  description = "GCP Subnet CIDR block"
  default     = "10.42.1.0/24"
}

variable "ssh_port" {
  type        = number
  description = "Hardened SSH management port"
  default     = 2222
}

variable "boot_image" {
  type        = string
  description = "Compute instance OS boot image"
  default     = "ubuntu-os-cloud/ubuntu-2404-lts-arm64"
}

variable "nodes" {
  type = list(object({
    id            = string
    zone          = string
    machine_type  = string
    decoy_domain  = string
    honeypot_port = number
    startup_script = optional(string, "")
  }))
  description = "List of GCP relay/control nodes"
  default     = []
}
