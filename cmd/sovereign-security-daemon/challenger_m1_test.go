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

// TestSecurityDaemonHighConcurrencySYNFloodAndGoroutineZeroLeak hammers the daemon
// with 5,000 concurrent adversarial TCP connections (abrupt closes, junk data, slowloris)
// and asserts zero goroutine leaks upon completion and shutdown.
func TestSecurityDaemonHighConcurrencySYNFloodAndGoroutineZeroLeak(t *testing.T) {
	runtime.GC()
	time.Sleep(50 * time.Millisecond)
	baselineGoroutines := runtime.NumGoroutine()

	cfg := DefaultConfig()
	cfg.ListenAddr = "127.0.0.1"
	cfg.HoneypotPort = 18199
	cfg.FirewallDriver = "mock"
	cfg.PerIPTokenCapacity = 50
	cfg.PerIPRefillRate = 25.0
	cfg.SubnetTokenCap = 250
	cfg.SubnetRefillRate = 100.0
	cfg.DryRun = true

	daemon, err := NewSecurityDaemon(cfg)
	if err != nil {
		t.Fatalf("Failed to create daemon: %v", err)
	}

	if err := daemon.Start(); err != nil {
		t.Fatalf("Failed to start daemon: %v", err)
	}

	const totalConnections = 5000
	var wg sync.WaitGroup
	var completed uint64
	var droppedOrFailed uint64

	start := time.Now()

	for i := 0; i < totalConnections; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()

			d := net.Dialer{Timeout: 2 * time.Second}
			conn, err := d.Dial("tcp", "127.0.0.1:18199")
			if err != nil {
				atomic.AddUint64(&droppedOrFailed, 1)
				return
			}
			defer conn.Close()

			switch idx % 4 {
			case 0:
				// Scenario A: Rapid connect and immediate close (SYN/RST behavior)
				return
			case 1:
				// Scenario B: Send garbage / malformed payload
				_ = conn.SetDeadline(time.Now().Add(500 * time.Millisecond))
				_, _ = conn.Write([]byte("MALFORMED_GARBAGE_PAYLOAD_NON_HTTP_PROBE\r\n\r\n"))
				buf := make([]byte, 128)
				_, _ = conn.Read(buf)
				atomic.AddUint64(&completed, 1)
			case 2:
				// Scenario C: Partial slow write
				_ = conn.SetDeadline(time.Now().Add(300 * time.Millisecond))
				_, _ = conn.Write([]byte("GET /"))
				time.Sleep(50 * time.Millisecond)
				_, _ = conn.Write([]byte(" HTTP/1.1\r\n\r\n"))
				buf := make([]byte, 128)
				_, _ = conn.Read(buf)
				atomic.AddUint64(&completed, 1)
			case 3:
				// Scenario D: Read honeypot banner
				_ = conn.SetDeadline(time.Now().Add(500 * time.Millisecond))
				buf := make([]byte, 256)
				n, err := conn.Read(buf)
				if err == nil && n > 0 {
					atomic.AddUint64(&completed, 1)
				} else {
					atomic.AddUint64(&droppedOrFailed, 1)
				}
			}
		}(i)
	}

	wg.Wait()
	duration := time.Since(start)

	t.Logf("Completed %d adversarial connections in %v (Rate: %.2f conn/sec)",
		totalConnections, duration, float64(totalConnections)/duration.Seconds())
	t.Logf("Completed: %d, Dropped/Failed: %d", completed, droppedOrFailed)

	// Stop daemon and verify full shutdown
	if err := daemon.Stop(); err != nil {
		t.Fatalf("Failed to stop daemon: %v", err)
	}

	// Allow goroutines to settle and run GC
	for i := 0; i < 5; i++ {
		runtime.GC()
		time.Sleep(50 * time.Millisecond)
	}

	finalGoroutines := runtime.NumGoroutine()
	t.Logf("Goroutines baseline: %d, after shutdown: %d", baselineGoroutines, finalGoroutines)

	if finalGoroutines > baselineGoroutines+3 {
		t.Fatalf("[CRITICAL GOROUTINE LEAK] Expected goroutines to return to ~%d, got %d (leaked %d goroutines)",
			baselineGoroutines, finalGoroutines, finalGoroutines-baselineGoroutines)
	}
}

