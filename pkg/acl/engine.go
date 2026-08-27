package acl

import (
	"errors"
	"fmt"
	"net"
	"sort"
	"sync"
	"time"
)

var (
	ErrGroupNotFound     = errors.New("peer group not found")
	ErrPolicyNotFound    = errors.New("policy rule not found")
	ErrSystemGroupLocked = errors.New("system group cannot be deleted")
	ErrNodeNotFound      = errors.New("target node not found")
)

// PolicyEngine maintains policy definitions and compiles peer filter tables
type PolicyEngine struct {
	mu       sync.RWMutex
	groups   map[string]*PeerGroup
	policies map[string]*PolicyRule
	epoch    uint64
}

// NewPolicyEngine initializes the ACL policy engine with default groups
func NewPolicyEngine() *PolicyEngine {
	pe := &PolicyEngine{
		groups:   make(map[string]*PeerGroup),
		policies: make(map[string]*PolicyRule),
		epoch:    1,
	}

	now := time.Now()
	systemGroups := []struct {
		id   string
		name string
		desc string
	}{
		{"group:all", "All Mesh Peers", "Default group containing all registered mesh nodes"},
		{"group:exit-nodes", "Exit Node Bridges", "All active exit bridges providing internet egress"},
		{"group:admin", "Administrators", "Administrative operators and monitoring controllers"},
		{"group:residential", "Residential Exit Bridges", "High-trust residential IP exit bridges"},
		{"group:mobile", "Mobile 5G Exit Bridges", "Mobile carrier cellular exit bridges"},
		{"group:datacenter", "Datacenter Exit Bridges", "High-throughput cloud and datacenter bridges"},
	}

	for _, sg := range systemGroups {
		pe.groups[sg.id] = &PeerGroup{
			ID:          sg.id,
			Name:        sg.name,
			Description: sg.desc,
			IsSystem:    true,
			Peers:       []string{},
			CreatedAt:   now,
			UpdatedAt:   now,
		}
	}

	return pe
}

// UpsertGroup adds or updates a peer group
func (pe *PolicyEngine) UpsertGroup(g *PeerGroup) error {
	pe.mu.Lock()
	defer pe.mu.Unlock()

	if g.ID == "" {
		return fmt.Errorf("group ID cannot be empty")
	}

	now := time.Now()
	if existing, ok := pe.groups[g.ID]; ok {
		// Preserve system flag and creation timestamp
		g.IsSystem = existing.IsSystem
		g.CreatedAt = existing.CreatedAt
		g.UpdatedAt = now
	} else {
		if g.CreatedAt.IsZero() {
			g.CreatedAt = now
		}
		g.UpdatedAt = now
	}

	if g.Peers == nil {
		g.Peers = []string{}
	}

	pe.groups[g.ID] = g
	pe.epoch++
	return nil
}

// GetGroup retrieves a peer group by ID
func (pe *PolicyEngine) GetGroup(id string) (*PeerGroup, bool) {
	pe.mu.RLock()
	defer pe.mu.RUnlock()

	grp, ok := pe.groups[id]
	if !ok {
		return nil, false
	}
	// Return a copy
	gCopy := *grp
	gCopy.Peers = append([]string(nil), grp.Peers...)
	return &gCopy, true
}

// ListGroups returns all peer groups sorted by ID
func (pe *PolicyEngine) ListGroups() []*PeerGroup {
	pe.mu.RLock()
	defer pe.mu.RUnlock()

	list := make([]*PeerGroup, 0, len(pe.groups))
	for _, g := range pe.groups {
		gCopy := *g
		gCopy.Peers = append([]string(nil), g.Peers...)
		list = append(list, &gCopy)
	}

	sort.Slice(list, func(i, j int) bool {
		return list[i].ID < list[j].ID
	})
	return list
}

// DeleteGroup removes a non-system peer group
func (pe *PolicyEngine) DeleteGroup(groupID string) error {
	pe.mu.Lock()
	defer pe.mu.Unlock()

	grp, ok := pe.groups[groupID]
	if !ok {
		return ErrGroupNotFound
	}
	if grp.IsSystem {
		return ErrSystemGroupLocked
	}

	delete(pe.groups, groupID)
	pe.epoch++
	return nil
}

// AssignPeerToGroup binds a peer to a group
func (pe *PolicyEngine) AssignPeerToGroup(groupID, nodeID string) error {
	pe.mu.Lock()
	defer pe.mu.Unlock()

	grp, ok := pe.groups[groupID]
	if !ok {
		return fmt.Errorf("%w: %s", ErrGroupNotFound, groupID)
	}

	for _, existing := range grp.Peers {
		if existing == nodeID {
			return nil // Already assigned
		}
	}

	grp.Peers = append(grp.Peers, nodeID)
	grp.UpdatedAt = time.Now()
	pe.epoch++
	return nil
}

