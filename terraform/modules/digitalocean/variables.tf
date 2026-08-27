variable "region" {
  type        = string
  description = "DigitalOcean region"
  default     = "nyc3"
}

variable "cluster_name" {
  type        = string
  description = "Cluster identifier name"
  default     = "sovereign-global-mesh"
}

variable "vpc_cidr" {
  type        = string
  description = "DigitalOcean VPC CIDR"
  default     = "10.43.0.0/16"
}

variable "ssh_port" {
  type        = number
  description = "Hardened SSH management port"
  default     = 2222
}

variable "image" {
  type        = string
  description = "Droplet OS image slug"
  default     = "ubuntu-24-04-x64"
}

variable "ssh_keys" {
  type        = list(string)
  description = "List of SSH key IDs or fingerprints"
  default     = []
}

variable "nodes" {
  type = list(object({
    id            = string
    size          = string
    decoy_domain  = string
    honeypot_port = number
    user_data     = optional(string, "")
  }))
  description = "List of DigitalOcean relay nodes"
  default     = []
}
