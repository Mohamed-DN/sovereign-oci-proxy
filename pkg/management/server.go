package management

import (
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/sovereign/proxy/v4/pkg/acl"
	"github.com/sovereign/proxy/v4/pkg/posture"
	"github.com/sovereign/proxy/v4/pkg/routes"
)

// NodeRecordView provides node metadata to the management server
type NodeRecordView struct {
	NodeID         string    `json:"node_id"`
	Role           string    `json:"role"`
	OverlayIPv4    string    `json:"overlay_ipv4"`
	OverlayIPv6    string    `json:"overlay_ipv6"`
	CountryCode    string    `json:"country_code"`
	City           string    `json:"city"`
	ASN            uint32    `json:"asn"`
	IPClass        string    `json:"ip_class"`
	MaxBandwidth   uint32    `json:"max_bandwidth_kbps"`
	IsHealthy      bool      `json:"is_healthy"`
	LastHeartbeat  time.Time `json:"last_heartbeat"`
	ActiveCircuits uint32    `json:"active_circuits"`
	RTTms          float64   `json:"rtt_ms"`
}

// RelayRecordView provides relay node metadata
type RelayRecordView struct {
	RelayID  string `json:"relay_id"`
	Hostname string `json:"hostname"`
	Region   string `json:"region"`
}

// NodeRegistry abstracts peer directory access for the management server
type NodeRegistry interface {
	ListNodes() []NodeRecordView
	GetNode(nodeID string) (*NodeRecordView, error)
	DeleteNode(nodeID string) error
	RelaysList() []RelayRecordView
	Epoch() uint64
}

// ManagementServer coordinates the administrative REST API and telemetry
type ManagementServer struct {
	mu            sync.RWMutex
	registry      NodeRegistry
	aclEngine     *acl.PolicyEngine
	routeTable    *routes.RouteTable
	postureEngine *posture.PostureEngine
	eventBus      *EventBus
}

// NewManagementServer creates an initialized management server instance
func NewManagementServer(
	reg NodeRegistry,
	aclEng *acl.PolicyEngine,
	rt *routes.RouteTable,
	postEng *posture.PostureEngine,
	eb *EventBus,
) *ManagementServer {
	if eb == nil {
		eb = NewEventBus(1000)
	}
	return &ManagementServer{
		registry:      reg,
		aclEngine:     aclEng,
		routeTable:    rt,
		postureEngine: postEng,
		eventBus:      eb,
	}
}

// RegisterRoutes attaches the management API routes to an HTTP ServeMux
func (ms *ManagementServer) RegisterRoutes(mux *http.ServeMux) {
	mux.HandleFunc("/api/v4/peers", ms.handlePeers)
	mux.HandleFunc("/api/v4/peers/", ms.handlePeerByID)
	mux.HandleFunc("/api/v4/topology/graph", ms.handleTopologyGraph)
	mux.HandleFunc("/api/v4/topology/matrix", ms.handleLatencyMatrix)
	mux.HandleFunc("/api/v4/acls", ms.handleACLs)
	mux.HandleFunc("/api/v4/acls/", ms.handleACLByID)
	mux.HandleFunc("/api/v4/groups", ms.handleGroups)
	mux.HandleFunc("/api/v4/groups/", ms.handleGroupByID)
	mux.HandleFunc("/api/v4/routes", ms.handleRoutes)
	mux.HandleFunc("/api/v4/routes/", ms.handleRouteByID)
	mux.HandleFunc("/api/v4/posture-checks", ms.handlePostureChecks)
	mux.HandleFunc("/api/v4/posture-checks/", ms.handlePostureCheckByID)
	mux.HandleFunc("/api/v4/events", ms.handleEvents)
	mux.HandleFunc("/metrics", ms.handlePrometheusMetrics)
}

// --- Handler Implementations ---

