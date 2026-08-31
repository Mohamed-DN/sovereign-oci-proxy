output "oci_nodes_public_ips" {
  value       = try(module.oci_cluster[0].public_ips, [])
  description = "Public IPs of OCI relay nodes"
}

output "aws_nodes_public_ips" {
  value       = try(module.aws_cluster[0].public_ips, [])
  description = "Public IPs of AWS relay nodes"
}

output "gcp_nodes_public_ips" {
  value       = try(module.gcp_cluster[0].public_ips, [])
  description = "Public IPs of GCP relay nodes"
}

output "digitalocean_nodes_public_ips" {
  value       = try(module.digitalocean_cluster[0].public_ips, [])
  description = "Public IPs of DigitalOcean relay nodes"
}

output "hetzner_nodes_public_ips" {
  value       = try(module.hetzner_cluster[0].public_ips, [])
  description = "Public IPs of Hetzner relay nodes"
}

output "vultr_nodes_public_ips" {
  value       = try(module.vultr_cluster[0].public_ips, [])
  description = "Public IPs of Vultr relay nodes"
}

output "cluster_endpoints_summary" {
  value = {
    cluster_name = var.cluster_name
    domain       = var.domain
    ssh_port     = var.ssh_port
    providers_active = compact([
      var.enable_oci ? "oci" : "",
      var.enable_aws ? "aws" : "",
      var.enable_gcp ? "gcp" : "",
      var.enable_digitalocean ? "digitalocean" : "",
      var.enable_hetzner ? "hetzner" : "",
      var.enable_vultr ? "vultr" : "",
    ])
  }
  description = "Master summary of multi-cloud deployment"
}
