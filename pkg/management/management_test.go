package management

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/sovereign/proxy/v4/pkg/acl"
	"github.com/sovereign/proxy/v4/pkg/posture"
	"github.com/sovereign/proxy/v4/pkg/routes"
)

type MockNodeRegistry struct {
	nodes  map[string]NodeRecordView
	relays []RelayRecordView
	epoch  uint64
}

func NewMockNodeRegistry() *MockNodeRegistry {
	return &MockNodeRegistry{
		nodes:  make(map[string]NodeRecordView),
		relays: make([]RelayRecordView, 0),
		epoch:  1,
	}
}

func (m *MockNodeRegistry) ListNodes() []NodeRecordView {
	list := make([]NodeRecordView, 0, len(m.nodes))
	for _, n := range m.nodes {
		list = append(list, n)
	}
	return list
}

func (m *MockNodeRegistry) GetNode(nodeID string) (*NodeRecordView, error) {
	n, ok := m.nodes[nodeID]
	if !ok {
		return nil, errors.New("node not found")
	}
	return &n, nil
}

func (m *MockNodeRegistry) DeleteNode(nodeID string) error {
	if _, ok := m.nodes[nodeID]; !ok {
		return errors.New("node not found")
	}
	delete(m.nodes, nodeID)
	m.epoch++
	return nil
}

func (m *MockNodeRegistry) RelaysList() []RelayRecordView {
	return m.relays
}

func (m *MockNodeRegistry) Epoch() uint64 {
	return m.epoch
}

func setupTestManagementServer() (*ManagementServer, *MockNodeRegistry, *http.ServeMux) {
	reg := NewMockNodeRegistry()
	aclEng := acl.NewPolicyEngine()
	rt := routes.NewRouteTable()
	postEng := posture.NewPostureEngine()
	eb := NewEventBus(100)

	server := NewManagementServer(reg, aclEng, rt, postEng, eb)
	mux := http.NewServeMux()
	server.RegisterRoutes(mux)

	return server, reg, mux
}

func TestPeersEndpoints(t *testing.T) {
	_, reg, mux := setupTestManagementServer()

	// 1. Seed registry with node
	nodeID := "pk_test_node_1"
	reg.nodes[nodeID] = NodeRecordView{
		NodeID:        nodeID,
		Role:          "EXIT_BRIDGE",
		OverlayIPv4:   "100.64.0.10",
		OverlayIPv6:   "fd7a:115c:a1e0::10",
		CountryCode:   "US",
		IsHealthy:     true,
		LastHeartbeat: time.Now().UTC(),
	}

	// 2. GET /api/v4/peers
	req := httptest.NewRequest(http.MethodGet, "/api/v4/peers", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("GET /api/v4/peers returned status %d", rec.Code)
	}

	var peerListResp struct {
		Peers []PeerView `json:"peers"`
		Total int        `json:"total"`
	}
	if err := json.NewDecoder(rec.Body).Decode(&peerListResp); err != nil {
		t.Fatalf("Failed to decode peers response: %v", err)
	}
	if peerListResp.Total != 1 || peerListResp.Peers[0].NodeID != nodeID {
		t.Fatalf("Unexpected peers response: %+v", peerListResp)
	}

	// 3. GET /api/v4/peers/{id}
	req = httptest.NewRequest(http.MethodGet, "/api/v4/peers/"+nodeID, nil)
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("GET /api/v4/peers/{id} returned status %d", rec.Code)
	}

	var peer PeerView
	if err := json.NewDecoder(rec.Body).Decode(&peer); err != nil {
		t.Fatalf("Failed to decode single peer response: %v", err)
	}
	if peer.NodeID != nodeID || peer.OverlayIPv4 != "100.64.0.10" {
		t.Fatalf("Peer detail mismatch: %+v", peer)
	}

	// 4. DELETE /api/v4/peers/{id}
	req = httptest.NewRequest(http.MethodDelete, "/api/v4/peers/"+nodeID, nil)
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("DELETE /api/v4/peers/{id} returned status %d", rec.Code)
	}

	// Verify node is deleted
	_, err := reg.GetNode(nodeID)
	if err == nil {
		t.Fatalf("Expected node to be deleted from registry")
	}
}

func TestTopologyGraphAndMatrix(t *testing.T) {
	_, reg, mux := setupTestManagementServer()

	nodeID := "pk_test_node_2"
	reg.nodes[nodeID] = NodeRecordView{
		NodeID:        nodeID,
		Role:          "HYBRID",
		OverlayIPv4:   "100.64.0.5",
		IsHealthy:     true,
		LastHeartbeat: time.Now().UTC(),
		RTTms:         18.5,
	}
	reg.relays = append(reg.relays, RelayRecordView{
		RelayID:  "relay-1",
		Region:   "us-east",
		Hostname: "relay-1.sovereign.net",
	})

	// 1. GET /api/v4/topology/graph
	req := httptest.NewRequest(http.MethodGet, "/api/v4/topology/graph", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("GET /api/v4/topology/graph returned status %d", rec.Code)
	}

	var graphResp struct {
		Nodes []struct {
			ID string `json:"id"`
		} `json:"nodes"`
		Edges []struct {
			Source string `json:"source"`
			Target string `json:"target"`
		} `json:"edges"`
	}
	if err := json.NewDecoder(rec.Body).Decode(&graphResp); err != nil {
		t.Fatalf("Failed to decode graph response: %v", err)
	}
	if len(graphResp.Nodes) != 1 || len(graphResp.Edges) != 1 {
		t.Fatalf("Unexpected graph response: %+v", graphResp)
	}

	// 2. GET /api/v4/topology/matrix
	req = httptest.NewRequest(http.MethodGet, "/api/v4/topology/matrix", nil)
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("GET /api/v4/topology/matrix returned status %d", rec.Code)
	}
}

