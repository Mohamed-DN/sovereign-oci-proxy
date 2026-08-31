package main

import (
	"fmt"
	"net"
	"strings"
	"sync"
)

// WhitelistManager manages network whitelisting and bogon subnet containment.
type WhitelistManager struct {
	mu       sync.RWMutex
	networks []*net.IPNet
	ips      map[string]bool
}

// NewWhitelistManager creates and initializes a WhitelistManager from CIDR strings.
func NewWhitelistManager(cidrs []string) (*WhitelistManager, error) {
	wm := &WhitelistManager{
		networks: make([]*net.IPNet, 0, len(cidrs)),
		ips:      make(map[string]bool),
	}

	for _, raw := range cidrs {
		raw = strings.TrimSpace(raw)
		if raw == "" {
			continue
		}
		if err := wm.Add(raw); err != nil {
			return nil, fmt.Errorf("invalid whitelist entry %q: %w", raw, err)
		}
	}

	return wm, nil
}

// Add adds a single CIDR or IP address to the whitelist.
func (wm *WhitelistManager) Add(raw string) error {
	wm.mu.Lock()
	defer wm.mu.Unlock()

	raw = strings.TrimSpace(raw)
	if strings.Contains(raw, "/") {
		_, ipNet, err := net.ParseCIDR(raw)
		if err != nil {
			return err
		}
		wm.networks = append(wm.networks, ipNet)
	} else {
		parsedIP := net.ParseIP(raw)
		if parsedIP == nil {
			return fmt.Errorf("invalid IP: %s", raw)
		}
		wm.ips[parsedIP.String()] = true
	}
	return nil
}

// IsWhitelisted checks if an IP is whitelisted or in a protected bogon/private network.
func (wm *WhitelistManager) IsWhitelisted(ip net.IP) bool {
	if ip == nil {
		return true // Treat nil/unparsable as safe to prevent accidental kernel panic or drop
	}

	wm.mu.RLock()
	defer wm.mu.RUnlock()

	// Direct IP check
	if wm.ips[ip.String()] {
		return true
	}

	// Network CIDR check
	for _, network := range wm.networks {
		if network.Contains(ip) {
			return true
		}
	}

	// Built-in special case checks
	if ip.IsLoopback() || ip.IsPrivate() || ip.IsLinkLocalUnicast() || ip.IsLinkLocalMulticast() || ip.IsUnspecified() {
		return true
	}

	return false
}
