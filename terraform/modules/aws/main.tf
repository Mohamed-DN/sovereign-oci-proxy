terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0"
    }
  }
}

resource "aws_vpc" "mesh_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name    = "${var.cluster_name}-aws-vpc"
    Project = "SovereignProxy"
  }
}

resource "aws_internet_gateway" "mesh_igw" {
  vpc_id = aws_vpc.mesh_vpc.id

  tags = {
    Name = "${var.cluster_name}-igw"
  }
}

resource "aws_subnet" "mesh_subnet" {
  vpc_id                  = aws_vpc.mesh_vpc.id
  cidr_block              = var.subnet_cidr
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.cluster_name}-subnet"
  }
}

resource "aws_route_table" "mesh_rt" {
  vpc_id = aws_vpc.mesh_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.mesh_igw.id
  }

  tags = {
    Name = "${var.cluster_name}-rt"
  }
}

resource "aws_route_table_association" "mesh_rta" {
  subnet_id      = aws_subnet.mesh_subnet.id
  route_table_id = aws_route_table.mesh_rt.id
}

resource "aws_security_group" "mesh_sg" {
  name        = "${var.cluster_name}-sg"
  description = "Security group for Sovereign Proxy Mesh nodes"
  vpc_id      = aws_vpc.mesh_vpc.id

  # SSH Hardened Port 2222
  ingress {
    description = "Hardened SSH"
    from_port   = var.ssh_port
    to_port     = var.ssh_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS / DERP Port 443
  ingress {
    description = "Sovereign Proxy DERP / TLS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP Port 80
  ingress {
    description = "ACME HTTP-01"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # STUN UDP Port 3478
  ingress {
    description = "Mesh STUN UDP Discovery"
    from_port   = 3478
    to_port     = 3478
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Honeypot Port 8080
  ingress {
    description = "Active Scanner Honeypot"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.cluster_name}-security-group"
  }
}

data "aws_ami" "ubuntu" {
  count       = var.ami_id == "" ? 1 : 0
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-noble-24.04-arm64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "relay_node" {
  count                  = length(var.nodes)
  ami                    = var.ami_id != "" ? var.ami_id : data.aws_ami.ubuntu[0].id
  instance_type          = var.nodes[count.index].instance_type
  subnet_id              = aws_subnet.mesh_subnet.id
  vpc_security_group_ids = [aws_security_group.mesh_sg.id]
  key_name               = var.key_name != "" ? var.key_name : null
  user_data              = var.nodes[count.index].user_data != "" ? var.nodes[count.index].user_data : null

  tags = {
    Name    = var.nodes[count.index].id
    Cluster = var.cluster_name
  }
}

resource "aws_eip" "node_eip" {
  count    = length(var.nodes)
  instance = aws_instance.relay_node[count.index].id
  domain   = "vpc"

  tags = {
    Name = "${var.nodes[count.index].id}-eip"
  }
}
