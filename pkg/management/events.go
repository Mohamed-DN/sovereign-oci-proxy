package management

import (
	"sync"
	"time"
)

// EventType categorizes network events
type EventType string

const (
	EventPeerRegistered    EventType = "PEER_REGISTERED"
	EventPeerQuarantined   EventType = "PEER_QUARANTINED"
	EventPeerUnquarantined EventType = "PEER_UNQUARANTINED"
	EventRouteFailover     EventType = "ROUTE_FAILOVER"
	EventACLViolation      EventType = "ACL_VIOLATION"
	EventKeyRevoked        EventType = "KEY_REVOKED"
)

// AuditEvent represents an auditable network state change
type AuditEvent struct {
	ID        uint64    `json:"id"`
	Type      EventType `json:"type"`
	NodeID    string    `json:"node_id"`
	Details   string    `json:"details"`
	Timestamp time.Time `json:"timestamp_utc"`
}

// EventBus provides circular buffer event retention and subscriber dispatch
type EventBus struct {
	mu       sync.RWMutex
	capacity int
	events   []AuditEvent
	seq      uint64
}

// NewEventBus initializes the audit event bus
func NewEventBus(capacity int) *EventBus {
	if capacity <= 0 {
		capacity = 1000
	}
	return &EventBus{
		capacity: capacity,
		events:   make([]AuditEvent, 0, capacity),
	}
}

// Publish adds a new event to the bus
func (eb *EventBus) Publish(evtType EventType, nodeID, details string) {
	eb.mu.Lock()
	defer eb.mu.Unlock()

	eb.seq++
	evt := AuditEvent{
		ID:        eb.seq,
		Type:      evtType,
		NodeID:    nodeID,
		Details:   details,
		Timestamp: time.Now().UTC(),
	}

	if len(eb.events) >= eb.capacity {
		eb.events = eb.events[1:]
	}
	eb.events = append(eb.events, evt)
}

// GetRecentEvents retrieves the last N events (most recent first or chronological)
func (eb *EventBus) GetRecentEvents(limit int) []AuditEvent {
	eb.mu.RLock()
	defer eb.mu.RUnlock()

	n := len(eb.events)
	if limit <= 0 || limit > n {
		limit = n
	}

	result := make([]AuditEvent, limit)
	start := n - limit
	copy(result, eb.events[start:])
	return result
}

// EventCount returns total recorded events sequence number
func (eb *EventBus) EventCount() uint64 {
	eb.mu.RLock()
	defer eb.mu.RUnlock()
	return eb.seq
}