func TestACLAndGroupEndpoints(t *testing.T) {
	_, _, mux := setupTestManagementServer()

	// 1. POST /api/v4/groups
	groupPayload := `{"id":"group:devs","name":"Developers Team","description":"Dev engineers"}`
	req := httptest.NewRequest(http.MethodPost, "/api/v4/groups", strings.NewReader(groupPayload))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("POST /api/v4/groups failed: %d - %s", rec.Code, rec.Body.String())
	}

	// 2. GET /api/v4/groups
	req = httptest.NewRequest(http.MethodGet, "/api/v4/groups", nil)
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("GET /api/v4/groups failed: %d", rec.Code)
	}

	// 3. POST /api/v4/acls
	policyPayload := `{
		"id": "policy-dev-ssh",
		"name": "Dev SSH Access",
		"enabled": true,
		"source_groups": ["group:devs"],
		"destination_groups": ["group:exit-nodes"],
		"rules": [
			{"protocol": "TCP", "port_ranges": [{"start": 22, "end": 22}], "action": "ACCEPT"}
		],
		"bidirectional": false
	}`
	req = httptest.NewRequest(http.MethodPost, "/api/v4/acls", strings.NewReader(policyPayload))
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("POST /api/v4/acls failed: %d - %s", rec.Code, rec.Body.String())
	}

	// 4. GET /api/v4/acls/policy-dev-ssh
	req = httptest.NewRequest(http.MethodGet, "/api/v4/acls/policy-dev-ssh", nil)
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("GET /api/v4/acls/{id} failed: %d", rec.Code)
	}

	// 5. DELETE /api/v4/acls/policy-dev-ssh
	req = httptest.NewRequest(http.MethodDelete, "/api/v4/acls/policy-dev-ssh", nil)
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("DELETE /api/v4/acls/{id} failed: %d", rec.Code)
	}
}

func TestRouteAndPostureEndpoints(t *testing.T) {
	_, _, mux := setupTestManagementServer()

	// 1. POST /api/v4/routes
	routePayload := `{
		"id": "rt-aws-vpc",
		"network_id": "aws-vpc",
		"description": "AWS Production Subnet",
		"network_cidr": "10.100.0.0/16",
		"masquerade": true,
		"failover_mode": "ACTIVE_PASSIVE",
		"routing_peers": [{"node_id": "gw-aws-1", "priority": 1, "is_healthy": true}],
		"groups": ["group:all"]
	}`
	req := httptest.NewRequest(http.MethodPost, "/api/v4/routes", strings.NewReader(routePayload))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("POST /api/v4/routes failed: %d - %s", rec.Code, rec.Body.String())
	}

	// 2. GET /api/v4/routes
	req = httptest.NewRequest(http.MethodGet, "/api/v4/routes", nil)
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("GET /api/v4/routes failed: %d", rec.Code)
	}

	// 3. POST /api/v4/posture-checks
	posturePayload := `{
		"id": "posture-base",
		"name": "Base Posture",
		"enabled": true,
		"min_client_version": "v4.0.0",
		"geo_rule": {
			"allowed_countries": ["US", "DE"]
		},
		"security_rule": {
			"require_disk_encryption": true
		}
	}`
	req = httptest.NewRequest(http.MethodPost, "/api/v4/posture-checks", strings.NewReader(posturePayload))
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("POST /api/v4/posture-checks failed: %d - %s", rec.Code, rec.Body.String())
	}

	// 4. GET /api/v4/posture-checks
	req = httptest.NewRequest(http.MethodGet, "/api/v4/posture-checks", nil)
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("GET /api/v4/posture-checks failed: %d", rec.Code)
	}
}

func TestPrometheusMetricsAndEvents(t *testing.T) {
	server, _, mux := setupTestManagementServer()

	server.eventBus.Publish(EventPeerRegistered, "node-1", "Registered successfully")
	server.eventBus.Publish(EventRouteFailover, "rt-1", "Failover to secondary")

	// 1. GET /api/v4/events
	req := httptest.NewRequest(http.MethodGet, "/api/v4/events", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("GET /api/v4/events failed: %d", rec.Code)
	}

	var eventsResp struct {
		Events []AuditEvent `json:"events"`
		Total  int          `json:"total"`
	}
	if err := json.NewDecoder(rec.Body).Decode(&eventsResp); err != nil {
		t.Fatalf("Failed to decode events response: %v", err)
	}
	if eventsResp.Total != 2 {
		t.Fatalf("Expected 2 events, got %d", eventsResp.Total)
	}

	// 2. GET /metrics
	req = httptest.NewRequest(http.MethodGet, "/metrics", nil)
	rec = httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("GET /metrics failed: %d", rec.Code)
	}

	body := rec.Body.String()
	requiredMetrics := []string{
		"sovereign_peers_total",
		"sovereign_peers_healthy",
		"sovereign_peers_quarantined",
		"sovereign_routes_total",
		"sovereign_route_epoch",
		"sovereign_acl_policies_total",
		"sovereign_acl_epoch",
		"sovereign_events_total",
	}

	for _, m := range requiredMetrics {
		if !strings.Contains(body, m) {
			t.Fatalf("Prometheus metrics missing expected metric: %s\nBody: %s", m, body)
		}
	}
}
