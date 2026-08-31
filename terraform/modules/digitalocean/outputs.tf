output "vpc_id" {
  value       = digitalocean_vpc.mesh_vpc.id
  description = "DigitalOcean VPC ID"
}

output "droplet_ids" {
  value       = digitalocean_droplet.relay_node[*].id
  description = "IDs of deployed Droplets"
}

output "public_ips" {
  value       = digitalocean_floating_ip.node_ip[*].ip_address
  description = "Floating/Public IP addresses of deployed DigitalOcean nodes"
}
