package routes

import (
	"errors"
	"net"
	"testing"
)

func TestAddRouteAndCIDRValidation(t *testing.T) {
	rt := NewRouteTable()

	// 1. Invalid CIDR
	_, err := rt.AddRoute("rt-bad", "net-1", "10.100.0.300/24", nil, nil, true, FailoverActivePassive)
	if err == nil || !errors.Is(err, ErrInvalidCIDR) {
		t.Fatalf("Expected ErrInvalidCIDR for bad CIDR, got: %v", err)
	}

	// 2. Valid CIDR
	route, err := rt.AddRoute("rt-1", "corp-vpc", "10.100.0.0/24", []*RoutingPeerSpec{
		{NodeID: "peer-east", Priority: 1, LatencyRTTms: 15.0},
	}, []string{"group:devs"}, true, FailoverActivePassive)
	if err != nil {
		t.Fatalf("Failed to add valid route: %v", err)
	}
	if route.NetworkCIDR.String() != "10.100.0.0/24" {
		t.Fatalf("Unexpected CIDR string: %s", route.NetworkCIDR.String())
	}
	if !route.RoutingPeers[0].IsHealthy {
		t.Fatalf("Expected peer to be marked initially healthy")
	}

	// 3. Duplicate Route ID
	_, err = rt.AddRoute("rt-1", "corp-vpc-2", "10.200.0.0/24", nil, nil, false, FailoverActivePassive)
	if err == nil || !errors.Is(err, ErrDuplicateRouteID) {
		t.Fatalf("Expected ErrDuplicateRouteID for duplicate route ID, got: %v", err)
	}
}

func TestLongestPrefixMatch(t *testing.T) {
	rt := NewRouteTable()

	// Add routes with varying prefix lengths
	_, _ = rt.AddRoute("rt-default", "internet", "0.0.0.0/0", []*RoutingPeerSpec{
		{NodeID: "gw-default", Priority: 1, IsHealthy: true},
	}, []string{"group:all"}, true, FailoverActivePassive)

	_, _ = rt.AddRoute("rt-corp-16", "corp", "10.100.0.0/16", []*RoutingPeerSpec{
		{NodeID: "gw-corp-16", Priority: 1, IsHealthy: true},
	}, []string{"group:all"}, true, FailoverActivePassive)

	_, _ = rt.AddRoute("rt-db-24", "prod-db", "10.100.5.0/24", []*RoutingPeerSpec{
		{NodeID: "gw-db-24", Priority: 1, IsHealthy: true},
	}, []string{"group:all"}, true, FailoverActivePassive)

	// 1. IP 10.100.5.15 should match /24 route (longest prefix)
	peer, route, err := rt.SelectNextHop(net.ParseIP("10.100.5.15"), []string{"group:all"})
	if err != nil {
		t.Fatalf("SelectNextHop failed: %v", err)
	}
	if route.ID != "rt-db-24" || peer.NodeID != "gw-db-24" {
		t.Fatalf("Expected LPM /24 match rt-db-24, got %s / %s", route.ID, peer.NodeID)
	}

	// 2. IP 10.100.99.1 should match /16 route
	peer, route, err = rt.SelectNextHop(net.ParseIP("10.100.99.1"), []string{"group:all"})
	if err != nil {
		t.Fatalf("SelectNextHop failed: %v", err)
	}
	if route.ID != "rt-corp-16" || peer.NodeID != "gw-corp-16" {
		t.Fatalf("Expected LPM /16 match rt-corp-16, got %s / %s", route.ID, peer.NodeID)
	}

	// 3. IP 198.51.100.5 should match default 0.0.0.0/0 route
	peer, route, err = rt.SelectNextHop(net.ParseIP("198.51.100.5"), []string{"group:all"})
	if err != nil {
		t.Fatalf("SelectNextHop failed: %v", err)
	}
	if route.ID != "rt-default" || peer.NodeID != "gw-default" {
		t.Fatalf("Expected default route match, got %s / %s", route.ID, peer.NodeID)
	}
}

