variable "tenancy_ocid" {
  description = "OCI Tenancy OCID"
  type        = string
}

variable "user_ocid" {
  description = "OCI User OCID"
  type        = string
}

variable "fingerprint" {
  description = "API Key Fingerprint"
  type        = string
}

variable "private_key_path" {
  description = "Path to the API Private Key"
  type        = string
}

variable "region" {
  description = "OCI Region (e.g., eu-milan-1)"
  type        = string
  default     = "eu-milan-1"
}

variable "compartment_ocid" {
  description = "Compartment OCID where resources will be created"
  type        = string
}

variable "ssh_public_key" {
  description = "Public SSH key for the compute instance"
  type        = string
}

variable "instance_name" {
  description = "Name of the proxy instance"
  type        = string
  default     = "sovereign-proxy"
}
