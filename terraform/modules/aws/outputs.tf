output "vpc_id" {
  value       = aws_vpc.mesh_vpc.id
  description = "AWS VPC ID"
}

output "subnet_id" {
  value       = aws_subnet.mesh_subnet.id
  description = "AWS Subnet ID"
}

output "security_group_id" {
  value       = aws_security_group.mesh_sg.id
  description = "AWS Security Group ID"
}

output "instance_ids" {
  value       = aws_instance.relay_node[*].id
  description = "IDs of deployed EC2 instances"
}

output "public_ips" {
  value       = aws_eip.node_eip[*].public_ip
  description = "Elastic Public IP addresses of deployed AWS nodes"
}

output "autoscaling_group_id" {
  value       = try(aws_autoscaling_group.relay_asg[0].id, null)
  description = "ID of the AWS Auto Scaling Group"
}

output "autoscaling_group_arn" {
  value       = try(aws_autoscaling_group.relay_asg[0].arn, null)
  description = "ARN of the AWS Auto Scaling Group"
}

output "launch_template_id" {
  value       = try(aws_launch_template.relay_launch_template[0].id, null)
  description = "ID of the EC2 Launch Template"
}

