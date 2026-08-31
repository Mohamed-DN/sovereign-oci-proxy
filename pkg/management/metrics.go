package management

import (
	"fmt"
	"strings"

	"github.com/sovereign/proxy/v4/pkg/acl"
	"github.com/sovereign/proxy/v4/pkg/posture"
	"github.com/sovereign/proxy/v4/pkg/routes"
)

// GeneratePrometheusMetrics constructs plaintext OpenMetrics format string for Prometheus scrapers
func GeneratePrometheusMetrics(
	reg NodeRegistry,
	aclEng *acl.PolicyEngine,
	rt *routes.RouteTable,
	postEng *posture.PostureEngine,
	eb *EventBus,
) string {
	var totalPeers, healthyPeers, quarantinedPeers int
	var routeEpoch, aclEpoch, eventCount uint64
	var totalRoutes, totalACLPolicies int

	if reg != nil {
		nodes := reg.ListNodes()
		totalPeers = len(nodes)
		for _, n := range nodes {
			if n.IsHealthy {
				healthyPeers++
			}
		}
	}

	if postEng != nil {
		quarantinedPeers = postEng.QuarantineManager().QuarantineCount()
	}

	if rt != nil {
		routesList := rt.ListRoutes()
		totalRoutes = len(routesList)
		routeEpoch = rt.Epoch()
	}

	if aclEng != nil {
		policies := aclEng.ListPolicies()
		totalACLPolicies = len(policies)
		aclEpoch = aclEng.Epoch()
	}

	if eb != nil {
		eventCount = eb.EventCount()
	}

	var sb strings.Builder
	sb.WriteString("# HELP sovereign_peers_total Total registered mesh peers\n")
	sb.WriteString("# TYPE sovereign_peers_total gauge\n")
	sb.WriteString(fmt.Sprintf("sovereign_peers_total %d\n", totalPeers))

	sb.WriteString("# HELP sovereign_peers_healthy Currently healthy mesh peers\n")
	sb.WriteString("# TYPE sovereign_peers_healthy gauge\n")
	sb.WriteString(fmt.Sprintf("sovereign_peers_healthy %d\n", healthyPeers))

	sb.WriteString("# HELP sovereign_peers_quarantined Quarantined non-compliant peers\n")
	sb.WriteString("# TYPE sovereign_peers_quarantined gauge\n")
	sb.WriteString(fmt.Sprintf("sovereign_peers_quarantined %d\n", quarantinedPeers))

	sb.WriteString("# HELP sovereign_routes_total Total advertised network routes\n")
	sb.WriteString("# TYPE sovereign_routes_total gauge\n")
	sb.WriteString(fmt.Sprintf("sovereign_routes_total %d\n", totalRoutes))

	sb.WriteString("# HELP sovereign_route_epoch Current subnet routing table epoch\n")
	sb.WriteString("# TYPE sovereign_route_epoch counter\n")
	sb.WriteString(fmt.Sprintf("sovereign_route_epoch %d\n", routeEpoch))

	sb.WriteString("# HELP sovereign_acl_policies_total Total configured ACL policy rules\n")
	sb.WriteString("# TYPE sovereign_acl_policies_total gauge\n")
	sb.WriteString(fmt.Sprintf("sovereign_acl_policies_total %d\n", totalACLPolicies))

	sb.WriteString("# HELP sovereign_acl_epoch Current ACL policy engine epoch\n")
	sb.WriteString("# TYPE sovereign_acl_epoch counter\n")
	sb.WriteString(fmt.Sprintf("sovereign_acl_epoch %d\n", aclEpoch))

	sb.WriteString("# HELP sovereign_events_total Total recorded audit events\n")
	sb.WriteString("# TYPE sovereign_events_total counter\n")
	sb.WriteString(fmt.Sprintf("sovereign_events_total %d\n", eventCount))

	return sb.String()
}