func TestActivePassiveMultiPeerFailover(t *testing.T) {
	rt := NewRouteTable()

	peers := []*RoutingPeerSpec{
		{NodeID: "peer-primary", Priority: 1, LatencyRTTms: 10.0, IsHealthy: true},
		{NodeID: "peer-secondary", Priority: 2, LatencyRTTms: 25.0, IsHealthy: true},
	}

	_, err := rt.AddRoute("rt-ha", "ha-subnet", "10.200.0.0/24", peers, []string{"group:all"}, true, FailoverActivePassive)
	if err != nil {
		t.Fatalf("AddRoute failed: %v", err)
	}

	destIP := net.ParseIP("10.200.0.50")

	// 1. Initial State: Primary peer (priority 1) should be selected
	p, r, err := rt.SelectNextHop(destIP, []string{"group:all"})
	if err != nil {
		t.Fatalf("SelectNextHop failed: %v", err)
	}
	if p.NodeID != "peer-primary" {
		t.Fatalf("Expected primary peer to be selected, got %s", p.NodeID)
	}

	// 2. Health probe fails once (fail count = 1) -> still healthy
	changed := rt.UpdatePeerHealth("rt-ha", "peer-primary", false, 0)
	if changed {
		t.Fatalf("State should not change on 1st probe failure")
	}
	p, _, _ = rt.SelectNextHop(destIP, []string{"group:all"})
	if p.NodeID != "peer-primary" {
		t.Fatalf("Primary should remain active after only 1 failure")
	}

	// 3. Health probe fails second time (fail count = 2) -> still healthy
	changed = rt.UpdatePeerHealth("rt-ha", "peer-primary", false, 0)
	if changed {
		t.Fatalf("State should not change on 2nd probe failure")
	}

	// 4. Health probe fails 3rd time (fail count = 3 >= threshold) -> marked UNHEALTHY
	changed = rt.UpdatePeerHealth("rt-ha", "peer-primary", false, 0)
	if !changed {
		t.Fatalf("Expected stateChanged=true on 3rd probe failure")
	}

	// Now SelectNextHop should FAILOVER to peer-secondary (priority 2)
	p, r, err = rt.SelectNextHop(destIP, []string{"group:all"})
	if err != nil {
		t.Fatalf("SelectNextHop failed after failover: %v", err)
	}
	if p.NodeID != "peer-secondary" {
		t.Fatalf("Expected failover to peer-secondary, got %s", p.NodeID)
	}

	// 5. Fail peer-secondary (3 failed probes)
	rt.UpdatePeerHealth("rt-ha", "peer-secondary", false, 0)
	rt.UpdatePeerHealth("rt-ha", "peer-secondary", false, 0)
	rt.UpdatePeerHealth("rt-ha", "peer-secondary", false, 0)

	// Now no healthy gateway should be available
	_, _, err = rt.SelectNextHop(destIP, []string{"group:all"})
	if !errors.Is(err, ErrNoHealthyGateway) {
		t.Fatalf("Expected ErrNoHealthyGateway when all peers fail, got: %v", err)
	}

	// 6. Recover Primary peer with single successful probe
	changed = rt.UpdatePeerHealth("rt-ha", "peer-primary", true, 12.0)
	if !changed {
		t.Fatalf("Expected stateChanged=true when primary recovers")
	}

	p, r, err = rt.SelectNextHop(destIP, []string{"group:all"})
	if err != nil {
		t.Fatalf("SelectNextHop failed after recovery: %v", err)
	}
	if p.NodeID != "peer-primary" {
		t.Fatalf("Expected primary peer to regain active status, got %s", p.NodeID)
	}
	if r.ID != "rt-ha" {
		t.Fatalf("Route ID mismatch: %s", r.ID)
	}
}

func TestActiveActiveECMPRouting(t *testing.T) {
	rt := NewRouteTable()

	peers := []*RoutingPeerSpec{
		{NodeID: "ecmp-gw-1", Priority: 1, IsHealthy: true},
		{NodeID: "ecmp-gw-2", Priority: 1, IsHealthy: true},
		{NodeID: "ecmp-gw-3", Priority: 1, IsHealthy: true},
	}

	_, err := rt.AddRoute("rt-ecmp", "ecmp-subnet", "172.16.0.0/16", peers, []string{"group:all"}, true, FailoverActiveActive)
	if err != nil {
		t.Fatalf("AddRoute failed: %v", err)
	}

	// Hash multiple destinations and verify traffic spreads across multiple gateways
	selected := make(map[string]int)
	for i := 1; i <= 30; i++ {
		destIP := net.ParseIP(net.IPv4(172, 16, byte(i), byte(i*3)).String())
		p, _, err := rt.SelectNextHop(destIP, []string{"group:all"})
		if err != nil {
			t.Fatalf("SelectNextHop failed for %s: %v", destIP, err)
		}
		selected[p.NodeID]++
	}

	if len(selected) < 2 {
		t.Fatalf("ECMP should distribute traffic across multiple gateways, got distribution: %v", selected)
	}

	// Excise gw-1 from ECMP pool (3 failed probes)
	rt.UpdatePeerHealth("rt-ecmp", "ecmp-gw-1", false, 0)
	rt.UpdatePeerHealth("rt-ecmp", "ecmp-gw-1", false, 0)
	rt.UpdatePeerHealth("rt-ecmp", "ecmp-gw-1", false, 0)

	// Ensure no traffic routes to ecmp-gw-1
	for i := 1; i <= 30; i++ {
		destIP := net.ParseIP(net.IPv4(172, 16, byte(i), byte(i*3)).String())
		p, _, err := rt.SelectNextHop(destIP, []string{"group:all"})
		if err != nil {
			t.Fatalf("SelectNextHop failed: %v", err)
		}
		if p.NodeID == "ecmp-gw-1" {
			t.Fatalf("Traffic incorrectly routed to failed ECMP peer ecmp-gw-1")
		}
	}
}

func TestGroupAccessControlForRoutes(t *testing.T) {
	rt := NewRouteTable()

	_, _ = rt.AddRoute("rt-secure-vpc", "secure", "10.50.0.0/16", []*RoutingPeerSpec{
		{NodeID: "gw-secure", Priority: 1, IsHealthy: true},
	}, []string{"group:admin", "group:devs"}, true, FailoverActivePassive)

	destIP := net.ParseIP("10.50.1.10")

	// 1. Client with only group:contractors -> Route Not Found (unauthorized)
	_, _, err := rt.SelectNextHop(destIP, []string{"group:contractors"})
	if !errors.Is(err, ErrRouteNotFound) {
		t.Fatalf("Expected ErrRouteNotFound for unauthorized client, got: %v", err)
	}

	// 2. Client with group:devs -> Authorized
	p, r, err := rt.SelectNextHop(destIP, []string{"group:devs"})
	if err != nil {
		t.Fatalf("Expected authorized access for group:devs, got: %v", err)
	}
	if p.NodeID != "gw-secure" || r.ID != "rt-secure-vpc" {
		t.Fatalf("Mismatch in authorized next-hop: %s / %s", p.NodeID, r.ID)
	}
}