// RemovePeerFromGroup removes a peer from a group
func (pe *PolicyEngine) RemovePeerFromGroup(groupID, nodeID string) error {
	pe.mu.Lock()
	defer pe.mu.Unlock()

	grp, ok := pe.groups[groupID]
	if !ok {
		return fmt.Errorf("%w: %s", ErrGroupNotFound, groupID)
	}

	newPeers := make([]string, 0, len(grp.Peers))
	found := false
	for _, p := range grp.Peers {
		if p == nodeID {
			found = true
			continue
		}
		newPeers = append(newPeers, p)
	}

	if found {
		grp.Peers = newPeers
		grp.UpdatedAt = time.Now()
		pe.epoch++
	}
	return nil
}

// GetPeerGroups returns all groups a given node belongs to
func (pe *PolicyEngine) GetPeerGroups(nodeID string) []string {
	pe.mu.RLock()
	defer pe.mu.RUnlock()

	var matched []string
	for id, grp := range pe.groups {
		if id == "group:all" {
			matched = append(matched, id)
			continue
		}
		for _, p := range grp.Peers {
			if p == nodeID {
				matched = append(matched, id)
				break
			}
		}
	}
	sort.Strings(matched)
	return matched
}

// UpsertPolicy adds or updates a policy rule
func (pe *PolicyEngine) UpsertPolicy(p *PolicyRule) error {
	pe.mu.Lock()
	defer pe.mu.Unlock()

	if p.ID == "" {
		return fmt.Errorf("policy ID cannot be empty")
	}
	if len(p.SourceGroups) == 0 || len(p.DestGroups) == 0 {
		return fmt.Errorf("policy must specify at least one source and one destination group")
	}
	if len(p.Rules) == 0 {
		return fmt.Errorf("policy must specify at least one rule item")
	}

	now := time.Now()
	if existing, ok := pe.policies[p.ID]; ok {
		p.CreatedAt = existing.CreatedAt
	} else if p.CreatedAt.IsZero() {
		p.CreatedAt = now
	}
	p.UpdatedAt = now

	pe.policies[p.ID] = p
	pe.epoch++
	return nil
}

// GetPolicy retrieves a policy rule by ID
func (pe *PolicyEngine) GetPolicy(id string) (*PolicyRule, bool) {
	pe.mu.RLock()
	defer pe.mu.RUnlock()

	p, ok := pe.policies[id]
	if !ok {
		return nil, false
	}
	pCopy := *p
	return &pCopy, true
}

// ListPolicies returns all policy rules sorted by ID
func (pe *PolicyEngine) ListPolicies() []*PolicyRule {
	pe.mu.RLock()
	defer pe.mu.RUnlock()

	list := make([]*PolicyRule, 0, len(pe.policies))
	for _, p := range pe.policies {
		pCopy := *p
		list = append(list, &pCopy)
	}

	sort.Slice(list, func(i, j int) bool {
		return list[i].ID < list[j].ID
	})
	return list
}

// DeletePolicy removes a policy
func (pe *PolicyEngine) DeletePolicy(policyID string) error {
	pe.mu.Lock()
	defer pe.mu.Unlock()

	if _, ok := pe.policies[policyID]; !ok {
		return ErrPolicyNotFound
	}
	delete(pe.policies, policyID)
	pe.epoch++
	return nil
}

// Epoch returns the current policy engine epoch
func (pe *PolicyEngine) Epoch() uint64 {
	pe.mu.RLock()
	defer pe.mu.RUnlock()
	return pe.epoch
}

// NodeLookupFunc abstracts looking up a node's VIP and assigned groups
type NodeLookupFunc func(nodeID string) (vip net.IP, groups []string, ok bool)

