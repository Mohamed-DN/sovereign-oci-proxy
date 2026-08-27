output "network_id" {
  value       = hcloud_network.mesh_network.id
  description = "Hetzner Network ID"
}

output "server_ids" {
  value       = hcloud_server.relay_node[*].id
  description = "IDs of deployed Hetzner servers"
}

output "public_ips" {
  value       = hcloud_server.relay_node[*].ipv4_address
  description = "Primary IPv4 addresses of deployed Hetzner nodes"
}

output "ipv6_addresses" {
  value       = hcloud_server.relay_node[*].ipv6_network
  description = "Assigned IPv6 subnets of deployed Hetzner nodes"
}
