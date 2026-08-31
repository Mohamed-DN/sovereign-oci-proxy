# Amazon Web Services (AWS) Auto-Scaling Module
# Defines Launch Template, Auto Scaling Group (ASG), Target Tracking & Step Policies,
# CloudWatch Alarms, and EC2 Terminating Lifecycle Drain Hook

# 1. EC2 Launch Template for Autoscaled Relay Nodes
resource "aws_launch_template" "relay_launch_template" {
  count         = var.enable_autoscaling ? 1 : 0
  name_prefix   = "${var.cluster_name}-relay-lt-"
  image_id      = var.ami_id != "" ? var.ami_id : data.aws_ami.ubuntu[0].id
  instance_type = var.autoscaling_instance_type
  key_name      = var.key_name != "" ? var.key_name : null

  vpc_security_group_ids = [aws_security_group.mesh_sg.id]

  user_data = var.autoscaling_user_data != "" ? base64encode(var.autoscaling_user_data) : null

  monitoring {
    enabled = true # Detailed CloudWatch monitoring for line-rate metrics
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name    = "${var.cluster_name}-autoscaling-relay"
      Cluster = var.cluster_name
      Role    = "relay-node"
    }
  }

  tag_specifications {
    resource_type = "volume"
    tags = {
      Name    = "${var.cluster_name}-autoscaling-relay-disk"
      Cluster = var.cluster_name
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# 2. AWS Auto Scaling Group (ASG)
resource "aws_autoscaling_group" "relay_asg" {
  count               = var.enable_autoscaling ? 1 : 0
  name_prefix         = "${var.cluster_name}-asg-"
  vpc_zone_identifier = length(var.subnet_ids) > 0 ? var.subnet_ids : [aws_subnet.mesh_subnet.id]

  min_size         = var.asg_min_size
  max_size         = var.asg_max_size
  desired_capacity = var.asg_desired_capacity

  health_check_type         = "EC2"
  health_check_grace_period = 120
  default_cooldown          = var.asg_cooldown_seconds
  termination_policies      = ["OldestInstance", "Default"]

  launch_template {
    id      = aws_launch_template.relay_launch_template[0].id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${var.cluster_name}-relay-asg-node"
    propagate_at_launch = true
  }

  tag {
    key                 = "Role"
    value               = "relay"
    propagate_at_launch = true
  }

  tag {
    key                 = "Cluster"
    value               = var.cluster_name
    propagate_at_launch = true
  }

  lifecycle {
    ignore_changes        = [desired_capacity]
    create_before_destroy = true
  }
}

# 3. Target Tracking Scaling Policy: Target Average CPU Utilization (e.g., 60%)
resource "aws_autoscaling_policy" "cpu_target_tracking" {
  count                  = var.enable_autoscaling ? 1 : 0
  name                   = "${var.cluster_name}-cpu-target-tracking"
  autoscaling_group_name = aws_autoscaling_group.relay_asg[0].name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value     = var.asg_target_cpu_utilization
    disable_scale_in = false
  }
}

# 4. Step Scaling Policy for Sudden Traffic Spikes (Network / Connection Burst)
resource "aws_autoscaling_policy" "scale_out_traffic" {
  count                  = var.enable_autoscaling ? 1 : 0
  name                   = "${var.cluster_name}-scale-out-high-traffic"
  scaling_adjustment     = var.asg_scale_out_step
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 120
  autoscaling_group_name = aws_autoscaling_group.relay_asg[0].name
}

# 5. Step Scaling Policy for Low Traffic Scale-In
resource "aws_autoscaling_policy" "scale_in_traffic" {
  count                  = var.enable_autoscaling ? 1 : 0
  name                   = "${var.cluster_name}-scale-in-low-traffic"
  scaling_adjustment     = var.asg_scale_in_step
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.relay_asg[0].name
}

# 6. CloudWatch Metric Alarm for High Inbound Network Traffic (Line-Rate Scale-Out)
resource "aws_cloudwatch_metric_alarm" "high_network_traffic" {
  count               = var.enable_autoscaling ? 1 : 0
  alarm_name          = "${var.cluster_name}-high-network-traffic"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "NetworkIn"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Average"
  threshold           = var.asg_network_in_threshold_bytes
  alarm_description   = "Trigger scale-out when average inbound traffic exceeds threshold"

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.relay_asg[0].name
  }

  alarm_actions = [aws_autoscaling_policy.scale_out_traffic[0].arn]
}

# 7. CloudWatch Metric Alarm for Low Inbound Network Traffic (Scale-In)
resource "aws_cloudwatch_metric_alarm" "low_network_traffic" {
  count               = var.enable_autoscaling ? 1 : 0
  alarm_name          = "${var.cluster_name}-low-network-traffic"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 5
  metric_name         = "NetworkIn"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Average"
  threshold           = var.asg_network_in_low_threshold_bytes
  alarm_description   = "Trigger scale-in when average inbound traffic remains below threshold"

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.relay_asg[0].name
  }

  alarm_actions = [aws_autoscaling_policy.scale_in_traffic[0].arn]
}

# 8. EC2 Terminating Lifecycle Hook for Connection Draining (120-second drain window)
resource "aws_autoscaling_lifecycle_hook" "drain_terminating_instances" {
  count                  = var.enable_autoscaling ? 1 : 0
  name                   = "${var.cluster_name}-terminating-drain-hook"
  autoscaling_group_name = aws_autoscaling_group.relay_asg[0].name
  default_result         = "CONTINUE"
  heartbeat_timeout      = 120
  lifecycle_transition   = "autoscaling:EC2_INSTANCE_TERMINATING"
}