type PeerView struct {
	NodeID         string   `json:"node_id"`
	OverlayIPv4    string   `json:"overlay_ipv4"`
	OverlayIPv6    string   `json:"overlay_ipv6"`
	Role           string   `json:"role"`
	Country        string   `json:"country"`
	IsHealthy      bool     `json:"is_healthy"`
	Quarantined    bool     `json:"quarantined"`
	LastHeartbeat  string   `json:"last_heartbeat"`
	ActiveCircuits uint32   `json:"active_circuits"`
	Groups         []string `json:"groups"`
	City           string   `json:"city"`
	ASN            uint32   `json:"asn"`
	IPClass        string   `json:"ip_class"`
}

func (ms *ManagementServer) handlePeers(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodes := ms.registry.ListNodes()
	list := make([]PeerView, 0, len(nodes))

	for _, n := range nodes {
		groups := []string{"group:all"}
		if ms.aclEngine != nil {
			groups = ms.aclEngine.GetPeerGroups(n.NodeID)
		}
		quarantined := false
		if ms.postureEngine != nil {
			quarantined = ms.postureEngine.QuarantineManager().IsQuarantined(n.NodeID)
		}

		list = append(list, PeerView{
			NodeID:         n.NodeID,
			OverlayIPv4:    n.OverlayIPv4,
			OverlayIPv6:    n.OverlayIPv6,
			Role:           n.Role,
			Country:        n.CountryCode,
			City:           n.City,
			ASN:            n.ASN,
			IPClass:        n.IPClass,
			IsHealthy:      n.IsHealthy,
			Quarantined:    quarantined,
			LastHeartbeat:  n.LastHeartbeat.UTC().Format(time.RFC3339),
			ActiveCircuits: n.ActiveCircuits,
			Groups:         groups,
		})
	}

	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"peers": list,
		"total": len(list),
		"epoch": ms.registry.Epoch(),
	})
}

func (ms *ManagementServer) handlePeerByID(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	nodeID := strings.TrimPrefix(r.URL.Path, "/api/v4/peers/")
	if nodeID == "" {
		http.Error(w, `{"error":"node ID required"}`, http.StatusBadRequest)
		return
	}

	switch r.Method {
	case http.MethodGet:
		n, err := ms.registry.GetNode(nodeID)
		if err != nil {
			http.Error(w, `{"error":"peer not found"}`, http.StatusNotFound)
			return
		}
		groups := []string{"group:all"}
		if ms.aclEngine != nil {
			groups = ms.aclEngine.GetPeerGroups(n.NodeID)
		}
		quarantined := false
		if ms.postureEngine != nil {
			quarantined = ms.postureEngine.QuarantineManager().IsQuarantined(n.NodeID)
		}
		_ = json.NewEncoder(w).Encode(PeerView{
			NodeID:         n.NodeID,
			OverlayIPv4:    n.OverlayIPv4,
			OverlayIPv6:    n.OverlayIPv6,
			Role:           n.Role,
			Country:        n.CountryCode,
			City:           n.City,
			ASN:            n.ASN,
			IPClass:        n.IPClass,
			IsHealthy:      n.IsHealthy,
			Quarantined:    quarantined,
			LastHeartbeat:  n.LastHeartbeat.UTC().Format(time.RFC3339),
			ActiveCircuits: n.ActiveCircuits,
			Groups:         groups,
		})
	case http.MethodDelete:
		err := ms.registry.DeleteNode(nodeID)
		if err != nil {
			http.Error(w, `{"error":"peer not found"}`, http.StatusNotFound)
			return
		}
		ms.eventBus.Publish(EventKeyRevoked, nodeID, "Peer unregistered/revoked via management API")
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(map[string]interface{}{"status": "revoked", "node_id": nodeID})
	default:
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
	}
}

