package acl

import (
	"errors"
	"fmt"
	"net"
	"sync"
	"time"
)

var (
	ErrNoPolicyLoaded      = errors.New("no active ACL policy loaded: default deny")
	ErrOutboundBlockedDrop = errors.New("connection blocked by outbound policy DROP rule")
	ErrOutboundDefaultDeny = errors.New("no matching outbound ACL rule: default deny")
	ErrInboundBlockedDrop  = errors.New("inbound packet dropped by policy DROP rule")
	ErrInboundDefaultDeny  = errors.New("inbound packet dropped: no matching rule (default deny)")
)

// ConntrackEntry tracks active stateful connections
type ConntrackEntry struct {
	SourceVIP  string
	SourcePort uint16
	DestVIP    string
	DestPort   uint16
	Protocol   Protocol
	CreatedAt  time.Time
	ExpiresAt  time.Time
}

// NetstackFilter enforces compiled ACL rules inside client bridge netstack
type NetstackFilter struct {
	mu           sync.RWMutex
	policy       *CompiledPeerPolicy
	conntrack    map[string]*ConntrackEntry
	conntrackTTL time.Duration
}

// NewNetstackFilter creates an initialized client netstack filter
func NewNetstackFilter() *NetstackFilter {
	return &NetstackFilter{
		conntrack:    make(map[string]*ConntrackEntry),
		conntrackTTL: 120 * time.Second,
	}
}

// SetConntrackTTL configures the stateful connection tracking timeout
func (nf *NetstackFilter) SetConntrackTTL(ttl time.Duration) {
	nf.mu.Lock()
	defer nf.mu.Unlock()
	nf.conntrackTTL = ttl
}

// UpdatePolicy installs a new compiled policy received from control plane
func (nf *NetstackFilter) UpdatePolicy(p *CompiledPeerPolicy) {
	nf.mu.Lock()
	defer nf.mu.Unlock()
	nf.policy = p
}

// GetPolicy returns the currently active compiled policy
func (nf *NetstackFilter) GetPolicy() *CompiledPeerPolicy {
	nf.mu.RLock()
	defer nf.mu.RUnlock()
	return nf.policy
}

// ConntrackCount returns the number of active conntrack entries
func (nf *NetstackFilter) ConntrackCount() int {
	nf.mu.Lock()
	defer nf.mu.Unlock()
	nf.purgeExpiredLocked()
	return len(nf.conntrack)
}

// EvaluateOutbound tests whether a client may initiate an outbound connection
func (nf *NetstackFilter) EvaluateOutbound(destVIP net.IP, proto Protocol, port uint16) error {
	return nf.EvaluateOutbound4Tuple(nil, 0, destVIP, port, proto)
}

// EvaluateOutbound4Tuple tests outbound connection and records 4-tuple conntrack state
func (nf *NetstackFilter) EvaluateOutbound4Tuple(srcVIP net.IP, srcPort uint16, destVIP net.IP, destPort uint16, proto Protocol) error {
	nf.mu.RLock()
	policy := nf.policy
	ttl := nf.conntrackTTL
	nf.mu.RUnlock()

	if policy == nil {
		return ErrNoPolicyLoaded
	}

	effectiveSrcVIP := srcVIP
	if effectiveSrcVIP == nil {
		effectiveSrcVIP = policy.OverlayIPv4
	}

	for _, rule := range policy.OutboundRules {
		if rule.AllowedPeerVIP.Equal(destVIP) {
			if rule.Protocol == ProtocolALL || rule.Protocol == proto {
				for _, pr := range rule.PortRanges {
					if pr.Matches(destPort) {
						if rule.Action == ActionAccept {
							// Record in conntrack for stateful return path
							nf.recordConntrack(effectiveSrcVIP, srcPort, destVIP, destPort, proto, ttl)
							return nil
						}
						return fmt.Errorf("%w: %s:%d/%s", ErrOutboundBlockedDrop, destVIP.String(), destPort, proto)
					}
				}
			}
		}
	}

	return fmt.Errorf("%w: %s:%d/%s", ErrOutboundDefaultDeny, destVIP.String(), destPort, proto)
}

