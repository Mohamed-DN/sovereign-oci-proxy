package main

import (
	"context"
	"io"
	"net"
	"sync"
	"testing"
	"time"
)

func TestWhitelist(t *testing.T) {
	cidrs := []string{
		"127.0.0.0/8",
		"10.0.0.0/8",
		"172.16.0.0/12",
		"192.168.0.0/16",
		"100.64.0.0/10",
		"1.1.1.1/32",
		"8.8.8.8",
		"9.9.9.9",
	}

	wm, err := NewWhitelistManager(cidrs)
	if err != nil {
		t.Fatalf("Failed to create whitelist manager: %v", err)
	}

	// Should be whitelisted
	whitelisted := []string{
		"127.0.0.1",
		"10.200.1.5",
		"172.20.10.2",
		"192.168.1.100",
		"100.64.0.1",
		"1.1.1.1",
		"8.8.8.8",
		"9.9.9.9",
	}

	for _, ipStr := range whitelisted {
		ip := net.ParseIP(ipStr)
		if !wm.IsWhitelisted(ip) {
			t.Errorf("Expected IP %s to be whitelisted, got false", ipStr)
		}
	}

	// Should NOT be whitelisted
	nonWhitelisted := []string{
		"198.51.100.25",
		"203.0.113.50",
		"45.33.32.156",
		"185.220.101.5",
	}

	for _, ipStr := range nonWhitelisted {
		ip := net.ParseIP(ipStr)
		if wm.IsWhitelisted(ip) {
			t.Errorf("Expected IP %s to NOT be whitelisted, got true", ipStr)
		}
	}
}

func TestDualTokenBucketLimiter(t *testing.T) {
	limiter := NewDualTokenBucketLimiter(5, 1.0, 10, 2.0)
	defer limiter.Close()

	testIP := net.ParseIP("203.0.113.10")

	// Consume first 5 tokens immediately (should all succeed)
	for i := 0; i < 5; i++ {
		if !limiter.Allow(testIP) {
			t.Fatalf("Expected token %d to be allowed", i+1)
		}
	}

	// 6th token should be rejected
	if limiter.Allow(testIP) {
		t.Fatalf("Expected 6th immediate token to be rejected due to capacity limit")
	}

	// Test concurrent token access
	var wg sync.WaitGroup
	allowedCount := 0
	var mu sync.Mutex

	for i := 0; i < 20; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			ip := net.ParseIP("203.0.113.20")
			if limiter.Allow(ip) {
				mu.Lock()
				allowedCount++
				mu.Unlock()
			}
		}(i)
	}
	wg.Wait()

	if allowedCount > 5 {
		t.Fatalf("Expected at most 5 concurrent requests allowed from fresh IP, got %d", allowedCount)
	}
}

func TestThreatScorerDecay(t *testing.T) {
	halfLife := 200 * time.Millisecond
	scorer := NewThreatScorer(100, halfLife, 10*time.Minute)
	defer scorer.Close()

	testIP := net.ParseIP("198.51.100.77")

	// Add 40 points -> score 40, no ban
	score1, ban1 := scorer.RecordThreat(testIP, 40)
	if ban1 {
		t.Fatalf("Did not expect ban at score %.1f", score1)
	}
	if score1 != 40 {
		t.Fatalf("Expected score 40, got %.1f", score1)
	}

	// Add 70 points -> score 110, triggers ban
	score2, ban2 := scorer.RecordThreat(testIP, 70)
	if !ban2 {
		t.Fatalf("Expected ban trigger when score is %.1f >= 100", score2)
	}

	// Wait for 2 half-lives (400ms) -> score should decay to ~1/4th (around 27)
	time.Sleep(450 * time.Millisecond)
	decayed := scorer.GetScore(testIP)
	if decayed > 35.0 || decayed < 15.0 {
		t.Fatalf("Expected decayed score around ~27, got %.2f", decayed)
	}
}

func TestMockFirewallDriver(t *testing.T) {
	driver := NewMockFirewallDriver()
	defer driver.Close()

	ctx := context.Background()
	testIP := net.ParseIP("203.0.113.99")

	// Initially not banned
	banned, err := driver.IsBanned(ctx, testIP)
	if err != nil || banned {
		t.Fatalf("Expected not banned initially, got banned=%v, err=%v", banned, err)
	}

	// Ban for 300ms
	err = driver.Ban(ctx, testIP, 300*time.Millisecond, "Test Ban")
	if err != nil {
		t.Fatalf("Failed to ban: %v", err)
	}

	// Verify banned
	banned, err = driver.IsBanned(ctx, testIP)
	if err != nil || !banned {
		t.Fatalf("Expected banned=true, got banned=%v, err=%v", banned, err)
	}

	list, err := driver.ListBanned(ctx)
	if err != nil || len(list) != 1 {
		t.Fatalf("Expected 1 banned entry in list, got %d", len(list))
	}

	// Wait for TTL expiration
	time.Sleep(400 * time.Millisecond)
	banned, err = driver.IsBanned(ctx, testIP)
	if err != nil || banned {
		t.Fatalf("Expected ban to expire, got banned=%v", banned)
	}
}

func TestSecurityDaemonEndToEnd(t *testing.T) {
	cfg := DefaultConfig()
	cfg.HoneypotPort = 18080
	cfg.FirewallDriver = "mock"
	cfg.ThreatScoreBan = 50
	cfg.DryRun = true

	daemon, err := NewSecurityDaemon(cfg)
	if err != nil {
		t.Fatalf("Failed to initialize daemon: %v", err)
	}

	if err := daemon.Start(); err != nil {
		t.Fatalf("Failed to start daemon: %v", err)
	}
	defer func() {
		_ = daemon.Stop()
	}()

	time.Sleep(50 * time.Millisecond)

	// Test connection from loopback (whitelisted)
	conn, err := net.DialTimeout("tcp", "127.0.0.1:18080", 1*time.Second)
	if err != nil {
		t.Fatalf("Failed to connect to honeypot: %v", err)
	}
	buf := make([]byte, 256)
	n, err := conn.Read(buf)
	if err != nil && err != io.EOF {
		t.Fatalf("Error reading banner: %v", err)
	}
	_ = conn.Close()

	if n == 0 {
		t.Fatalf("Expected honeypot banner response, got 0 bytes")
	}

	// Verify that loopback IP was NOT banned
	ctx := context.Background()
	banned, _ := daemon.firewall.IsBanned(ctx, net.ParseIP("127.0.0.1"))
	if banned {
		t.Fatalf("Whitelisted 127.0.0.1 must never be banned")
	}
}
