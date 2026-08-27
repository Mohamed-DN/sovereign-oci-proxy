terraform {
  required_version = ">= 1.5.0"
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = ">= 1.45.0"
    }
  }
}

resource "hcloud_network" "mesh_network" {
  name     = "${var.cluster_name}-hcloud-network"
  ip_range = var.network_cidr
}

resource "hcloud_network_subnet" "mesh_subnet" {
  network_id   = hcloud_network.mesh_network.id
  type         = "cloud"
  network_zone = "eu-central"
  ip_range     = var.subnet_cidr
}

resource "hcloud_firewall" "mesh_firewall" {
  name = "${var.cluster_name}-firewall"

  # SSH (Port 2222)
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = tostring(var.ssh_port)
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
    description = "Hardened SSH"
  }

  # HTTP (Port 80)
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "80"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
    description = "ACME HTTP-01"
  }

  # HTTPS / DERP (Port 443)
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "443"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
    description = "Sovereign Proxy DERP / TLS"
  }

  # STUN UDP (Port 3478)
  rule {
    direction = "in"
    protocol  = "udp"
    port      = "3478"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
    description = "Mesh STUN UDP Discovery"
  }

  # Honeypot Sensor (Port 8080)
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "8080"
    source_ips = [
      "0.0.0.0/0",
      "::/0"
    ]
    description = "Active Honeypot Trap"
  }
}

resource "hcloud_server" "relay_node" {
  count        = length(var.nodes)
  name         = var.nodes[count.index].id
  image        = var.image
  server_type  = var.nodes[count.index].server_type
  location     = var.location
  ssh_keys     = var.ssh_keys
  firewall_ids = [hcloud_firewall.mesh_firewall.id]
  user_data    = var.nodes[count.index].user_data != "" ? var.nodes[count.index].user_data : null

  labels = {
    cluster = var.cluster_name
    role    = "relay"
  }
}

resource "hcloud_server_network" "node_net" {
  count     = length(var.nodes)
  server_id = hcloud_server.relay_node[count.index].id
  subnet_id = hcloud_network_subnet.mesh_subnet.id
}