func (ms *ManagementServer) handleTopologyGraph(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	type GraphNode struct {
		ID          string `json:"id"`
		Label       string `json:"label"`
		Role        string `json:"role"`
		Country     string `json:"country"`
		VIP         string `json:"vip"`
		IsHealthy   bool   `json:"is_healthy"`
		Quarantined bool   `json:"quarantined"`
	}

	type GraphEdge struct {
		Source string  `json:"source"`
		Target string  `json:"target"`
		RTTms  float64 `json:"rtt_ms"`
		Direct bool    `json:"direct_p2p"`
	}

	nodes := ms.registry.ListNodes()
	graphNodes := make([]GraphNode, 0, len(nodes))
	for _, n := range nodes {
		quarantined := false
		if ms.postureEngine != nil {
			quarantined = ms.postureEngine.QuarantineManager().IsQuarantined(n.NodeID)
		}
		graphNodes = append(graphNodes, GraphNode{
			ID:          n.NodeID,
			Label:       fmt.Sprintf("%s (%s)", n.NodeID, n.Role),
			Role:        n.Role,
			Country:     n.CountryCode,
			VIP:         n.OverlayIPv4,
			IsHealthy:   n.IsHealthy,
			Quarantined: quarantined,
		})
	}

	// Build edges among peers and relays
	graphEdges := make([]GraphEdge, 0)
	relays := ms.registry.RelaysList()
	for _, n := range nodes {
		for _, rl := range relays {
			graphEdges = append(graphEdges, GraphEdge{
				Source: n.NodeID,
				Target: rl.RelayID,
				RTTms:  n.RTTms,
				Direct: false,
			})
		}
	}

	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"nodes": graphNodes,
		"edges": graphEdges,
		"epoch": ms.registry.Epoch(),
	})
}

func (ms *ManagementServer) handleLatencyMatrix(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	nodes := ms.registry.ListNodes()
	matrix := make(map[string]map[string]float64)

	for _, src := range nodes {
		matrix[src.NodeID] = make(map[string]float64)
		for _, dst := range nodes {
			if src.NodeID == dst.NodeID {
				matrix[src.NodeID][dst.NodeID] = 0.0
			} else {
				matrix[src.NodeID][dst.NodeID] = 25.0 // Estimated pairwise RTT
			}
		}
	}

	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"timestamp_utc": time.Now().UTC().Format(time.RFC3339),
		"matrix":        matrix,
		"epoch":         ms.registry.Epoch(),
	})
}

func (ms *ManagementServer) handleACLs(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	switch r.Method {
	case http.MethodGet:
		policies := ms.aclEngine.ListPolicies()
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"policies": policies,
			"total":    len(policies),
			"epoch":    ms.aclEngine.Epoch(),
		})
	case http.MethodPost:
		var p acl.PolicyRule
		if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"invalid JSON: %s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		if err := ms.aclEngine.UpsertPolicy(&p); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		w.WriteHeader(http.StatusCreated)
		_ = json.NewEncoder(w).Encode(p)
	default:
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
	}
}

func (ms *ManagementServer) handleACLByID(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	id := strings.TrimPrefix(r.URL.Path, "/api/v4/acls/")
	if id == "" {
		http.Error(w, `{"error":"policy ID required"}`, http.StatusBadRequest)
		return
	}

	switch r.Method {
	case http.MethodGet:
		p, ok := ms.aclEngine.GetPolicy(id)
		if !ok {
			http.Error(w, `{"error":"policy not found"}`, http.StatusNotFound)
			return
		}
		_ = json.NewEncoder(w).Encode(p)
	case http.MethodPut:
		var p acl.PolicyRule
		if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"invalid JSON: %s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		p.ID = id
		if err := ms.aclEngine.UpsertPolicy(&p); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		_ = json.NewEncoder(w).Encode(p)
	case http.MethodDelete:
		if err := ms.aclEngine.DeletePolicy(id); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusNotFound)
			return
		}
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(map[string]interface{}{"status": "deleted", "id": id})
	default:
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
	}
}

func (ms *ManagementServer) handleGroups(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	switch r.Method {
	case http.MethodGet:
		groups := ms.aclEngine.ListGroups()
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"groups": groups,
			"total":  len(groups),
			"epoch":  ms.aclEngine.Epoch(),
		})
	case http.MethodPost:
		var g acl.PeerGroup
		if err := json.NewDecoder(r.Body).Decode(&g); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"invalid JSON: %s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		if err := ms.aclEngine.UpsertGroup(&g); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		w.WriteHeader(http.StatusCreated)
		_ = json.NewEncoder(w).Encode(g)
	default:
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
	}
}

