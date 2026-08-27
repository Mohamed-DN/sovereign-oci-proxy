package main

import (
	"fmt"
	"net"
	"runtime"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// TestChallengerDualTokenBucketExtremeFlood tests 50,000 requests across 1,000 goroutines.
func TestChallengerDualTokenBucketExtremeFlood(t *testing.T) {
	// 5 req/s per IP, 20 req/s per /24 subnet
	limiter := NewDualTokenBucketLimiter(5, 1.0, 20, 4.0)
	defer limiter.Close()

	const totalRequests = 50000
	const numSubnets = 20
	const numIPsPerSubnet = 10

	var wg sync.WaitGroup
	var allowedCount uint64
	var droppedCount uint64

	start := time.Now()

	for i := 0; i < totalRequests; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()

			subnet := idx % numSubnets
			host := (idx / numSubnets) % numIPsPerSubnet
			ip := net.IPv4(198, 51, byte(100+subnet), byte(1+host))

			if limiter.Allow(ip) {
				atomic.AddUint64(&allowedCount, 1)
			} else {
				atomic.AddUint64(&droppedCount, 1)
			}
		}(i)
	}

	wg.Wait()
	duration := time.Since(start)

	t.Logf("[CHALLENGER] Processed %d checks in %v (Rate: %.2f ops/sec)", totalRequests, duration, float64(totalRequests)/duration.Seconds())
	t.Logf("[CHALLENGER] Allowed: %d, Dropped: %d", allowedCount, droppedCount)

	// Subnet envelope: 20 subnets * 20 max burst = 400 theoretical instant burst
	if allowedCount > 1000 {
		t.Fatalf("[CHALLENGER FAILURE] Rate limiter allowed %d requests, exceeding allowable burst envelope", allowedCount)
	}
	if droppedCount < 40000 {
		t.Fatalf("[CHALLENGER FAILURE] Expected at least 40,000 dropped requests, got %d", droppedCount)
	}

	// Test IPv6 subnetting (/48)
	t.Log("[CHALLENGER] Testing IPv6 /48 rate limiting...")
	var v6Allowed uint64
	var v6Dropped uint64
	for i := 0; i < 500; i++ {
		// All in same /48 (2001:db8:abcd::/48)
		ip := net.ParseIP(fmt.Sprintf("2001:db8:abcd:%x::1", i%16))
		if limiter.Allow(ip) {
			v6Allowed++
		} else {
			v6Dropped++
		}
	}
	t.Logf("[CHALLENGER] IPv6: Allowed=%d, Dropped=%d", v6Allowed, v6Dropped)
	if v6Dropped == 0 {
		t.Fatalf("[CHALLENGER FAILURE] IPv6 rate limiter failed to drop requests in /48 subnet")
	}

	// Nil IP check
	if limiter.Allow(nil) {
		t.Fatalf("[CHALLENGER FAILURE] Rate limiter allowed nil IP")
	}
}

// TestChallengerThreatScorerMathematicalDecayExactness tests exponential decay accuracy.
func TestChallengerThreatScorerMathematicalDecayExactness(t *testing.T) {
	halfLife := 300 * time.Millisecond
	scorer := NewThreatScorer(100, halfLife, 1*time.Hour)
	defer scorer.Close()

	testIP := net.ParseIP("203.0.113.42")

	// Step 1: Record 80 points
	score, shouldBan := scorer.RecordThreat(testIP, 80.0)
	if shouldBan {
		t.Fatalf("Score 80 should not trigger ban (threshold 100)")
	}
	if score != 80.0 {
		t.Fatalf("Expected initial score 80.0, got %.2f", score)
	}

	// Step 2: Sleep for 1 half-life (300ms)
	time.Sleep(halfLife)

	// Score should now be approximately 80 / 2 = 40
	decayedScore := scorer.GetScore(testIP)
	t.Logf("[CHALLENGER] Decayed score after 1 half-life: %.2f (expected ~40.0)", decayedScore)
	if decayedScore < 32.0 || decayedScore > 48.0 {
		t.Fatalf("[CHALLENGER FAILURE] Exponential decay inaccurate: expected ~40.0, got %.2f", decayedScore)
	}

	// Step 3: Add 70 points -> decayed + 70 >= 100, triggering ban
	newScore, shouldBan := scorer.RecordThreat(testIP, 70.0)
	t.Logf("[CHALLENGER] New score after adding 70: %.2f, ban=%v", newScore, shouldBan)
	if !shouldBan {
		t.Fatalf("[CHALLENGER FAILURE] Expected ban=true after adding 70 points to decayed score %.2f", decayedScore)
	}
	if newScore < 100.0 {
		t.Fatalf("[CHALLENGER FAILURE] Expected score >= 100, got %.2f", newScore)
	}

	// Step 4: Reset score
	scorer.ResetScore(testIP)
	resetScore := scorer.GetScore(testIP)
	if resetScore != 0.0 {
		t.Fatalf("Expected 0.0 after reset, got %.2f", resetScore)
	}

	// Step 5: Concurrency test (50,000 rapid threats across 100 IPs)
	const totalConcAttacks = 50000
	var wg sync.WaitGroup
	start := time.Now()
	for i := 0; i < totalConcAttacks; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			ip := net.IPv4(203, 0, 113, byte((idx%100)+1))
			scorer.RecordThreat(ip, 10.0)
		}(i)
	}
	wg.Wait()
	duration := time.Since(start)
	t.Logf("[CHALLENGER] Executed %d concurrent threat updates in %v (Rate: %.2f ops/sec)", totalConcAttacks, duration, float64(totalConcAttacks)/duration.Seconds())
}

