package control

import (
	"encoding/binary"
	"errors"
	"fmt"
	"net"
	"sync"
)

var (
	ErrNoVIPAvailable = errors.New("overlay VIP pool exhausted")
)

// VIPAllocator manages dynamic overlay IPv4 and IPv6 assignment
type VIPAllocator struct {
	mu          sync.Mutex
	baseIPv4    uint32 // e.g. 100.64.0.1
	maxIPv4     uint32 // e.g. 100.127.255.254
	nextOffset  uint32
	allocated   map[string]uint32 // nodeID -> ipv4 uint32
	ipv6Prefix  string            // e.g. "fd7a:115c:a1e0"
}

// NewVIPAllocator creates a new allocator for 100.64.0.0/10
func NewVIPAllocator() *VIPAllocator {
	base := binary.BigEndian.Uint32(net.ParseIP("100.64.0.2").To4())
	max := binary.BigEndian.Uint32(net.ParseIP("100.127.255.254").To4())

	return &VIPAllocator{
		baseIPv4:   base,
		maxIPv4:    max,
		nextOffset: 0,
		allocated:  make(map[string]uint32),
		ipv6Prefix: "fd7a:115c:a1e0",
	}
}

// Allocate assigns a unique overlay IPv4 and IPv6 address to a node ID
func (a *VIPAllocator) Allocate(nodeID string) (ipv4 string, ipv6 string, err error) {
	a.mu.Lock()
	defer a.mu.Unlock()

	if existing, ok := a.allocated[nodeID]; ok {
		return uint32ToIP(existing).String(), fmt.Sprintf("%s::%x", a.ipv6Prefix, existing-a.baseIPv4+2), nil
	}

	if a.baseIPv4+a.nextOffset > a.maxIPv4 {
		return "", "", ErrNoVIPAvailable
	}

	ipInt := a.baseIPv4 + a.nextOffset
	a.nextOffset++
	a.allocated[nodeID] = ipInt

	ip := uint32ToIP(ipInt)
	ipv6Str := fmt.Sprintf("%s::%x", a.ipv6Prefix, a.nextOffset+1)

	return ip.String(), ipv6Str, nil
}

// Release frees an allocated overlay IP
func (a *VIPAllocator) Release(nodeID string) {
	a.mu.Lock()
	defer a.mu.Unlock()
	delete(a.allocated, nodeID)
}

func uint32ToIP(n uint32) net.IP {
	ip := make(net.IP, 4)
	binary.BigEndian.PutUint32(ip, n)
	return ip
}
