variable "region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}

variable "cluster_name" {
  type        = string
  description = "Cluster identifier name"
  default     = "sovereign-global-mesh"
}

variable "vpc_cidr" {
  type        = string
  description = "AWS VPC CIDR"
  default     = "10.41.0.0/16"
}

variable "subnet_cidr" {
  type        = string
  description = "AWS Subnet CIDR"
  default     = "10.41.1.0/24"
}

variable "ssh_port" {
  type        = number
  description = "Hardened SSH management port"
  default     = 2222
}

variable "ami_id" {
  type        = string
  description = "AMI ID (Ubuntu 24.04 LTS ARM64/AMD64)"
  default     = ""
}

variable "key_name" {
  type        = string
  description = "EC2 KeyPair name"
  default     = ""
}

variable "nodes" {
  type = list(object({
    id                = string
    availability_zone = string
    instance_type     = string
    decoy_domain      = string
    honeypot_port     = number
    user_data         = optional(string, "")
  }))
  description = "List of static AWS relay nodes"
  default     = []
}

# ==============================================================================
# Auto-Scaling Configuration Variables
# ==============================================================================

variable "enable_autoscaling" {
  type        = bool
  description = "Enable AWS Auto Scaling Group (ASG) and dynamic scaling policies"
  default     = false
}

variable "autoscaling_instance_type" {
  type        = string
  description = "EC2 instance type for autoscaled relay nodes (Graviton/ARM64 or x86_64)"
  default     = "c7g.large"
}

variable "asg_min_size" {
  type        = number
  description = "Minimum capacity of the Auto Scaling Group"
  default     = 2
}

variable "asg_max_size" {
  type        = number
  description = "Maximum capacity of the Auto Scaling Group"
  default     = 20
}

variable "asg_desired_capacity" {
  type        = number
  description = "Desired capacity of the Auto Scaling Group"
  default     = 4
}

variable "asg_cooldown_seconds" {
  type        = number
  description = "Cooldown period in seconds between scaling actions"
  default     = 300
}

variable "asg_target_cpu_utilization" {
  type        = number
  description = "Target average CPU utilization percentage for ASG Target Tracking"
  default     = 60.0
}

variable "asg_scale_out_step" {
  type        = number
  description = "Number of instances to add during sudden high-traffic scale-out"
  default     = 2
}

variable "asg_scale_in_step" {
  type        = number
  description = "Number of instances to remove during low-traffic scale-in"
  default     = -1
}

variable "asg_network_in_threshold_bytes" {
  type        = number
  description = "NetworkIn threshold in bytes/period for step scale-out alarm (~100MB/s)"
  default     = 100000000
}

variable "asg_network_in_low_threshold_bytes" {
  type        = number
  description = "NetworkIn threshold in bytes/period for step scale-in alarm (~10MB/s)"
  default     = 10000000
}

variable "autoscaling_user_data" {
  type        = string
  description = "Custom cloud-init user-data for autoscaled EC2 instances"
  default     = ""
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of VPC Subnet IDs for multi-AZ ASG deployment (falls back to single mesh_subnet if empty)"
  default     = []
}

