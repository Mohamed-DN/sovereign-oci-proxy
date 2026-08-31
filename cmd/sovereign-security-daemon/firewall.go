package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"os/exec"
	"strconv"
	"sync"
	"time"
)

// BanEntry represents a banned IP and its metadata.
type BanEntry struct {
	IP        string    `json:"ip"`
	BannedAt  time.Time `json:"banned_at"`
	ExpiresAt time.Time `json:"expires_at"`
	Reason    string    `json:"reason"`
}

// FirewallDriver is the interface for pluggable non-blocking packet drop engines.
type FirewallDriver interface {
	Ban(ctx context.Context, ip net.IP, duration time.Duration, reason string) error
	Unban(ctx context.Context, ip net.IP) error
	IsBanned(ctx context.Context, ip net.IP) (bool, error)
	ListBanned(ctx context.Context) ([]BanEntry, error)
	Close() error
}

// --- Mock Driver (Thread-safe, TTL-based, perfect for CI/Tests) ---

// MockFirewallDriver maintains an in-memory ban table.
type MockFirewallDriver struct {
	mu       sync.RWMutex
	banned   map[string]BanEntry
	stopChan chan struct{}
}

// NewMockFirewallDriver creates a new in-memory MockFirewallDriver.
func NewMockFirewallDriver() *MockFirewallDriver {
	d := &MockFirewallDriver{
		banned:   make(map[string]BanEntry),
		stopChan: make(chan struct{}),
	}
	go d.evictionLoop()
	return d
}

func (m *MockFirewallDriver) Ban(ctx context.Context, ip net.IP, duration time.Duration, reason string) error {
	if ip == nil {
		return fmt.Errorf("cannot ban nil IP")
	}
	m.mu.Lock()
	defer m.mu.Unlock()

	now := time.Now()
	m.banned[ip.String()] = BanEntry{
		IP:        ip.String(),
		BannedAt:  now,
		ExpiresAt: now.Add(duration),
		Reason:    reason,
	}
	return nil
}

func (m *MockFirewallDriver) Unban(ctx context.Context, ip net.IP) error {
	if ip == nil {
		return nil
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.banned, ip.String())
	return nil
}

func (m *MockFirewallDriver) IsBanned(ctx context.Context, ip net.IP) (bool, error) {
	if ip == nil {
		return false, nil
	}
	m.mu.RLock()
	defer m.mu.RUnlock()
	entry, exists := m.banned[ip.String()]
	if !exists {
		return false, nil
	}
	if time.Now().After(entry.ExpiresAt) {
		return false, nil
	}
	return true, nil
}

func (m *MockFirewallDriver) ListBanned(ctx context.Context) ([]BanEntry, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	now := time.Now()
	list := make([]BanEntry, 0, len(m.banned))
	for _, entry := range m.banned {
		if now.Before(entry.ExpiresAt) {
			list = append(list, entry)
		}
	}
	return list, nil
}

func (m *MockFirewallDriver) evictionLoop() {
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-m.stopChan:
			return
		case now := <-ticker.C:
			m.mu.Lock()
			for k, entry := range m.banned {
				if now.After(entry.ExpiresAt) {
					delete(m.banned, k)
				}
			}
			m.mu.Unlock()
		}
	}
}

func (m *MockFirewallDriver) Close() error {
	select {
	case <-m.stopChan:
	default:
		close(m.stopChan)
	}
	return nil
}

// --- Linux IPSet Driver (O(1) Kernel Hash Table) ---

type IPSetDriver struct {
	setName string
	dryRun  bool
	mock    *MockFirewallDriver
}

func NewIPSetDriver(setName string, dryRun bool) (*IPSetDriver, error) {
	if setName == "" {
		setName = "sovereign-ban"
	}
	d := &IPSetDriver{
		setName: setName,
		dryRun:  dryRun,
		mock:    NewMockFirewallDriver(),
	}

	if !dryRun {
		// Ensure ipset exists: ipset create sovereign-ban hash:ip timeout 86400 -exist
		cmd := exec.Command("ipset", "create", setName, "hash:ip", "timeout", "86400", "-exist")
		if out, err := cmd.CombinedOutput(); err != nil {
			log.Printf("[Firewall] Warning: ipset create error (%v): %s. Falling back to mock tracking.", err, string(out))
		}
	}

	return d, nil
}

func (d *IPSetDriver) Ban(ctx context.Context, ip net.IP, duration time.Duration, reason string) error {
	d.mock.Ban(ctx, ip, duration, reason)
	if d.dryRun {
		return nil
	}
	timeoutSec := int(duration.Seconds())
	if timeoutSec <= 0 {
		timeoutSec = 86400
	}
	cmd := exec.CommandContext(ctx, "ipset", "add", d.setName, ip.String(), "timeout", strconv.Itoa(timeoutSec), "-exist")
	return cmd.Run()
}

func (d *IPSetDriver) Unban(ctx context.Context, ip net.IP) error {
	d.mock.Unban(ctx, ip)
	if d.dryRun {
		return nil
	}
	cmd := exec.CommandContext(ctx, "ipset", "del", d.setName, ip.String())
	return cmd.Run()
}

func (d *IPSetDriver) IsBanned(ctx context.Context, ip net.IP) (bool, error) {
	if d.dryRun {
		return d.mock.IsBanned(ctx, ip)
	}
	cmd := exec.CommandContext(ctx, "ipset", "test", d.setName, ip.String())
	err := cmd.Run()
	if err == nil {
		return true, nil
	}
	return false, nil
}

func (d *IPSetDriver) ListBanned(ctx context.Context) ([]BanEntry, error) {
	return d.mock.ListBanned(ctx)
}

func (d *IPSetDriver) Close() error {
	return d.mock.Close()
}

// --- Factory Constructor ---

func NewFirewallDriver(name string, dryRun bool) (FirewallDriver, error) {
	switch name {
	case "ipset":
		return NewIPSetDriver("sovereign-ban", dryRun)
	case "mock", "":
		return NewMockFirewallDriver(), nil
	default:
		return NewMockFirewallDriver(), nil
	}
}
