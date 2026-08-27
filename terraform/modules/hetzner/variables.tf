variable "location" {
  type        = string
  description = "Hetzner Cloud datacenter location"
  default     = "nbg1"
}

variable "cluster_name" {
  type        = string
  description = "Cluster identifier name"
  default     = "sovereign-global-mesh"
}

variable "network_cidr" {
  type        = string
  description = "Hetzner private network IP range"
  default     = "10.44.0.0/16"
}

variable "subnet_cidr" {
  type        = string
  description = "Hetzner subnet IP range"
  default     = "10.44.1.0/24"
}

variable "ssh_port" {
  type        = number
  description = "Hardened SSH management port"
  default     = 2222
}

variable "image" {
  type        = string
  description = "Server OS image"
  default     = "ubuntu-24.04"
}

variable "ssh_keys" {
  type        = list(string)
  description = "List of SSH key names or IDs"
  default     = []
}

variable "nodes" {
  type = list(object({
    id            = string
    server_type   = string
    decoy_domain  = string
    honeypot_port = number
    user_data     = optional(string, "")
  }))
  description = "List of Hetzner relay nodes"
  default     = []
}