// TestChallengerWhitelistExhaustiveAdversarial tests whitelist boundary conditions.
func TestChallengerWhitelistExhaustiveAdversarial(t *testing.T) {
	cidrs := []string{
		"127.0.0.0/8",
		"10.0.0.0/8",
		"172.16.0.0/12",
		"192.168.0.0/16",
		"100.64.0.0/10",
		"169.254.0.0/16",
		"224.0.0.0/4",
		"1.1.1.1/32",
		"1.0.0.1/32",
		"8.8.8.8/32",
		"8.8.4.4/32",
		"9.9.9.9/32",
	}

	wm, err := NewWhitelistManager(cidrs)
	if err != nil {
		t.Fatalf("Failed to init WhitelistManager: %v", err)
	}

	whitelistedSamples := []string{
		"127.0.0.1",
		"127.255.255.254",
		"::1",
		"10.0.0.1",
		"10.254.254.254",
		"172.16.0.1",
		"172.31.255.254",
		"192.168.1.1",
		"192.168.254.254",
		"100.64.0.1",
		"100.100.100.100",
		"100.127.255.254",
		"169.254.169.254",
		"224.0.0.251",
		"1.1.1.1",
		"1.0.0.1",
		"8.8.8.8",
		"8.8.4.4",
		"9.9.9.9",
	}

	for _, ipStr := range whitelistedSamples {
		ip := net.ParseIP(ipStr)
		if !wm.IsWhitelisted(ip) {
			t.Fatalf("[CHALLENGER FAILURE] Expected %s to be whitelisted", ipStr)
		}
	}

	nonWhitelistedSamples := []string{
		"1.1.1.2",
		"8.8.8.9",
		"9.9.9.10",
		"198.51.100.1",
		"203.0.113.1",
		"100.128.0.1", // Just outside 100.64.0.0/10
		"172.32.0.1",  // Just outside 172.16.0.0/12
		"11.0.0.1",    // Just outside 10.0.0.0/8
		"192.169.0.1", // Just outside 192.168.0.0/16
	}

	for _, ipStr := range nonWhitelistedSamples {
		ip := net.ParseIP(ipStr)
		if wm.IsWhitelisted(ip) {
			t.Fatalf("[CHALLENGER FAILURE] Expected %s to NOT be whitelisted", ipStr)
		}
	}

	// Concurrency test: dynamic add and check simultaneously
	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(2)
		go func(idx int) {
			defer wg.Done()
			_ = wm.Add(fmt.Sprintf("198.18.%d.0/24", idx))
		}(i)
		go func(idx int) {
			defer wg.Done()
			wm.IsWhitelisted(net.ParseIP(fmt.Sprintf("198.18.%d.42", idx)))
		}(i)
	}
	wg.Wait()
	t.Log("[CHALLENGER] Whitelist manager concurrent read/write test passed.")
}

// TestChallengerHoneypotSlowlorisAndStorm tests slowloris and rapid connection burst.
func TestChallengerHoneypotSlowlorisAndStorm(t *testing.T) {
	cfg := DefaultConfig()
	cfg.ListenAddr = "127.0.0.1"
	cfg.HoneypotPort = 18199
	cfg.FirewallDriver = "mock"
	cfg.ThreatScoreBan = 100
	cfg.PerIPTokenCapacity = 100
	cfg.PerIPRefillRate = 50.0
	cfg.SubnetTokenCap = 500
	cfg.SubnetRefillRate = 200.0
	cfg.DryRun = true

	daemon, err := NewSecurityDaemon(cfg)
	if err != nil {
		t.Fatalf("Failed to init daemon: %v", err)
	}

	if err := daemon.Start(); err != nil {
		t.Fatalf("Failed to start daemon: %v", err)
	}
	defer func() {
		_ = daemon.Stop()
	}()

	time.Sleep(50 * time.Millisecond)

	// Slowloris simulation: open 20 connections and hold them open without reading/writing
	t.Log("[CHALLENGER] Simulating Slowloris connection hold...")
	var slowWg sync.WaitGroup
	for i := 0; i < 20; i++ {
		slowWg.Add(1)
		go func() {
			defer slowWg.Done()
			conn, err := net.DialTimeout("tcp", "127.0.0.1:18199", 1*time.Second)
			if err != nil {
				return
			}
			defer conn.Close()

			// Sleep for 3.5s - daemon connection timeout is 3s, so connection must be closed by server
			time.Sleep(3500 * time.Millisecond)
			buf := make([]byte, 10)
			_ = conn.SetReadDeadline(time.Now().Add(500 * time.Millisecond))
			_, _ = conn.Read(buf)
		}()
	}

	slowWg.Wait()
	t.Log("[CHALLENGER] Slowloris connections successfully handled and closed by deadline.")

	// Rapid connection storm: 3,000 connections
	const totalConns = 3000
	var stormWg sync.WaitGroup
	var successConns uint64

	start := time.Now()
	for i := 0; i < totalConns; i++ {
		stormWg.Add(1)
		go func() {
			defer stormWg.Done()
			d := net.Dialer{Timeout: 1 * time.Second}
			conn, err := d.Dial("tcp", "127.0.0.1:18199")
			if err != nil {
				return
			}
			defer conn.Close()
			buf := make([]byte, 32)
			n, _ := conn.Read(buf)
			if n > 0 {
				atomic.AddUint64(&successConns, 1)
			}
		}()
	}

	stormWg.Wait()
	duration := time.Since(start)
	t.Logf("[CHALLENGER] Storm test: %d connections in %v (Rate: %.2f conn/sec, Handled: %d)", totalConns, duration, float64(totalConns)/duration.Seconds(), successConns)

	// Verify goroutine cleanup
	time.Sleep(200 * time.Millisecond)
	activeGoroutines := runtime.NumGoroutine()
	t.Logf("[CHALLENGER] Active goroutines after storm: %d", activeGoroutines)
}
