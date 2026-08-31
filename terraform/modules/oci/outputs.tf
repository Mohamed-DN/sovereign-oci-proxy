output "vcn_id" {
  value       = oci_core_vcn.mesh_vcn.id
  description = "OCID of the created VCN"
}

output "subnet_id" {
  value       = oci_core_subnet.mesh_subnet.id
  description = "OCID of the regional subnet"
}

output "instance_ids" {
  value       = oci_core_instance.relay_node[*].id
  description = "OCIDs of deployed instances"
}

output "public_ips" {
  value       = oci_core_instance.relay_node[*].public_ip
  description = "Assigned public IP addresses of deployed OCI nodes"
}

output "instance_pool_id" {
  value       = try(oci_core_instance_pool.relay_pool[0].id, null)
  description = "OCID of the autoscaled OCI instance pool"
}

output "autoscaling_configuration_id" {
  value       = try(oci_autoscaling_auto_scaling_configuration.relay_autoscaling[0].id, null)
  description = "OCID of the OCI autoscaling configuration"
}

