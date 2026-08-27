# Oracle Cloud Infrastructure (OCI) Auto-Scaling Module
# Defines Instance Configuration, Instance Pool, and Metric-Based Autoscaling Configuration

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_id
}

# 1. Instance Configuration for Autoscaled Relay Nodes
resource "oci_core_instance_configuration" "relay_instance_config" {
  count          = var.enable_autoscaling ? 1 : 0
  compartment_id = var.compartment_id
  display_name   = "${var.cluster_name}-relay-instance-config"

  instance_details {
    instance_type = "compute"

    launch_details {
      compartment_id = var.compartment_id
      shape          = var.autoscaling_instance_shape

      shape_config {
        ocpus         = var.autoscaling_ocpus
        memory_in_gbs = var.autoscaling_memory_in_gbs
      }

      source_details {
        source_type = "image"
        image_id    = var.image_id
      }

      create_vnic_details {
        subnet_id        = oci_core_subnet.mesh_subnet.id
        display_name     = "${var.cluster_name}-relay-pool-vnic"
        assign_public_ip = true
        hostname_label   = "relay-pool"
      }

      metadata = {
        ssh_authorized_keys = var.ssh_public_key
        user_data           = var.autoscaling_user_data_base64 != "" ? var.autoscaling_user_data_base64 : null
      }
    }
  }
}

# 2. Instance Pool managing dynamic fleet across Availability Domains
resource "oci_core_instance_pool" "relay_pool" {
  count                     = var.enable_autoscaling ? 1 : 0
  compartment_id            = var.compartment_id
  instance_configuration_id = oci_core_instance_configuration.relay_instance_config[0].id
  display_name              = "${var.cluster_name}-relay-pool"
  size                      = var.autoscaling_initial_size

  placement_configurations {
    availability_domain = var.availability_domain != "" ? var.availability_domain : data.oci_identity_availability_domains.ads.availability_domains[0].name
    primary_subnet_id   = oci_core_subnet.mesh_subnet.id
  }

  lifecycle {
    ignore_changes = [size] # Allow autoscaling policy to dynamically adjust pool size
  }
}

# 3. Autoscaling Configuration with Metric-Based Threshold Policies
resource "oci_autoscaling_auto_scaling_configuration" "relay_autoscaling" {
  count                = var.enable_autoscaling ? 1 : 0
  compartment_id       = var.compartment_id
  display_name         = "${var.cluster_name}-relay-autoscaling"
  cool_down_in_seconds = var.autoscaling_cooldown_seconds
  is_enabled           = true

  auto_scaling_resources {
    id   = oci_core_instance_pool.relay_pool[0].id
    type = "instancePool"
  }

  policies {
    policy_type  = "threshold"
    display_name = "${var.cluster_name}-threshold-policy"

    capacity {
      initial = var.autoscaling_initial_size
      min     = var.autoscaling_min_size
      max     = var.autoscaling_max_size
    }

    # Scale-Out Rule: High CPU utilization across the pool
    rules {
      display_name = "ScaleOutOnHighCPU"

      action {
        type  = "CHANGE_COUNT_BY"
        value = var.scale_out_step
      }

      metric {
        metric_type = "CPU_UTILIZATION"

        threshold {
          operator = "GT"
          value    = var.scale_out_cpu_threshold
        }
      }
    }

    # Scale-In Rule: Low CPU utilization indicating idle capacity
    rules {
      display_name = "ScaleInOnLowCPU"

      action {
        type  = "CHANGE_COUNT_BY"
        value = var.scale_in_step
      }

      metric {
        metric_type = "CPU_UTILIZATION"

        threshold {
          operator = "LT"
          value    = var.scale_in_cpu_threshold
        }
      }
    }
  }
}
