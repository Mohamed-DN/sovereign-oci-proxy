variable "cluster_name" {
  type        = string
  description = "Global Sovereign Mesh cluster name"
  default     = "neronet-global-mesh-prod"
}

variable "domain" {
  type        = string
  description = "Cluster root domain"
  default     = "neronet.darknero.com"
}

variable "ssh_port" {
  type        = number
  description = "Standardized hardened SSH management port across all clouds"
  default     = 2222
}

# --- OCI Configuration ---
variable "enable_oci" {
  type        = bool
  description = "Whether to provision OCI resources"
  default     = true
}

variable "oci_compartment_id" {
  type        = string
  description = "OCI Compartment OCID"
  default     = ""
}

variable "oci_nodes" {
  type = list(object({
    id                  = string
    availability_domain = string
    shape               = string
    ocpus               = number
    memory_in_gbs       = number
    decoy_domain        = string
    honeypot_port       = number
    user_data_base64    = optional(string, "")
  }))
  description = "OCI relay nodes"
  default     = []
}

# --- AWS Configuration ---
variable "enable_aws" {
  type        = bool
  description = "Whether to provision AWS resources"
  default     = true
}

variable "aws_region" {
  type        = string
  description = "AWS deployment region"
  default     = "us-east-1"
}

variable "aws_nodes" {
  type = list(object({
    id                = string
    availability_zone = string
    instance_type     = string
    decoy_domain      = string
    honeypot_port     = number
    user_data         = optional(string, "")
  }))
  description = "AWS relay nodes"
  default     = []
}

# --- GCP Configuration ---
variable "enable_gcp" {
  type        = bool
  description = "Whether to provision GCP resources"
  default     = true
}

variable "gcp_project_id" {
  type        = string
  description = "GCP Project ID"
  default     = ""
}

variable "gcp_region" {
  type        = string
  description = "GCP Region"
  default     = "europe-west3"
}

variable "gcp_nodes" {
  type = list(object({
    id            = string
    zone          = string
    machine_type  = string
    decoy_domain  = string
    honeypot_port = number
    startup_script = optional(string, "")
  }))
  description = "GCP relay nodes"
  default     = []
}

# --- DigitalOcean Configuration ---
variable "enable_digitalocean" {
  type        = bool
  description = "Whether to provision DigitalOcean resources"
  default     = true
}

variable "do_region" {
  type        = string
  description = "DigitalOcean region"
  default     = "nyc3"
}

variable "do_nodes" {
  type = list(object({
    id            = string
    size          = string
    decoy_domain  = string
    honeypot_port = number
    user_data     = optional(string, "")
  }))
  description = "DigitalOcean relay nodes"
  default     = []
}

# --- Hetzner Configuration ---
variable "enable_hetzner" {
  type        = bool
  description = "Whether to provision Hetzner resources"
  default     = true
}

variable "hetzner_location" {
  type        = string
  description = "Hetzner location"
  default     = "nbg1"
}

variable "hetzner_nodes" {
  type = list(object({
    id            = string
    server_type   = string
    decoy_domain  = string
    honeypot_port = number
    user_data     = optional(string, "")
  }))
  description = "Hetzner relay nodes"
  default     = []
}

# --- Vultr Configuration ---
variable "enable_vultr" {
  type        = bool
  description = "Whether to provision Vultr resources"
  default     = true
}

variable "vultr_region" {
  type        = string
  description = "Vultr region"
  default     = "nrt"
}

variable "vultr_nodes" {
  type = list(object({
    id            = string
    plan          = string
    decoy_domain  = string
    honeypot_port = number
    user_data     = optional(string, "")
  }))
  description = "Vultr relay nodes"
  default     = []
}
