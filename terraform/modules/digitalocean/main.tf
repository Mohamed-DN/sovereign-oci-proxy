terraform {
  required_version = ">= 1.5.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = ">= 2.0.0"
    }
  }
}

resource "digitalocean_vpc" "mesh_vpc" {
  name     = "${var.cluster_name}-do-vpc"
  region   = var.region
  ip_range = var.vpc_cidr
}

resource "digitalocean_droplet" "relay_node" {
  count      = length(var.nodes)
  image      = var.image
  name       = var.nodes[count.index].id
  region     = var.region
  size       = var.nodes[count.index].size
  vpc_uuid   = digitalocean_vpc.mesh_vpc.id
  ssh_keys   = var.ssh_keys
  user_data  = var.nodes[count.index].user_data != "" ? var.nodes[count.index].user_data : null
  tags       = ["sovereign-mesh", var.cluster_name]
}

resource "digitalocean_floating_ip" "node_ip" {
  count      = length(var.nodes)
  droplet_id = digitalocean_droplet.relay_node[count.index].id
  region     = var.region
}

resource "digitalocean_firewall" "mesh_firewall" {
  name = "${var.cluster_name}-firewall"

  droplet_ids = digitalocean_droplet.relay_node[*].id

  # Inbound Hardened SSH (Port 2222)
  inbound_rule {
    protocol         = "tcp"
    port_range       = tostring(var.ssh_port)
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Inbound HTTP (Port 80)
  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Inbound HTTPS / DERP (Port 443)
  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Inbound STUN (Port 3478 UDP)
  inbound_rule {
    protocol         = "udp"
    port_range       = "3478"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Inbound Honeypot Sensor (Port 8080)
  inbound_rule {
    protocol         = "tcp"
    port_range       = "8080"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Outbound All Traffic
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}
