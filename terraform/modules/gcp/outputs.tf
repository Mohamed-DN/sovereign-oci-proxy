output "network_id" {
  value       = google_compute_network.mesh_network.id
  description = "GCP VPC Network ID"
}

output "subnet_id" {
  value       = google_compute_subnetwork.mesh_subnet.id
  description = "GCP Subnetwork ID"
}

output "instance_ids" {
  value       = google_compute_instance.relay_node[*].id
  description = "GCP Compute Engine instance IDs"
}

output "public_ips" {
  value       = google_compute_address.static_ip[*].address
  description = "Static external IP addresses of deployed GCP nodes"
}