// EvaluateInbound tests whether an inbound packet/stream from a peer is permitted
func (nf *NetstackFilter) EvaluateInbound(srcVIP net.IP, srcPort uint16, destPort uint16, proto Protocol) error {
	nf.mu.Lock()
	// 1. Check Conntrack for established stateful connections
	nf.purgeExpiredLocked()
	if nf.checkConntrackLocked(srcVIP, srcPort, destPort, proto) {
		nf.mu.Unlock()
		return nil
	}
	policy := nf.policy
	nf.mu.Unlock()

	if policy == nil {
		return ErrNoPolicyLoaded
	}

	// 2. Evaluate Inbound Policy Rules
	for _, rule := range policy.InboundRules {
		if rule.AllowedPeerVIP.Equal(srcVIP) {
			if rule.Protocol == ProtocolALL || rule.Protocol == proto {
				for _, pr := range rule.PortRanges {
					if pr.Matches(destPort) {
						if rule.Action == ActionAccept {
							return nil
						}
						return fmt.Errorf("%w: %s -> :%d/%s", ErrInboundBlockedDrop, srcVIP.String(), destPort, proto)
					}
				}
			}
		}
	}

	return fmt.Errorf("%w: %s -> :%d/%s", ErrInboundDefaultDeny, srcVIP.String(), destPort, proto)
}

// recordConntrack creates or updates a conntrack entry for the expected reverse return traffic
func (nf *NetstackFilter) recordConntrack(src net.IP, srcPort uint16, dst net.IP, dstPort uint16, proto Protocol, ttl time.Duration) {
	now := time.Now()
	exp := now.Add(ttl)

	nf.mu.Lock()
	defer nf.mu.Unlock()

	// If source port is specified, create precise 4-tuple key: "dstVIP:dstPort->srcVIP:srcPort/proto"
	// Also create 2-tuple fallback key: "dstVIP:*->srcVIP:dstPort/proto" if srcPort is dynamic/0
	keyExact := fmt.Sprintf("%s:%d->%s:%d/%s", dst.String(), dstPort, src.String(), srcPort, proto)
	nf.conntrack[keyExact] = &ConntrackEntry{
		SourceVIP:  src.String(),
		SourcePort: srcPort,
		DestVIP:    dst.String(),
		DestPort:   dstPort,
		Protocol:   proto,
		CreatedAt:  now,
		ExpiresAt:  exp,
	}

	if srcPort == 0 {
		keyWildcard := fmt.Sprintf("%s:0->%s:%d/%s", dst.String(), src.String(), dstPort, proto)
		nf.conntrack[keyWildcard] = &ConntrackEntry{
			SourceVIP:  src.String(),
			SourcePort: 0,
			DestVIP:    dst.String(),
			DestPort:   dstPort,
			Protocol:   proto,
			CreatedAt:  now,
			ExpiresAt:  exp,
		}
	}
}

func (nf *NetstackFilter) checkConntrackLocked(src net.IP, srcPort uint16, dstPort uint16, proto Protocol) bool {
	if nf.policy == nil || nf.policy.OverlayIPv4 == nil {
		return false
	}

	localVIP := nf.policy.OverlayIPv4.String()
	now := time.Now()

	// 1. Try exact 4-tuple reverse match: "srcIP:srcPort -> localVIP:dstPort / proto"
	keyExact := fmt.Sprintf("%s:%d->%s:%d/%s", src.String(), srcPort, localVIP, dstPort, proto)
	if entry, ok := nf.conntrack[keyExact]; ok && now.Before(entry.ExpiresAt) {
		return true
	}

	// 2. Try match with destination port from outbound (where client had srcPort=0): "srcIP:srcPort -> localVIP:0 / proto"
	keyWildcard := fmt.Sprintf("%s:%d->%s:0/%s", src.String(), srcPort, localVIP, proto)
	if entry, ok := nf.conntrack[keyWildcard]; ok && now.Before(entry.ExpiresAt) {
		return true
	}

	// 3. Try match with recorded dstPort: "srcIP:0 -> localVIP:dstPort / proto"
	keyDstWildcard := fmt.Sprintf("%s:0->%s:%d/%s", src.String(), localVIP, srcPort, proto)
	if entry, ok := nf.conntrack[keyDstWildcard]; ok && now.Before(entry.ExpiresAt) {
		return true
	}

	return false
}

// PurgeExpiredConntrack removes expired conntrack entries
func (nf *NetstackFilter) PurgeExpiredConntrack() {
	nf.mu.Lock()
	defer nf.mu.Unlock()
	nf.purgeExpiredLocked()
}

func (nf *NetstackFilter) purgeExpiredLocked() {
	now := time.Now()
	for k, v := range nf.conntrack {
		if !now.Before(v.ExpiresAt) {
			delete(nf.conntrack, k)
		}
	}
}
