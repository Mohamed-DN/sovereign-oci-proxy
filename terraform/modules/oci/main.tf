terraform {
  required_version = ">= 1.5.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0.0"
    }
  }
}

resource "oci_core_vcn" "mesh_vcn" {
  compartment_id = var.compartment_id
  cidr_blocks    = [var.vpc_cidr]
  display_name   = "${var.cluster_name}-oci-vcn"
  dns_label      = "sovereignmesh"
}

resource "oci_core_internet_gateway" "mesh_igw" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.mesh_vcn.id
  display_name   = "${var.cluster_name}-igw"
  enabled        = true
}

resource "oci_core_route_table" "mesh_rt" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.mesh_vcn.id
  display_name   = "${var.cluster_name}-route-table"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.mesh_igw.id
  }
}

resource "oci_core_subnet" "mesh_subnet" {
  compartment_id             = var.compartment_id
  vcn_id                     = oci_core_vcn.mesh_vcn.id
  cidr_block                 = var.subnet_cidr
  display_name               = "${var.cluster_name}-subnet"
  route_table_id             = oci_core_route_table.mesh_rt.id
  security_list_ids          = [oci_core_security_list.mesh_sec_list.id]
  prohibit_public_ip_on_vnic = false
}

resource "oci_core_instance" "relay_node" {
  count               = length(var.nodes)
  compartment_id      = var.compartment_id
  availability_domain = var.nodes[count.index].availability_domain
  display_name        = var.nodes[count.index].id
  shape               = var.nodes[count.index].shape

  shape_config {
    ocpus         = var.nodes[count.index].ocpus
    memory_in_gbs = var.nodes[count.index].memory_in_gbs
  }

  source_details {
    source_type = "image"
    source_id   = var.image_id
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.mesh_subnet.id
    display_name     = "${var.nodes[count.index].id}-vnic"
    assign_public_ip = true
    hostname_label   = var.nodes[count.index].id
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = var.nodes[count.index].user_data_base64 != "" ? var.nodes[count.index].user_data_base64 : null
  }
}
