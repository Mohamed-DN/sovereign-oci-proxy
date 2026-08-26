terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 5.0"
    }
  }
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

# --- Network Infrastructure ---

resource "oci_core_vcn" "sovereign_vcn" {
  cidr_block     = "10.0.0.0/16"
  compartment_id = var.compartment_ocid
  display_name   = "sovereign_vcn"
  dns_label      = "sovereign"
}

resource "oci_core_internet_gateway" "sovereign_igw" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.sovereign_vcn.id
  display_name   = "sovereign_igw"
  enabled        = true
}

resource "oci_core_route_table" "sovereign_rt" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.sovereign_vcn.id
  display_name   = "sovereign_route_table"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.sovereign_igw.id
  }
}

# --- Security List (Firewall) ---

resource "oci_core_security_list" "sovereign_sl" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.sovereign_vcn.id
  display_name   = "sovereign_security_list"

  egress_security_rules {
    destination      = "0.0.0.0/0"
    protocol         = "all"
    description      = "Allow all outbound traffic"
  }

  # SSH Default (temporary until hardened)
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "SSH Default"
    tcp_options {
      max = 22
      min = 22
    }
  }

  # SSH Hardened
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "SSH Custom"
    tcp_options {
      max = 2222
      min = 2222
    }
  }

  # VLESS Proxy + HTTP/3 WireGuard Multiplexing
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "VLESS Reality TCP"
    tcp_options {
      max = 443
      min = 443
    }
  }

  ingress_security_rules {
    protocol    = "17" # UDP
    source      = "0.0.0.0/0"
    description = "WireGuard Stealth UDP"
    udp_options {
      max = 443
      min = 443
    }
  }

  # ACME HTTP-01
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "ACME HTTP-01"
    tcp_options {
      max = 80
      min = 80
    }
  }

  # Honeypot Trap
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "Python Honeypot"
    tcp_options {
      max = 8080
      min = 8080
    }
  }
}

resource "oci_core_subnet" "sovereign_subnet" {
  cidr_block                 = "10.0.1.0/24"
  compartment_id             = var.compartment_ocid
  vcn_id                     = oci_core_vcn.sovereign_vcn.id
  display_name               = "sovereign_subnet"
  route_table_id             = oci_core_route_table.sovereign_rt.id
  security_list_ids          = [oci_core_security_list.sovereign_sl.id]
  dns_label                  = "proxy"
  prohibit_public_ip_on_vnic = false
}

# --- Compute Instance (Always Free ARM) ---

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_ocid
}

# Get latest Ubuntu 24.04 ARM image
data "oci_core_images" "ubuntu_arm" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

resource "oci_core_instance" "sovereign_instance" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_ocid
  display_name        = var.instance_name
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = 2
    memory_in_gbs = 12
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu_arm.images[0].id
    boot_volume_size_in_gbs = 200
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.sovereign_subnet.id
    display_name     = "Primaryvnic"
    assign_public_ip = true
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }
}
