variable "region" {
  type        = string
  description = "Vultr region code"
  default     = "nrt"
}

variable "cluster_name" {
  type        = string
  description = "Cluster identifier name"
  default     = "sovereign-global-mesh"
}

variable "vpc_cidr" {
  type        = string
  description = "Vultr VPC 2.0 CIDR block"
  default     = "10.45.0.0/16"
}

variable "ssh_port" {
  type        = number
  description = "Hardened SSH management port"
  default     = 2222
}

variable "os_id" {
  type        = number
  description = "Vultr OS ID (Ubuntu 24.04 x64 / ARM)"
  default     = 2284 # Ubuntu 24.04 LTS x64
}

variable "ssh_key_ids" {
  type        = list(string)
  description = "List of SSH key IDs"
  default     = []
}

variable "nodes" {
  type = list(object({
    id            = string
    plan          = string
    decoy_domain  = string
    honeypot_port = number
    user_data     = optional(string, "")
  }))
  description = "List of Vultr relay nodes"
  default     = []
}