func (ms *ManagementServer) handleGroupByID(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	id := strings.TrimPrefix(r.URL.Path, "/api/v4/groups/")
	if id == "" {
		http.Error(w, `{"error":"group ID required"}`, http.StatusBadRequest)
		return
	}

	switch r.Method {
	case http.MethodGet:
		g, ok := ms.aclEngine.GetGroup(id)
		if !ok {
			http.Error(w, `{"error":"group not found"}`, http.StatusNotFound)
			return
		}
		_ = json.NewEncoder(w).Encode(g)
	case http.MethodPut:
		var g acl.PeerGroup
		if err := json.NewDecoder(r.Body).Decode(&g); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"invalid JSON: %s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		g.ID = id
		if err := ms.aclEngine.UpsertGroup(&g); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		_ = json.NewEncoder(w).Encode(g)
	case http.MethodDelete:
		if err := ms.aclEngine.DeleteGroup(id); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(map[string]interface{}{"status": "deleted", "id": id})
	default:
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
	}
}

type RouteJSONView struct {
	ID           string                    `json:"id"`
	NetworkID    string                    `json:"network_id"`
	Description  string                    `json:"description"`
	NetworkCIDR  string                    `json:"network_cidr"`
	Masquerade   bool                      `json:"masquerade"`
	Failover     routes.FailoverMode       `json:"failover_mode"`
	RoutingPeers []*routes.RoutingPeerSpec `json:"routing_peers"`
	Groups       []string                  `json:"groups"`
	Enabled      bool                      `json:"enabled"`
	CreatedAt    time.Time                 `json:"created_at"`
	UpdatedAt    time.Time                 `json:"updated_at"`
}

func (ms *ManagementServer) handleRoutes(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	switch r.Method {
	case http.MethodGet:
		routesList := ms.routeTable.ListRoutes()
		jsonList := make([]RouteJSONView, 0, len(routesList))
		for _, route := range routesList {
			cidrStr := ""
			if route.NetworkCIDR != nil {
				cidrStr = route.NetworkCIDR.String()
			}
			jsonList = append(jsonList, RouteJSONView{
				ID:           route.ID,
				NetworkID:    route.NetworkID,
				Description:  route.Description,
				NetworkCIDR:  cidrStr,
				Masquerade:   route.Masquerade,
				Failover:     route.Failover,
				RoutingPeers: route.RoutingPeers,
				Groups:       route.Groups,
				Enabled:      route.Enabled,
				CreatedAt:    route.CreatedAt,
				UpdatedAt:    route.UpdatedAt,
			})
		}
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"routes": jsonList,
			"total":  len(jsonList),
			"epoch":  ms.routeTable.Epoch(),
		})
	case http.MethodPost:
		var req RouteJSONView
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"invalid JSON: %s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		route, err := ms.routeTable.AddRoute(req.ID, req.NetworkID, req.NetworkCIDR, req.RoutingPeers, req.Groups, req.Masquerade, req.Failover)
		if err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		w.WriteHeader(http.StatusCreated)
		_ = json.NewEncoder(w).Encode(RouteJSONView{
			ID:           route.ID,
			NetworkID:    route.NetworkID,
			Description:  route.Description,
			NetworkCIDR:  route.NetworkCIDR.String(),
			Masquerade:   route.Masquerade,
			Failover:     route.Failover,
			RoutingPeers: route.RoutingPeers,
			Groups:       route.Groups,
			Enabled:      route.Enabled,
			CreatedAt:    route.CreatedAt,
			UpdatedAt:    route.UpdatedAt,
		})
	default:
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
	}
}