// CompilePolicyForPeer generates the complete compiled inbound and outbound filter rules for a peer
func (pe *PolicyEngine) CompilePolicyForPeer(targetNodeID string, lookup NodeLookupFunc) (*CompiledPeerPolicy, error) {
	pe.mu.RLock()
	defer pe.mu.RUnlock()

	targetVIP, targetGroups, ok := lookup(targetNodeID)
	if !ok {
		return nil, fmt.Errorf("%w: %s", ErrNodeNotFound, targetNodeID)
	}

	// Ensure target has group:all
	hasAll := false
	for _, g := range targetGroups {
		if g == "group:all" {
			hasAll = true
			break
		}
	}
	if !hasAll {
		targetGroups = append(targetGroups, "group:all")
	}

	targetGroupSet := make(map[string]bool)
	for _, g := range targetGroups {
		targetGroupSet[g] = true
	}

	compiled := &CompiledPeerPolicy{
		NodeID:        targetNodeID,
		OverlayIPv4:   targetVIP,
		InboundRules:  make([]CompiledFilterRule, 0),
		OutboundRules: make([]CompiledFilterRule, 0),
		Epoch:         pe.epoch,
	}

	// Sort policies by ID for deterministic compilation order
	sortedPolicies := make([]*PolicyRule, 0, len(pe.policies))
	for _, p := range pe.policies {
		sortedPolicies = append(sortedPolicies, p)
	}
	sort.Slice(sortedPolicies, func(i, j int) bool {
		return sortedPolicies[i].ID < sortedPolicies[j].ID
	})

	for _, policy := range sortedPolicies {
		if !policy.Enabled {
			continue
		}

		isSource := false
		isDest := false

		for _, sg := range policy.SourceGroups {
			if targetGroupSet[sg] {
				isSource = true
				break
			}
		}

		for _, dg := range policy.DestGroups {
			if targetGroupSet[dg] {
				isDest = true
				break
			}
		}

		// Case 1: Target is in Source Group -> Can initiate outbound traffic to Destination peers
		if isSource {
			for _, dg := range policy.DestGroups {
				destGrp := pe.groups[dg]
				if destGrp == nil {
					continue
				}
				for _, destNodeID := range destGrp.Peers {
					if destNodeID == targetNodeID {
						continue
					}
					destVIP, _, destOK := lookup(destNodeID)
					if !destOK || destVIP == nil {
						continue
					}

					for _, r := range policy.Rules {
						compiled.OutboundRules = append(compiled.OutboundRules, CompiledFilterRule{
							AllowedPeerVIP: destVIP,
							Protocol:       r.Protocol,
							PortRanges:     r.PortRanges,
							Action:         r.Action,
							IsDirectional:  !policy.Bidirectional,
						})
					}
				}
			}
		}

		// Case 2: Target is in Dest Group -> Can receive inbound traffic from Source peers
		if isDest {
			for _, sg := range policy.SourceGroups {
				srcGrp := pe.groups[sg]
				if srcGrp == nil {
					continue
				}
				for _, srcNodeID := range srcGrp.Peers {
					if srcNodeID == targetNodeID {
						continue
					}
					srcVIP, _, srcOK := lookup(srcNodeID)
					if !srcOK || srcVIP == nil {
						continue
					}

					for _, r := range policy.Rules {
						compiled.InboundRules = append(compiled.InboundRules, CompiledFilterRule{
							AllowedPeerVIP: srcVIP,
							Protocol:       r.Protocol,
							PortRanges:     r.PortRanges,
							Action:         r.Action,
							IsDirectional:  !policy.Bidirectional,
						})
					}
				}
			}
		}

		// Case 3: Bidirectional rule allows reverse initiation
		if policy.Bidirectional {
			if isSource {
				// Also allow inbound from Dest peers
				for _, dg := range policy.DestGroups {
					destGrp := pe.groups[dg]
					if destGrp == nil {
						continue
					}
					for _, destNodeID := range destGrp.Peers {
						if destNodeID == targetNodeID {
							continue
						}
						destVIP, _, destOK := lookup(destNodeID)
						if !destOK || destVIP == nil {
							continue
						}
						for _, r := range policy.Rules {
							compiled.InboundRules = append(compiled.InboundRules, CompiledFilterRule{
								AllowedPeerVIP: destVIP,
								Protocol:       r.Protocol,
								PortRanges:     r.PortRanges,
								Action:         r.Action,
								IsDirectional:  false,
							})
						}
					}
				}
			}
			if isDest {
				// Also allow outbound to Source peers
				for _, sg := range policy.SourceGroups {
					srcGrp := pe.groups[sg]
					if srcGrp == nil {
						continue
					}
					for _, srcNodeID := range srcGrp.Peers {
						if srcNodeID == targetNodeID {
							continue
						}
						srcVIP, _, srcOK := lookup(srcNodeID)
						if !srcOK || srcVIP == nil {
							continue
						}
						for _, r := range policy.Rules {
							compiled.OutboundRules = append(compiled.OutboundRules, CompiledFilterRule{
								AllowedPeerVIP: srcVIP,
								Protocol:       r.Protocol,
								PortRanges:     r.PortRanges,
								Action:         r.Action,
								IsDirectional:  false,
							})
						}
					}
				}
			}
		}
	}

	return compiled, nil
}
