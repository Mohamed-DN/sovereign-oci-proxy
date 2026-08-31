terraform {
  required_version = ">= 1.5.0"
  required_providers {
    vultr = {
      source  = "vultr/vultr"
      version = ">= 2.19.0"
    }
  }
}

resource "vultr_vpc" "mesh_vpc" {
  description = "${var.cluster_name}-vultr-vpc"
  region      = var.region
  v4_subnet   = split("/", var.vpc_cidr)[0]
  v4_subnet_mask = tonumber(split("/", var.vpc_cidr)[1])
}

resource "vultr_firewall_group" "mesh_fw_group" {
  description = "${var.cluster_name}-firewall-group"
}

# SSH Port 2222
resource "vultr_firewall_rule" "ssh" {
  firewall_group_id = vultr_firewall_group.mesh_fw_group.id
  protocol          = "tcp"
  ip_type           = "v4"
  subnet            = "0.0.0.0"
  subnet_size       = 0
  port              = tostring(var.ssh_port)
  notes             = "Hardened SSH"
}

# HTTP Port 80
resource "vultr_firewall_rule" "http" {
  firewall_group_id = vultr_firewall_group.mesh_fw_group.id
  protocol          = "tcp"
  ip_type           = "v4"
  subnet            = "0.0.0.0"
  subnet_size       = 0
  port              = "80"
  notes             = "ACME HTTP-01"
}

# HTTPS / DERP Port 443
resource "vultr_firewall_rule" "https_derp" {
  firewall_group_id = vultr_firewall_group.mesh_fw_group.id
  protocol          = "tcp"
  ip_type           = "v4"
  subnet            = "0.0.0.0"
  subnet_size       = 0
  port              = "443"
  notes             = "Sovereign Proxy DERP / TLS"
}

# STUN Port 3478 UDP
resource "vultr_firewall_rule" "stun_udp" {
  firewall_group_id = vultr_firewall_group.mesh_fw_group.id
  protocol          = "udp"
  ip_type           = "v4"
  subnet            = "0.0.0.0"
  subnet_size       = 0
  port              = "3478"
  notes             = "Mesh STUN UDP Discovery"
}

# Honeypot Port 8080
resource "vultr_firewall_rule" "honeypot" {
  firewall_group_id = vultr_firewall_group.mesh_fw_group.id
  protocol          = "tcp"
  ip_type           = "v4"
  subnet            = "0.0.0.0"
  subnet_size       = 0
  port              = "8080"
  notes             = "Active Honeypot Trap"
}

resource "vultr_instance" "relay_node" {
  count             = length(var.nodes)
  label             = var.nodes[count.index].id
  hostname          = var.nodes[count.index].id
  region            = var.region
  plan              = var.nodes[count.index].plan
  os_id             = var.os_id
  firewall_group_id = vultr_firewall_group.mesh_fw_group.id
  vpc_ids           = [vultr_vpc.mesh_vpc.id]
  ssh_key_ids       = var.ssh_key_ids
  user_data         = var.nodes[count.index].user_data != "" ? var.nodes[count.index].user_data : null
  enable_ipv6       = true
  backups           = "disabled"
  ddos_protection   = false
  tags              = ["sovereign-mesh", var.cluster_name]
}
