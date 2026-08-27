variable "compartment_id" {
  type        = string
  description = "OCI Compartment OCID"
}

variable "cluster_name" {
  type        = string
  description = "Cluster identifier name"
  default     = "sovereign-global-mesh"
}

variable "vpc_cidr" {
  type        = string
  description = "VCN CIDR block"
  default     = "10.40.0.0/16"
}

variable "subnet_cidr" {
  type        = string
  description = "Subnet CIDR block"
  default     = "10.40.1.0/24"
}

variable "ssh_port" {
  type        = number
  description = "Hardened SSH port"
  default     = 2222
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key for instance access"
  default     = ""
}

variable "image_id" {
  type        = string
  description = "OCI image OCID (Ubuntu 22.04/24.04 or Oracle Linux 9)"
  default     = "ocid1.image.oc1..oraclelinux9"
}

variable "nodes" {
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
  description = "List of static OCI relay/control nodes to deploy"
  default     = []
}

# ==============================================================================
# Auto-Scaling Configuration Variables
# ==============================================================================

variable "enable_autoscaling" {
  type        = bool
  description = "Enable OCI Instance Pool and Metric-Based Autoscaling Configuration"
  default     = false
}

variable "autoscaling_instance_shape" {
  type        = string
  description = "Compute shape for autoscaled relay instances"
  default     = "VM.Standard.A1.Flex"
}

variable "autoscaling_ocpus" {
  type        = number
  description = "Number of OCPUs for autoscaled instances (Flex shapes)"
  default     = 4
}

variable "autoscaling_memory_in_gbs" {
  type        = number
  description = "RAM size in GB for autoscaled instances (Flex shapes)"
  default     = 24
}

variable "autoscaling_min_size" {
  type        = number
  description = "Minimum number of instances in the OCI instance pool"
  default     = 2
}

variable "autoscaling_max_size" {
  type        = number
  description = "Maximum number of instances in the OCI instance pool"
  default     = 20
}

variable "autoscaling_initial_size" {
  type        = number
  description = "Initial desired number of instances in the OCI instance pool"
  default     = 4
}

variable "autoscaling_cooldown_seconds" {
  type        = number
  description = "Autoscaling policy cooldown period in seconds"
  default     = 300
}

variable "scale_out_cpu_threshold" {
  type        = number
  description = "CPU utilization percentage threshold to trigger scale-out"
  default     = 65
}

variable "scale_in_cpu_threshold" {
  type        = number
  description = "CPU utilization percentage threshold to trigger scale-in"
  default     = 30
}

variable "scale_out_step" {
  type        = number
  description = "Number of instances to add during a scale-out event"
  default     = 2
}

variable "scale_in_step" {
  type        = number
  description = "Number of instances to remove during a scale-in event"
  default     = -1
}

variable "autoscaling_user_data_base64" {
  type        = string
  description = "Base64-encoded cloud-init script for autoscaled instance enrollment"
  default     = ""
}

variable "availability_domain" {
  type        = string
  description = "Target availability domain name for instance pool placement (leave blank for AD discovery)"
  default     = ""
}

