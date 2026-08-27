output "vpc_id" {
  value       = vultr_vpc.mesh_vpc.id
  description = "Vultr VPC 2.0 ID"
}

output "instance_ids" {
  value       = vultr_instance.relay_node[*].id
  description = "IDs of deployed Vultr instances"
}

output "public_ips" {
  value       = vultr_instance.relay_node[*].main_ip
  description = "Main IPv4 addresses of deployed Vultr nodes"
}

output "ipv6_addresses" {
  value       = vultr_instance.relay_node[*].v6_main_ip
  description = "Main IPv6 addresses of deployed Vultr nodes"
}
