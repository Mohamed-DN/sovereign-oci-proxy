package config

import (
	"errors"
	"fmt"
	"net"
	"regexp"
	"strings"
)

var (
	validProviders = map[string]bool{
		"oci":          true,
		"aws":          true,
		"gcp":          true,
		"digitalocean": true,
		"hetzner":      true,
		"vultr":        true,
	}

	validNoiseSuites = map[string]bool{
		"Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s": true,
		"Noise_IK_25519_ChaChaPoly_BLAKE2s":     true,
		"Noise_XX_25519_ChaChaPoly_BLAKE2s":     true,
	}

	validExitModes = map[string]bool{
		"country":       true,
		"specific_host": true,
		"onion_3hop":    true,
	}

	domainRegex = regexp.MustCompile(`^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$`)
	nodeIdRegex = regexp.MustCompile(`^[a-z0-9][a-z0-9\-]{2,62}[a-z0-9]$`)
)

// ValidationError represents an aggregation of validation failures.
type ValidationError struct {
	Errors []string
}

func (v *ValidationError) Error() string {
	return fmt.Sprintf("validation failed with %d error(s):\n - %s", len(v.Errors), strings.Join(v.Errors, "\n - "))
}

func (v *ValidationError) Add(format string, args ...interface{}) {
	v.Errors = append(v.Errors, fmt.Sprintf(format, args...))
}

func (v *ValidationError) HasErrors() bool {
	return len(v.Errors) > 0
}

