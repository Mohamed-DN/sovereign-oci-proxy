terraform {
  required_version = ">= 1.5.0"
  required_providers {
    oci          = { source = "oracle/oci", version = ">= 5.0.0" }
    aws          = { source = "hashicorp/aws", version = ">= 5.0.0" }
    google       = { source = "hashicorp/google", version = ">= 5.0.0" }
    digitalocean = { source = "digitalocean/digitalocean", version = ">= 2.0.0" }
    hcloud       = { source = "hetznercloud/hcloud", version = ">= 1.45.0" }
    vultr        = { source = "vultr/vultr", version = ">= 2.19.0" }
  }
}

# 1. Oracle Cloud Infrastructure Module
module "oci_cluster" {
  count          = var.enable_oci ? 1 : 0
  source         = "../../modules/oci"
  compartment_id = var.oci_compartment_id
  cluster_name   = var.cluster_name
  ssh_port       = var.ssh_port
  nodes          = var.oci_nodes
}

# 2. Amazon Web Services Module
module "aws_cluster" {
  count        = var.enable_aws ? 1 : 0
  source       = "../../modules/aws"
  region       = var.aws_region
  cluster_name = var.cluster_name
  ssh_port     = var.ssh_port
  nodes        = var.aws_nodes
}

# 3. Google Cloud Platform Module
module "gcp_cluster" {
  count        = var.enable_gcp ? 1 : 0
  source       = "../../modules/gcp"
  project_id   = var.gcp_project_id
  region       = var.gcp_region
  cluster_name = var.cluster_name
  ssh_port     = var.ssh_port
  nodes        = var.gcp_nodes
}

# 4. DigitalOcean Module
module "digitalocean_cluster" {
  count        = var.enable_digitalocean ? 1 : 0
  source       = "../../modules/digitalocean"
  region       = var.do_region
  cluster_name = var.cluster_name
  ssh_port     = var.ssh_port
  nodes        = var.do_nodes
}

# 5. Hetzner Cloud Module
module "hetzner_cluster" {
  count        = var.enable_hetzner ? 1 : 0
  source       = "../../modules/hetzner"
  location     = var.hetzner_location
  cluster_name = var.cluster_name
  ssh_port     = var.ssh_port
  nodes        = var.hetzner_nodes
}

# 6. Vultr Module
module "vultr_cluster" {
  count        = var.enable_vultr ? 1 : 0
  source       = "../../modules/vultr"
  region       = var.vultr_region
  cluster_name = var.cluster_name
  ssh_port     = var.ssh_port
  nodes        = var.vultr_nodes
}
