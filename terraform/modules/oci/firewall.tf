resource "oci_core_security_list" "mesh_sec_list" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.mesh_vcn.id
  display_name   = "${var.cluster_name}-security-list"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
    description = "Allow all outbound traffic"
  }

  # Inbound Hardened SSH (Port 2222)
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "Hardened SSH management port"
    tcp_options {
      min = var.ssh_port
      max = var.ssh_port
    }
  }

  # Inbound DERP Relay / HTTPS (Port 443)
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "Sovereign Proxy DERP TLS / Anti-Censorship"
    tcp_options {
      min = 443
      max = 443
    }
  }

  # Inbound HTTP (Port 80) for ACME challenge
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "ACME HTTP-01 challenge"
    tcp_options {
      min = 80
      max = 80
    }
  }

  # Inbound STUN UDP (Port 3478)
  ingress_security_rules {
    protocol    = "17" # UDP
    source      = "0.0.0.0/0"
    description = "Mesh STUN UDP Discovery"
    udp_options {
      min = 3478
      max = 3478
    }
  }

  # Inbound Honeypot Sensor (Port 8080)
  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "Active Port Scanner Honeypot Sensor"
    tcp_options {
      min = 8080
      max = 8080
    }
  }
}
