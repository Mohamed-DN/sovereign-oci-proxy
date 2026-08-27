terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0"
    }
  }
}

resource "google_compute_network" "mesh_network" {
  name                    = "${var.cluster_name}-gcp-vpc"
  auto_create_subnetworks = false
  project                 = var.project_id
}

resource "google_compute_subnetwork" "mesh_subnet" {
  name          = "${var.cluster_name}-subnet"
  ip_cidr_range = var.vpc_cidr
  region        = var.region
  network       = google_compute_network.mesh_network.id
  project       = var.project_id
}

resource "google_compute_firewall" "allow_mesh_inbound" {
  name    = "${var.cluster_name}-fw-ingress"
  network = google_compute_network.mesh_network.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = [tostring(var.ssh_port), "80", "443", "8080"]
  }

  allow {
    protocol = "udp"
    ports    = ["3478"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["sovereign-node"]
}

resource "google_compute_address" "static_ip" {
  count   = length(var.nodes)
  name    = "${var.nodes[count.index].id}-ip"
  region  = var.region
  project = var.project_id
}

resource "google_compute_instance" "relay_node" {
  count        = length(var.nodes)
  name         = var.nodes[count.index].id
  machine_type = var.nodes[count.index].machine_type
  zone         = var.nodes[count.index].zone
  project      = var.project_id
  tags         = ["sovereign-node"]

  boot_disk {
    initialize_params {
      image = var.boot_image
      size  = 30
      type  = "pd-balanced"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.mesh_subnet.id
    access_config {
      nat_ip = google_compute_address.static_ip[count.index].address
    }
  }

  metadata = {
    startup-script = var.nodes[count.index].startup_script != "" ? var.nodes[count.index].startup_script : null
    enable-oslogin = "TRUE"
  }
}
