package nat

import (
	"context"
	"fmt"
	"net"
	"time"
)

// TraversalStrategy represents the NAT punch method
type TraversalStrategy string

const (
	StrategyDirect               TraversalStrategy = "DIRECT"
	StrategyDualPing             TraversalStrategy = "DUAL_PING"
	StrategySequentialPrediction TraversalStrategy = "SEQUENTIAL_PREDICTION"
	StrategyBirthdaySpray        TraversalStrategy = "BIRTHDAY_SPRAY"
	StrategyDERPFallback         TraversalStrategy = "DERP_FALLBACK"
)

// EndpointCandidate represents an address candidate for peer connection
type EndpointCandidate struct {
	Type     string       `json:"type"` // "local", "stun", "relay"
	Addr     *net.UDPAddr `json:"addr"`
	Priority int          `json:"priority"`
}

// DiscoCoordinator manages peer discovery, strategy selection, and hole punching
type DiscoCoordinator struct {
	stunServers []string
	localConn   *net.UDPConn
	descriptor  *NATDescriptor
}

// NewDiscoCoordinator creates a new Disco-v4 coordinator
func NewDiscoCoordinator(stunServers []string, localConn *net.UDPConn) *DiscoCoordinator {
	return &DiscoCoordinator{
		stunServers: stunServers,
		localConn:   localConn,
	}
}

// DiscoverLocalEndpoints collects local interface IP candidates
func (c *DiscoCoordinator) DiscoverLocalEndpoints() ([]EndpointCandidate, error) {
	var candidates []EndpointCandidate

	ifaces, err := net.Interfaces()
	if err != nil {
		return nil, err
	}

	port := 0
	if c.localConn != nil {
		if laddr, ok := c.localConn.LocalAddr().(*net.UDPAddr); ok {
			port = laddr.Port
		}
	}

	for _, iface := range ifaces {
		if (iface.Flags&net.FlagUp) == 0 || (iface.Flags&net.FlagLoopback) != 0 {
			continue
		}

		addrs, err := iface.Addrs()
		if err != nil {
			continue
		}

		for _, addr := range addrs {
			var ip net.IP
			switch v := addr.(type) {
			case *net.IPNet:
				ip = v.IP
			case *net.IPAddr:
				ip = v.IP
			}

			if ip != nil && ip.To4() != nil && !ip.IsLoopback() {
				candidates = append(candidates, EndpointCandidate{
					Type:     "local",
					Addr:     &net.UDPAddr{IP: ip, Port: port},
					Priority: 100,
				})
			}
		}
	}

	return candidates, nil
}

// DiscoverPublicEndpoints runs STUN classification to find reflected public IP/port
func (c *DiscoCoordinator) DiscoverPublicEndpoints(timeout time.Duration) (*NATDescriptor, error) {
	desc, err := ClassifyNAT(c.stunServers, c.localConn, timeout)
	if err != nil {
		return desc, err
	}
	c.descriptor = desc
	return desc, nil
}

// SelectStrategy determines the optimal hole punching method between local and remote NAT descriptors
func SelectStrategy(localDesc, remoteDesc *NATDescriptor) TraversalStrategy {
	if localDesc == nil || remoteDesc == nil {
		return StrategyDERPFallback
	}

	if localDesc.Type == NATTypeBlocked || remoteDesc.Type == NATTypeBlocked {
		return StrategyDERPFallback
	}

	if localDesc.Type == NATTypeDirectPublic || remoteDesc.Type == NATTypeDirectPublic {
		return StrategyDirect
	}

	isLocalCone := localDesc.Type == NATTypeFullCone ||
		localDesc.Type == NATTypeRestrictedCone ||
		localDesc.Type == NATTypePortRestrictedCone

	isRemoteCone := remoteDesc.Type == NATTypeFullCone ||
		remoteDesc.Type == NATTypeRestrictedCone ||
		remoteDesc.Type == NATTypePortRestrictedCone

	if isLocalCone && isRemoteCone {
		return StrategyDualPing
	}

	if (localDesc.Type == NATTypeSymmetric && isRemoteCone) ||
		(remoteDesc.Type == NATTypeSymmetric && isLocalCone) {
		if (localDesc.Type == NATTypeSymmetric && localDesc.IsSequential) ||
			(remoteDesc.Type == NATTypeSymmetric && remoteDesc.IsSequential) {
			return StrategySequentialPrediction
		}
		return StrategyBirthdaySpray
	}

	if localDesc.Type == NATTypeSymmetric && remoteDesc.Type == NATTypeSymmetric {
		return StrategyBirthdaySpray
	}

	return StrategyDERPFallback
}

// PunchHole coordinates the traversal execution given a remote peer's endpoint and NAT descriptor
func (c *DiscoCoordinator) PunchHole(
	ctx context.Context,
	remoteDesc *NATDescriptor,
) (*SprayResult, TraversalStrategy, error) {
	if c.localConn == nil {
		return nil, StrategyDERPFallback, fmt.Errorf("local UDP connection not initialized")
	}

	strat := SelectStrategy(c.descriptor, remoteDesc)

	switch strat {
	case StrategyDirect, StrategyDualPing:
		// Send dual ping bursts directly to peer's public address
		res, err := ExecuteSequentialPrediction(ctx, c.localConn, remoteDesc.PublicAddr1.IP, remoteDesc.PublicAddr1.Port, 0, 8)
		if err == nil {
			return res, strat, nil
		}
	case StrategySequentialPrediction:
		delta := remoteDesc.PortDelta
		if delta == 0 {
			delta = 1
		}
		res, err := ExecuteSequentialPrediction(ctx, c.localConn, remoteDesc.PublicAddr1.IP, remoteDesc.PublicAddr1.Port, delta, 32)
		if err == nil {
			return res, strat, nil
		}
	case StrategyBirthdaySpray:
		res, err := ExecuteBirthdaySpray(ctx, c.localConn, remoteDesc.PublicAddr1.IP, remoteDesc.PublicAddr1.Port, 256)
		if err == nil {
			return res, strat, nil
		}
	}

	return nil, StrategyDERPFallback, ErrHolePunchFailed
}