func (ms *ManagementServer) handleRouteByID(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	id := strings.TrimPrefix(r.URL.Path, "/api/v4/routes/")
	if id == "" {
		http.Error(w, `{"error":"route ID required"}`, http.StatusBadRequest)
		return
	}

	switch r.Method {
	case http.MethodGet:
		route, ok := ms.routeTable.GetRoute(id)
		if !ok {
			http.Error(w, `{"error":"route not found"}`, http.StatusNotFound)
			return
		}
		_ = json.NewEncoder(w).Encode(RouteJSONView{
			ID:           route.ID,
			NetworkID:    route.NetworkID,
			Description:  route.Description,
			NetworkCIDR:  route.NetworkCIDR.String(),
			Masquerade:   route.Masquerade,
			Failover:     route.Failover,
			RoutingPeers: route.RoutingPeers,
			Groups:       route.Groups,
			Enabled:      route.Enabled,
			CreatedAt:    route.CreatedAt,
			UpdatedAt:    route.UpdatedAt,
		})
	case http.MethodPut:
		var req RouteJSONView
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"invalid JSON: %s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		_, ipnet, err := net.ParseCIDR(req.NetworkCIDR)
		if err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"invalid CIDR: %s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		route := &routes.NetworkRoute{
			ID:           id,
			NetworkID:    req.NetworkID,
			Description:  req.Description,
			NetworkCIDR:  ipnet,
			Masquerade:   req.Masquerade,
			Failover:     req.Failover,
			RoutingPeers: req.RoutingPeers,
			Groups:       req.Groups,
			Enabled:      req.Enabled,
		}
		if err := ms.routeTable.UpsertRoute(route); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		_ = json.NewEncoder(w).Encode(req)
	case http.MethodDelete:
		if err := ms.routeTable.DeleteRoute(id); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusNotFound)
			return
		}
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(map[string]interface{}{"status": "deleted", "id": id})
	default:
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
	}
}

func (ms *ManagementServer) handlePostureChecks(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	switch r.Method {
	case http.MethodGet:
		policies := ms.postureEngine.ListPolicies()
		quarantined := ms.postureEngine.QuarantineManager().ListQuarantinedPeers()
		_ = json.NewEncoder(w).Encode(map[string]interface{}{
			"posture_checks": policies,
			"quarantined":    quarantined,
			"total":          len(policies),
			"epoch":          ms.postureEngine.Epoch(),
		})
	case http.MethodPost:
		var p posture.PosturePolicy
		if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"invalid JSON: %s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		if err := ms.postureEngine.UpsertPolicy(&p); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		w.WriteHeader(http.StatusCreated)
		_ = json.NewEncoder(w).Encode(p)
	default:
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
	}
}

func (ms *ManagementServer) handlePostureCheckByID(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	id := strings.TrimPrefix(r.URL.Path, "/api/v4/posture-checks/")
	if id == "" {
		http.Error(w, `{"error":"posture check ID required"}`, http.StatusBadRequest)
		return
	}

	switch r.Method {
	case http.MethodGet:
		p, ok := ms.postureEngine.GetPolicy(id)
		if !ok {
			http.Error(w, `{"error":"posture check not found"}`, http.StatusNotFound)
			return
		}
		_ = json.NewEncoder(w).Encode(p)
	case http.MethodPut:
		var p posture.PosturePolicy
		if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"invalid JSON: %s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		p.ID = id
		if err := ms.postureEngine.UpsertPolicy(&p); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusBadRequest)
			return
		}
		_ = json.NewEncoder(w).Encode(p)
	case http.MethodDelete:
		if err := ms.postureEngine.DeletePolicy(id); err != nil {
			http.Error(w, fmt.Sprintf(`{"error":"%s"}`, err.Error()), http.StatusNotFound)
			return
		}
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(map[string]interface{}{"status": "deleted", "id": id})
	default:
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
	}
}

func (ms *ManagementServer) handleEvents(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if r.Method != http.MethodGet {
		http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		return
	}

	limit := 50
	if limStr := r.URL.Query().Get("limit"); limStr != "" {
		if l, err := strconv.Atoi(limStr); err == nil && l > 0 {
			limit = l
		}
	}

	events := ms.eventBus.GetRecentEvents(limit)
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"events": events,
		"total":  len(events),
	})
}

func (ms *ManagementServer) handlePrometheusMetrics(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	output := GeneratePrometheusMetrics(
		ms.registry,
		ms.aclEngine,
		ms.routeTable,
		ms.postureEngine,
		ms.eventBus,
	)
	_, _ = w.Write([]byte(output))
}