// TestSecurityDaemonLifecycleMultiRestartLeak starts and stops the SecurityDaemon 30 times
// to confirm no lingering background tickers or worker routines leak across restarts.
func TestSecurityDaemonLifecycleMultiRestartLeak(t *testing.T) {
	runtime.GC()
	time.Sleep(30 * time.Millisecond)
	baselineGoroutines := runtime.NumGoroutine()

	for iteration := 0; iteration < 30; iteration++ {
		port := 18200 + iteration
		cfg := DefaultConfig()
		cfg.ListenAddr = "127.0.0.1"
		cfg.HoneypotPort = port
		cfg.FirewallDriver = "mock"
		cfg.DryRun = true

		d, err := NewSecurityDaemon(cfg)
		if err != nil {
			t.Fatalf("Iteration %d: NewSecurityDaemon failed: %v", iteration, err)
		}
		if err := d.Start(); err != nil {
			t.Fatalf("Iteration %d: Start failed: %v", iteration, err)
		}

		// Quick connection
		conn, err := net.DialTimeout("tcp", fmt.Sprintf("127.0.0.1:%d", port), 500*time.Millisecond)
		if err == nil {
			_ = conn.Close()
		}

		if err := d.Stop(); err != nil {
			t.Fatalf("Iteration %d: Stop failed: %v", iteration, err)
		}
	}

	for i := 0; i < 5; i++ {
		runtime.GC()
		time.Sleep(40 * time.Millisecond)
	}

	finalGoroutines := runtime.NumGoroutine()
	t.Logf("Multi-restart test (30 cycles) - Baseline: %d, Final: %d", baselineGoroutines, finalGoroutines)

	if finalGoroutines > baselineGoroutines+3 {
		t.Fatalf("[LIFECYCLE LEAK] Leaked goroutines across 30 daemon start/stop cycles: baseline=%d, final=%d",
			baselineGoroutines, finalGoroutines)
	}
}

// TestTokenBucketSubnetIsolationAdversarial tests that an attacker flooding from
// one /24 subnet cannot exhaust the capacity of another /24 subnet.
func TestTokenBucketSubnetIsolationAdversarial(t *testing.T) {
	limiter := NewDualTokenBucketLimiter(10, 1.0, 30, 2.0)
	defer limiter.Close()

	// Attacker subnet: 198.51.100.0/24
	attackerSubnetIPs := make([]net.IP, 50)
	for i := 0; i < 50; i++ {
		attackerSubnetIPs[i] = net.IPv4(198, 51, 100, byte(i+1))
	}

	// Victim/Legitimate subnet: 203.0.113.0/24
	victimIP := net.IPv4(203, 0, 113, 10)

	// Attacker floods with 500 requests across their /24 subnet
	attackerAllowed := 0
	attackerDropped := 0
	for round := 0; round < 10; round++ {
		for _, ip := range attackerSubnetIPs {
			if limiter.Allow(ip) {
				attackerAllowed++
			} else {
				attackerDropped++
			}
		}
	}

	t.Logf("Attacker traffic on 198.51.100.0/24: Allowed=%d, Dropped=%d", attackerAllowed, attackerDropped)
	if attackerDropped == 0 {
		t.Fatalf("Subnet rate limiter failed to drop attacker traffic")
	}

	// Victim from separate subnet MUST still be allowed full per-IP capacity (10 tokens)
	victimAllowed := 0
	for i := 0; i < 10; i++ {
		if limiter.Allow(victimIP) {
			victimAllowed++
		}
	}

	if victimAllowed != 10 {
		t.Fatalf("[SUBNET ISOLATION FAILURE] Legitimate subnet was starved by attacker in separate subnet! Allowed=%d/10", victimAllowed)
	}
}

// TestThreatScorerAdversarialDecayEdgeCases tests threat scoring under extreme float values,
// concurrent access, zero points, and boundary conditions.
func TestThreatScorerAdversarialDecayEdgeCases(t *testing.T) {
	scorer := NewThreatScorer(100, 100*time.Millisecond, 1*time.Hour)
	defer scorer.Close()

	// 1. Zero points
	ip1 := net.IPv4(192, 0, 2, 1)
	s1, ban1 := scorer.RecordThreat(ip1, 0)
	if ban1 || s1 != 0 {
		t.Errorf("Zero threat points produced unexpected score: %.2f (ban=%v)", s1, ban1)
	}

	// 2. Huge threat points
	ip2 := net.IPv4(192, 0, 2, 2)
	s2, ban2 := scorer.RecordThreat(ip2, 1e9)
	if !ban2 || s2 < 1e9 {
		t.Errorf("Huge threat points failed to trigger ban: %.2f (ban=%v)", s2, ban2)
	}

	// 3. Nil IP handling
	sNil, banNil := scorer.RecordThreat(nil, 50)
	if banNil || sNil != 0 {
		t.Errorf("Nil IP should return 0, false; got %.2f, %v", sNil, banNil)
	}

	// 4. Concurrent threat recording & decay across 1,000 goroutines
	const numGoroutines = 1000
	var wg sync.WaitGroup
	for i := 0; i < numGoroutines; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			ip := net.IPv4(192, 0, 2, byte(idx%10+10))
			scorer.RecordThreat(ip, 5.0)
			_ = scorer.GetScore(ip)
			if idx%100 == 0 {
				scorer.ResetScore(ip)
			}
		}(i)
	}
	wg.Wait()

	// 5. Exponential decay check after 300ms (3 half-lives)
	testIP := net.IPv4(192, 0, 2, 99)
	scorer.RecordThreat(testIP, 80.0)
	time.Sleep(320 * time.Millisecond)
	decayedScore := scorer.GetScore(testIP)
	// Expected: 80 * (0.5^3) = 10
	if decayedScore > 18.0 || decayedScore < 5.0 {
		t.Errorf("Expected decayed score around ~10, got %.2f", decayedScore)
	}
}