// ValidateMeshConfig performs comprehensive semantic and schema checks on MeshClusterConfig.
func ValidateMeshConfig(cfg *MeshClusterConfig) error {
	if cfg == nil {
		return errors.New("configuration is nil")
	}

	v := &ValidationError{}

	// 1. Root & Metadata Validation
	if cfg.APIVersion != "sovereign.mesh/v4alpha1" {
		v.Add("invalid apiVersion '%s': expected 'sovereign.mesh/v4alpha1'", cfg.APIVersion)
	}
	if cfg.Kind != "SovereignCluster" {
		v.Add("invalid kind '%s': expected 'SovereignCluster'", cfg.Kind)
	}
	if strings.TrimSpace(cfg.Metadata.ClusterName) == "" {
		v.Add("metadata.clusterName must not be empty")
	}
	if strings.TrimSpace(cfg.Metadata.Environment) == "" {
		v.Add("metadata.environment must not be empty")
	}

	// 2. Global Settings Validation
	if cfg.Global.Domain == "" || !domainRegex.MatchString(cfg.Global.Domain) {
		v.Add("global.domain '%s' is not a valid FQDN domain name", cfg.Global.Domain)
	}
	if cfg.Global.OverlayCidr == "" {
		v.Add("global.overlayCidr must not be empty")
	} else if _, _, err := net.ParseCIDR(cfg.Global.OverlayCidr); err != nil {
		v.Add("global.overlayCidr '%s' is not a valid CIDR: %v", cfg.Global.OverlayCidr, err)
	}
	if !validNoiseSuites[cfg.Global.Encryption.NoiseSuite] {
		v.Add("global.encryption.noiseSuite '%s' is invalid or unsupported", cfg.Global.Encryption.NoiseSuite)
	}
	if cfg.Global.Security.SSHPort <= 0 || cfg.Global.Security.SSHPort > 65535 {
		v.Add("global.security.sshPort %d must be between 1 and 65535", cfg.Global.Security.SSHPort)
	}

	// 3. Control Plane Validation
	if cfg.ControlPlane.Replicas < 1 {
		v.Add("controlPlane.replicas must be at least 1, got %d", cfg.ControlPlane.Replicas)
	}
	if cfg.ControlPlane.ListenPort <= 0 || cfg.ControlPlane.ListenPort > 65535 {
		v.Add("controlPlane.listenPort %d is invalid", cfg.ControlPlane.ListenPort)
	}
	if cfg.ControlPlane.GrpcPort <= 0 || cfg.ControlPlane.GrpcPort > 65535 {
		v.Add("controlPlane.grpcPort %d is invalid", cfg.ControlPlane.GrpcPort)
	}
	if len(cfg.ControlPlane.Distribution) == 0 {
		v.Add("controlPlane.distribution must contain at least one node location")
	}
	for idx, cpNode := range cfg.ControlPlane.Distribution {
		if !validProviders[strings.ToLower(cpNode.Provider)] {
			v.Add("controlPlane.distribution[%d].provider '%s' is not a supported cloud provider", idx, cpNode.Provider)
		}
		if cpNode.Region == "" {
			v.Add("controlPlane.distribution[%d].region must not be empty", idx)
		}
		if cpNode.Shape == "" {
			v.Add("controlPlane.distribution[%d].shape must not be empty", idx)
		}
	}

	// 4. Relay Fleet Validation
	if cfg.RelayFleet.DefaultPort <= 0 || cfg.RelayFleet.DefaultPort > 65535 {
		v.Add("relayFleet.defaultPort %d is invalid", cfg.RelayFleet.DefaultPort)
	}
	if cfg.RelayFleet.StunPort <= 0 || cfg.RelayFleet.StunPort > 65535 {
		v.Add("relayFleet.stunPort %d is invalid", cfg.RelayFleet.StunPort)
	}
	if len(cfg.RelayFleet.Nodes) == 0 {
		v.Add("relayFleet.nodes must contain at least one relay node")
	}

	nodeIdMap := make(map[string]bool)
	for idx, node := range cfg.RelayFleet.Nodes {
		if !nodeIdRegex.MatchString(node.ID) {
			v.Add("relayFleet.nodes[%d].id '%s' is invalid (must match [a-z0-9][a-z0-9-]{2,62}[a-z0-9])", idx, node.ID)
		}
		if nodeIdMap[node.ID] {
			v.Add("relayFleet.nodes[%d].id '%s' is duplicated", idx, node.ID)
		}
		nodeIdMap[node.ID] = true

		if !validProviders[strings.ToLower(node.Provider)] {
			v.Add("relayFleet.nodes[%d].provider '%s' is not supported", idx, node.Provider)
		}
		if node.Region == "" {
			v.Add("relayFleet.nodes[%d].region must not be empty", idx)
		}
		if node.Shape == "" {
			v.Add("relayFleet.nodes[%d].shape must not be empty", idx)
		}
		if node.AntiCensorship.DecoyDomain == "" || !domainRegex.MatchString(node.AntiCensorship.DecoyDomain) {
			v.Add("relayFleet.nodes[%d].antiCensorship.decoyDomain '%s' is invalid", idx, node.AntiCensorship.DecoyDomain)
		}
		if node.AntiCensorship.HoneypotPort <= 0 || node.AntiCensorship.HoneypotPort > 65535 {
			v.Add("relayFleet.nodes[%d].antiCensorship.honeypotPort %d is invalid", idx, node.AntiCensorship.HoneypotPort)
		}
	}

	// 5. Egress Gateway Validation
	if !validExitModes[cfg.EgressGateways.DefaultExitMode] {
		v.Add("egressGateways.defaultExitMode '%s' is invalid (must be 'country', 'specific_host', or 'onion_3hop')", cfg.EgressGateways.DefaultExitMode)
	}
	for idx, cidr := range cfg.EgressGateways.BogonFilter.BlockedCidrs {
		if _, _, err := net.ParseCIDR(cidr); err != nil {
			v.Add("egressGateways.bogonFilter.blockedCidrs[%d] '%s' is invalid CIDR: %v", idx, cidr, err)
		}
	}

	// 6. Providers Network CIDRs Validation
	validateCIDROptional := func(fieldName, cidr string) {
		if cidr != "" {
			if _, _, err := net.ParseCIDR(cidr); err != nil {
				v.Add("%s '%s' is invalid CIDR: %v", fieldName, cidr, err)
			}
		}
	}

	validateCIDROptional("providers.oci.vpcCidr", cfg.Providers.OCI.VpcCidr)
	validateCIDROptional("providers.oci.subnetCidr", cfg.Providers.OCI.SubnetCidr)
	validateCIDROptional("providers.aws.vpcCidr", cfg.Providers.AWS.VpcCidr)
	validateCIDROptional("providers.aws.subnetCidr", cfg.Providers.AWS.SubnetCidr)
	validateCIDROptional("providers.gcp.vpcCidr", cfg.Providers.GCP.VpcCidr)
	validateCIDROptional("providers.gcp.subnetCidr", cfg.Providers.GCP.SubnetCidr)
	validateCIDROptional("providers.digitalocean.vpcCidr", cfg.Providers.DigitalOcean.VpcCidr)
	validateCIDROptional("providers.hetzner.networkCidr", cfg.Providers.Hetzner.NetworkCidr)
	validateCIDROptional("providers.hetzner.subnetCidr", cfg.Providers.Hetzner.SubnetCidr)
	validateCIDROptional("providers.vultr.vpcCidr", cfg.Providers.Vultr.VpcCidr)
	validateCIDROptional("providers.vultr.subnetCidr", cfg.Providers.Vultr.SubnetCidr)

	if v.HasErrors() {
		return v
	}
	return nil
}
