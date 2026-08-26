output "instance_public_ip" {
  description = "Public IP address of the Sovereign Proxy instance"
  value       = oci_core_instance.sovereign_instance.public_ip
}

output "instance_state" {
  description = "State of the Sovereign Proxy instance"
  value       = oci_core_instance.sovereign_instance.state
}

output "ssh_command_default" {
  description = "Command to SSH into the instance (before hardening)"
  value       = "ssh ubuntu@${oci_core_instance.sovereign_instance.public_ip}"
}

output "ssh_command_hardened" {
  description = "Command to SSH into the instance (after hardening port 2222)"
  value       = "ssh -p 2222 ubuntu@${oci_core_instance.sovereign_instance.public_ip}"
}