// TestWhitelistComprehensiveEdgeCases tests IPv4-mapped IPv6, CGNAT, Loopback, LinkLocal,
// DNS resolvers, and nil IPs.
func TestWhitelistComprehensiveEdgeCases(t *testing.T) {
	wm, err := NewWhitelistManager(DefaultConfig().WhitelistedCIDRs)
	if err != nil {
		t.Fatalf("Failed to create whitelist manager: %v", err)
	}

	tests := []struct {
		name        string
		ip          net.IP
		whitelisted bool
	}{
		{"Nil_IP", nil, true}, // Safe fallback
		{"IPv4_Loopback", net.ParseIP("127.0.0.1"), true},
		{"IPv4_Loopback_High", net.ParseIP("127.255.255.254"), true},
		{"IPv6_Loopback", net.ParseIP("::1"), true},
		{"RFC1918_10_Net", net.ParseIP("10.50.100.200"), true},
		{"RFC1918_172_Net", net.ParseIP("172.20.5.1"), true},
		{"RFC1918_192_Net", net.ParseIP("192.168.100.1"), true},
		{"CGNAT_Mesh_VIP", net.ParseIP("100.64.1.1"), true},
		{"CGNAT_Mesh_High", net.ParseIP("100.127.255.254"), true},
		{"LinkLocal_Metadata", net.ParseIP("169.254.169.254"), true},
		{"Cloudflare_DNS_Primary", net.ParseIP("1.1.1.1"), true},
		{"Cloudflare_DNS_Secondary", net.ParseIP("1.0.0.1"), true},
		{"Google_DNS_Primary", net.ParseIP("8.8.8.8"), true},
		{"Google_DNS_Secondary", net.ParseIP("8.8.4.4"), true},
		{"Quad9_DNS", net.ParseIP("9.9.9.9"), true},
		{"IPv4_Mapped_Loopback", net.ParseIP("::ffff:127.0.0.1"), true},
		{"IPv4_Mapped_RFC1918", net.ParseIP("::ffff:10.0.0.1"), true},
		{"IPv4_Mapped_CGNAT", net.ParseIP("::ffff:100.64.0.5"), true},
		{"Public_NonWhitelisted_1", net.ParseIP("198.51.100.42"), false},
		{"Public_NonWhitelisted_2", net.ParseIP("203.0.113.88"), false},
		{"Public_NonWhitelisted_3", net.ParseIP("45.33.32.156"), false},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			res := wm.IsWhitelisted(tc.ip)
			if res != tc.whitelisted {
				t.Errorf("IsWhitelisted(%v) = %v; expected %v", tc.ip, res, tc.whitelisted)
			}
		})
	}
}

// TestNotificationPoolWorkerDrainAndClose tests high-throughput notification dispatch
// and clean worker pool termination without deadlock.
func TestNotificationPoolWorkerDrainAndClose(t *testing.T) {
	pool := NewNotificationPool("", "", 4, 1000)

	const totalEvents = 2000
	var wg sync.WaitGroup

	for i := 0; i < totalEvents; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			pool.Dispatch(NotificationEvent{
				IP:        fmt.Sprintf("198.51.100.%d", idx%250+1),
				Reason:    "Honeypot probe test",
				Score:     105.0,
				Timestamp: time.Now(),
			})
		}(i)
	}

	wg.Wait()

	// Ensure Close() terminates cleanly without hanging
	done := make(chan struct{})
	go func() {
		pool.Close()
		close(done)
	}()

	select {
	case <-done:
		t.Log("NotificationPool closed cleanly")
	case <-time.After(2 * time.Second):
		t.Fatal("NotificationPool.Close() hung / deadlocked")
	}
}
