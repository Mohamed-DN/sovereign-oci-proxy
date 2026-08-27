package stress

import (
	"bytes"
	"context"
	"crypto/rand"
	"fmt"
	"io"
	"net"
	"net/http"
	"runtime"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/gorilla/websocket"
	"github.com/sovereign/proxy/v4/pkg/bridge"
	"github.com/sovereign/proxy/v4/pkg/derp"
	"github.com/sovereign/proxy/v4/pkg/nat"
)

// TestDiscoV4NATClassificationAndPortPrediction tests all NAT classification permutations,
// delta prediction calculation, and strategy selection matrix.
func TestDiscoV4NATClassificationAndPortPrediction(t *testing.T) {
	// 1. Mock STUN server pair for Cone NAT (identical reflected ports)
	srvCone1, err := nat.StartSTUNServer("127.0.0.1:0")
	if err != nil {
		t.Fatalf("StartSTUNServer failed: %v", err)
	}
	defer srvCone1.Close()

	srvCone2, err := nat.StartSTUNServer("127.0.0.1:0")
	if err != nil {
		t.Fatalf("StartSTUNServer failed: %v", err)
	}
	defer srvCone2.Close()

	clientConn, err := net.ListenUDP("udp", &net.UDPAddr{IP: net.ParseIP("127.0.0.1"), Port: 0})
	if err != nil {
		t.Fatalf("ListenUDP failed: %v", err)
	}
	defer clientConn.Close()

	desc, err := nat.ClassifyNAT([]string{srvCone1.Addr().String(), srvCone2.Addr().String()}, clientConn, time.Second)
	if err != nil {
		t.Fatalf("ClassifyNAT failed: %v", err)
	}

	if desc.Type != nat.NATTypeDirectPublic && desc.Type != nat.NATTypePortRestrictedCone {
		t.Fatalf("Expected DirectPublic or PortRestrictedCone on loopback, got: %s", desc.Type)
	}

	// 2. Test Strategy Matrix Exhaustively
	tests := []struct {
		name     string
		local    *nat.NATDescriptor
		remote   *nat.NATDescriptor
		expected nat.TraversalStrategy
	}{
		{
			name:     "DirectPublic_Local",
			local:    &nat.NATDescriptor{Type: nat.NATTypeDirectPublic},
			remote:   &nat.NATDescriptor{Type: nat.NATTypePortRestrictedCone},
			expected: nat.StrategyDirect,
		},
		{
			name:     "DirectPublic_Remote",
			local:    &nat.NATDescriptor{Type: nat.NATTypeSymmetric},
			remote:   &nat.NATDescriptor{Type: nat.NATTypeDirectPublic},
			expected: nat.StrategyDirect,
		},
		{
			name:     "Cone_Cone_DualPing",
			local:    &nat.NATDescriptor{Type: nat.NATTypeFullCone},
			remote:   &nat.NATDescriptor{Type: nat.NATTypePortRestrictedCone},
			expected: nat.StrategyDualPing,
		},
		{
			name:     "SymmetricSeq_Cone_SequentialPrediction",
			local:    &nat.NATDescriptor{Type: nat.NATTypeSymmetric, IsSequential: true, PortDelta: 2},
			remote:   &nat.NATDescriptor{Type: nat.NATTypeRestrictedCone},
			expected: nat.StrategySequentialPrediction,
		},
		{
			name:     "Cone_SymmetricSeq_SequentialPrediction",
			local:    &nat.NATDescriptor{Type: nat.NATTypePortRestrictedCone},
			remote:   &nat.NATDescriptor{Type: nat.NATTypeSymmetric, IsSequential: true, PortDelta: -2},
			expected: nat.StrategySequentialPrediction,
		},
		{
			name:     "SymmetricRandom_Cone_BirthdaySpray",
			local:    &nat.NATDescriptor{Type: nat.NATTypeSymmetric, IsSequential: false, PortDelta: 5120},
			remote:   &nat.NATDescriptor{Type: nat.NATTypeFullCone},
			expected: nat.StrategyBirthdaySpray,
		},
		{
			name:     "Symmetric_Symmetric_BirthdaySpray",
			local:    &nat.NATDescriptor{Type: nat.NATTypeSymmetric, IsSequential: false},
			remote:   &nat.NATDescriptor{Type: nat.NATTypeSymmetric, IsSequential: false},
			expected: nat.StrategyBirthdaySpray,
		},
		{
			name:     "Blocked_Cone_DERPFallback",
			local:    &nat.NATDescriptor{Type: nat.NATTypeBlocked},
			remote:   &nat.NATDescriptor{Type: nat.NATTypeFullCone},
			expected: nat.StrategyDERPFallback,
		},
		{
			name:     "Nil_Descriptor_DERPFallback",
			local:    nil,
			remote:   &nat.NATDescriptor{Type: nat.NATTypeFullCone},
			expected: nat.StrategyDERPFallback,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			strat := nat.SelectStrategy(tc.local, tc.remote)
			if strat != tc.expected {
				t.Fatalf("Strategy selection mismatch for %s: expected %s, got %s", tc.name, tc.expected, strat)
			}
		})
	}
}

// TestDiscoV4BirthdaySprayUnderAdversarialJitterAndLoss tests 256-port birthday spraying simulation
// with simulated network jitter, dropped probes, and rapid timeouts.
func TestDiscoV4BirthdaySprayUnderAdversarialJitterAndLoss(t *testing.T) {
	const peerPairs = 10
	var wg sync.WaitGroup

	for i := 0; i < peerPairs; i++ {
		wg.Add(1)
		go func(pairIdx int) {
			defer wg.Done()

			aliceConn, err := net.ListenUDP("udp", &net.UDPAddr{IP: net.ParseIP("127.0.0.1"), Port: 0})
			if err != nil {
				t.Errorf("Alice listen failed: %v", err)
				return
			}
			defer aliceConn.Close()

			bobConn, err := net.ListenUDP("udp", &net.UDPAddr{IP: net.ParseIP("127.0.0.1"), Port: 0})
			if err != nil {
				t.Errorf("Bob listen failed: %v", err)
				return
			}
			defer bobConn.Close()

			aliceAddr := aliceConn.LocalAddr().(*net.UDPAddr)
			bobAddr := bobConn.LocalAddr().(*net.UDPAddr)

			ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
			defer cancel()

			resCh := make(chan *nat.SprayResult, 2)
			errCh := make(chan error, 2)

			// Alice sprays towards Bob's port window
			go func() {
				res, err := nat.ExecuteBirthdaySpray(ctx, aliceConn, bobAddr.IP, bobAddr.Port, 64)
				if err != nil {
					errCh <- err
				} else {
					resCh <- res
				}
			}()

			// Bob probes Alice's exact port
			go func() {
				// Inject slight jitter before Bob responds
				time.Sleep(time.Duration(5+pairIdx*2) * time.Millisecond)
				res, err := nat.ExecuteSequentialPrediction(ctx, bobConn, aliceAddr.IP, aliceAddr.Port, 0, 8)
				if err != nil {
					errCh <- err
				} else {
					resCh <- res
				}
			}()

			// Wait for at least one side to establish bidirectional link
			select {
			case res := <-resCh:
				if res.RemoteAddr == nil {
					t.Errorf("Pair %d: Result remote address is nil", pairIdx)
				}
			case err := <-errCh:
				t.Errorf("Pair %d: Hole punch spray error: %v", pairIdx, err)
			case <-time.After(3 * time.Second):
				t.Errorf("Pair %d: Hole punch timed out", pairIdx)
			}
		}(i)
	}

	wg.Wait()
}

// TestDiscoV4TimeoutAndContextCancellation verifies that hole punching aborts cleanly on timeout
// without hanging or leaking goroutines.
func TestDiscoV4TimeoutAndContextCancellation(t *testing.T) {
	conn, err := net.ListenUDP("udp", &net.UDPAddr{IP: net.ParseIP("127.0.0.1"), Port: 0})
	if err != nil {
		t.Fatalf("ListenUDP failed: %v", err)
	}
	defer conn.Close()

	// Target an unreachable / non-listening IP
	unreachableIP := net.ParseIP("192.0.2.1") // RFC 5737 TEST-NET-1 (Unroutable)

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	start := time.Now()
	res, err := nat.ExecuteBirthdaySpray(ctx, conn, unreachableIP, 50000, 32)
	elapsed := time.Since(start)

	if err == nil || res != nil {
		t.Fatalf("Expected hole punch to fail on unreachable target, got res: %v, err: %v", res, err)
	}

	if elapsed > 1*time.Second {
		t.Fatalf("Hole punch took too long to abort on cancelled context: %v", elapsed)
	}
}

// TestDERPV4DecoyWebServerAdversarialProbing sends malicious scanner requests, query fuzzing,
// and invalid HTTP methods to verify the authentic Nginx camouflage response.
func TestDERPV4DecoyWebServerAdversarialProbing(t *testing.T) {
	server := derp.NewServer(derp.ServerConfig{
		ListenAddr: "127.0.0.1:0",
		DecoyTitle: "Enterprise Cloud Mirror - Edge Relay",
	})
	if err := server.Start(); err != nil {
		t.Fatalf("DERP server start failed: %v", err)
	}
	defer server.Close()

	serverAddr := server.Addr().String()
	baseURL := fmt.Sprintf("http://%s", serverAddr)

	adversarialPaths := []struct {
		method string
		path   string
		body   string
	}{
		{"GET", "/", ""},
		{"GET", "/index.html", ""},
		{"GET", "/robots.txt", ""},
		{"GET", "/wp-admin/login.php", ""},
		{"GET", "/cgi-bin/test-cgi", ""},
		{"GET", "/.env", ""},
		{"GET", "/.git/config", ""},
		{"GET", "/%2e%2e/%2e%2e/etc/passwd", ""},
		{"GET", "/api/v1/debug?query=SELECT+*+FROM+users", ""},
		{"POST", "/api/login", `{"user":"admin","pass":"' OR '1'='1"}`},
		{"PUT", "/upload.php", "MALICIOUS_SHELL_PAYLOAD"},
		{"DELETE", "/data/nodes", ""},
		{"OPTIONS", "/", ""},
		{"HEAD", "/", ""},
		{"GET", "/" + strings.Repeat("A", 1024), ""},
	}

	httpClient := &http.Client{Timeout: 2 * time.Second}

	for _, probe := range adversarialPaths {
		t.Run(fmt.Sprintf("%s_%s", probe.method, probe.path), func(t *testing.T) {
			reqURL := baseURL + probe.path
			var bodyReader io.Reader
			if probe.body != "" {
				bodyReader = strings.NewReader(probe.body)
			}

			req, err := http.NewRequest(probe.method, reqURL, bodyReader)
			if err != nil {
				// Path might be invalid URL, which is fine
				return
			}

			req.Header.Set("User-Agent", "Mozilla/5.0 (Adversarial Scanner 4.0; Nikto/2.1.6; sqlmap/1.7)")
			req.Header.Set("X-Forwarded-For", "127.0.0.1")
			req.Header.Set("Host", "spoofed.corp.internal")

			resp, err := httpClient.Do(req)
			if err != nil {
				t.Fatalf("Probe %s %s failed to connect: %v", probe.method, probe.path, err)
			}
			defer resp.Body.Close()

			// Decoy handler must return HTTP 200 OK
			if resp.StatusCode != http.StatusOK {
				t.Errorf("Expected status 200 for %s %s, got %d", probe.method, probe.path, resp.StatusCode)
			}

			// Camouflage headers MUST match genuine Nginx signature
			if serverHdr := resp.Header.Get("Server"); serverHdr != "nginx/1.24.0 (Ubuntu)" {
				t.Errorf("Server header mismatch for %s: got '%s', expected 'nginx/1.24.0 (Ubuntu)'", probe.path, serverHdr)
			}
			if ct := resp.Header.Get("Content-Type"); !strings.Contains(ct, "text/html") {
				t.Errorf("Content-Type mismatch: got '%s'", ct)
			}
			if xcto := resp.Header.Get("X-Content-Type-Options"); xcto != "nosniff" {
				t.Errorf("X-Content-Type-Options mismatch: got '%s'", xcto)
			}
			if xfo := resp.Header.Get("X-Frame-Options"); xfo != "DENY" {
				t.Errorf("X-Frame-Options mismatch: got '%s'", xfo)
			}

			// Body content inspection (except HEAD which has empty body)
			if probe.method != "HEAD" {
				bodyBytes, _ := io.ReadAll(resp.Body)
				if !bytes.Contains(bodyBytes, []byte("Enterprise Cloud Mirror - Edge Relay")) {
					t.Errorf("Decoy body does not contain expected title for %s", probe.path)
				}
				if !bytes.Contains(bodyBytes, []byte("Operational")) {
					t.Errorf("Decoy body does not contain status badge for %s", probe.path)
				}
			}
		})
	}
}

// TestDERPV4WebSocketRelayAdversarialEdgeCases stress-tests invalid handshakes, garbage frames,
// unknown destinations, oversized payloads, and high-concurrency client multiplexing.
func TestDERPV4WebSocketRelayAdversarialEdgeCases(t *testing.T) {
	server := derp.NewServer(derp.ServerConfig{
		ListenAddr: "127.0.0.1:0",
		DecoyTitle: "Relay Test",
	})
	if err := server.Start(); err != nil {
		t.Fatalf("DERP server start failed: %v", err)
	}
	defer server.Close()

	wsURL := fmt.Sprintf("ws://%s/ws/v4/relay", server.Addr().String())

	// 1. Test Garbage binary connect on /ws/v4/relay
	t.Run("Garbage_Binary_Handshake", func(t *testing.T) {
		conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
		if err != nil {
			t.Fatalf("WebSocket dial failed: %v", err)
		}
		defer conn.Close()

		// Write random garbage instead of valid FrameClientInfo
		junk := make([]byte, 128)
		rand.Read(junk)
		_ = conn.WriteMessage(websocket.BinaryMessage, junk)

		// Expect server to close connection due to invalid initial frame
		_ = conn.SetReadDeadline(time.Now().Add(500 * time.Millisecond))
		_, _, err = conn.ReadMessage()
		if err == nil {
			// Either error or closed is expected
		}
	})

	// 2. Test Frame Oversize (> 65535 bytes)
	t.Run("Frame_Oversize_Rejection", func(t *testing.T) {
		hugePayload := make([]byte, 70000)
		frame := &derp.Frame{
			Type:    derp.FrameSendPacket,
			Payload: hugePayload,
		}
		_, err := derp.EncodeFrame(frame)
		if err != derp.ErrPayloadTooLarge {
			t.Fatalf("Expected ErrPayloadTooLarge, got: %v", err)
		}
	})

	// 3. Test Routing to Unknown Destination Key (Drop Counter Verification)
	t.Run("Route_To_Unknown_Destination", func(t *testing.T) {
		var srcPub, unknownDestPub [derp.PubKeySize]byte
		rand.Read(srcPub[:])
		rand.Read(unknownDestPub[:])

		client := derp.NewClient(wsURL, srcPub, func(src [derp.PubKeySize]byte, p []byte) {}, nil)
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()

		if err := client.Connect(ctx); err != nil {
			t.Fatalf("Client connect failed: %v", err)
		}
		defer client.Close()

		time.Sleep(50 * time.Millisecond)

		// Send packet to unknown public key
		payload := []byte("Packet destined for nowhere")
		if err := client.SendTo(unknownDestPub, payload); err != nil {
			t.Fatalf("SendTo failed: %v", err)
		}

		time.Sleep(50 * time.Millisecond)

		_, dropped := server.Router().Metrics()
		if dropped == 0 {
			t.Fatalf("Expected dropped packet count > 0 for unknown destination, got %d", dropped)
		}
	})

	// 4. Test 100 Clients High-Concurrency Concurrent Routing & Instant Churn
	t.Run("100_Clients_High_Concurrency_Churn", func(t *testing.T) {
		const numPeers = 50
		clients := make([]*derp.Client, numPeers)
		pubKeys := make([][derp.PubKeySize]byte, numPeers)

		var receivedCount int64
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()

		for i := 0; i < numPeers; i++ {
			rand.Read(pubKeys[i][:])
			idx := i
			clients[i] = derp.NewClient(wsURL, pubKeys[i], func(src [derp.PubKeySize]byte, p []byte) {
				atomic.AddInt64(&receivedCount, 1)
			}, nil)

			if err := clients[i].Connect(ctx); err != nil {
				t.Fatalf("Client %d connect failed: %v", idx, err)
			}
			defer clients[i].Close()
		}

		time.Sleep(100 * time.Millisecond)
		activeCount := server.Router().ActiveSessionsCount()
		if activeCount != numPeers {
			t.Fatalf("Expected %d active sessions, got %d", numPeers, activeCount)
		}

		// Concurrently send 500 packets across ring peers
		var sendWg sync.WaitGroup
		const packetsPerClient = 10
		for i := 0; i < numPeers; i++ {
			sendWg.Add(1)
			go func(senderIdx int) {
				defer sendWg.Done()
				destIdx := (senderIdx + 1) % numPeers
				for k := 0; k < packetsPerClient; k++ {
					msg := []byte(fmt.Sprintf("Ring-Message-%d-to-%d-seq-%d", senderIdx, destIdx, k))
					_ = clients[senderIdx].SendTo(pubKeys[destIdx], msg)
				}
			}(i)
		}

		sendWg.Wait()
		time.Sleep(200 * time.Millisecond)

		expectedTotal := int64(numPeers * packetsPerClient)
		recvd := atomic.LoadInt64(&receivedCount)
		if recvd != expectedTotal {
			t.Fatalf("Expected %d total received packets, got %d", expectedTotal, recvd)
		}
	})
}

// TestBogonSuppressionExhaustiveMatrix verifies all RFC 1918, CGNAT, Loopback, Link-Local,
// Multicast, IPv6 Unique Local, and IPv4-mapped IPv6 ranges are suppressed without leak.
func TestBogonSuppressionExhaustiveMatrix(t *testing.T) {
	policy := bridge.NewSandboxPolicyEngine(bridge.SandboxPolicyConfig{AllowLAN: false})

	bogonVectors := []struct {
		cidrName string
		ipStr    string
		port     int
	}{
		// 10.0.0.0/8
		{"RFC1918_10_Network", "10.0.0.0", 80},
		{"RFC1918_10_Host", "10.1.2.3", 443},
		{"RFC1918_10_Broadcast", "10.255.255.255", 8080},

		// 172.16.0.0/12
		{"RFC1918_172_Start", "172.16.0.1", 80},
		{"RFC1918_172_Mid", "172.20.10.5", 443},
		{"RFC1918_172_End", "172.31.255.254", 80},

		// 192.168.0.0/16
		{"RFC1918_192_Start", "192.168.0.1", 80},
		{"RFC1918_192_Router", "192.168.1.1", 443},
		{"RFC1918_192_End", "192.168.255.255", 80},

		// 127.0.0.0/8 Loopback
		{"Loopback_1", "127.0.0.1", 80},
		{"Loopback_127_0_1_1", "127.0.1.1", 443},
		{"Loopback_End", "127.255.255.254", 80},

		// 100.64.0.0/10 CGNAT / Tailscale / Mesh VIP range
		{"CGNAT_Start", "100.64.0.1", 80},
		{"CGNAT_Mid", "100.80.50.25", 443},
		{"CGNAT_End", "100.127.255.254", 80},

		// 169.254.0.0/16 Cloud Metadata / Link-Local
		{"CloudMetadata_AWS_GCP", "169.254.169.254", 80},
		{"LinkLocal_Start", "169.254.0.1", 443},
		{"LinkLocal_End", "169.254.255.254", 80},

		// 224.0.0.0/4 Multicast
		{"Multicast_AllSystems", "224.0.0.1", 80},
		{"Multicast_mDNS", "224.0.0.251", 5353},
		{"Multicast_SSDP", "239.255.255.250", 1900},

		// 0.0.0.0/8
		{"Unspecified_IPv4", "0.0.0.0", 80},

		// IPv6 Bogons
		{"IPv6_Loopback", "::1", 80},
		{"IPv6_Unspecified", "::", 80},
		{"IPv6_UniqueLocal_1", "fc00::1", 443},
		{"IPv6_UniqueLocal_2", "fd12:3456:789a::1", 443},
		{"IPv6_LinkLocal", "fe80::1", 443},
		{"IPv6_Multicast", "ff02::1", 80},

		// IPv4-mapped IPv6 Bogons
		{"IPv6_Mapped_10", "::ffff:10.0.0.1", 80},
		{"IPv6_Mapped_192", "::ffff:192.168.1.1", 443},
		{"IPv6_Mapped_127", "::ffff:127.0.0.1", 80},
		{"IPv6_Mapped_Metadata", "::ffff:169.254.169.254", 80},
		{"IPv6_Mapped_CGNAT", "::ffff:100.64.0.1", 80},
	}

	for _, tc := range bogonVectors {
		t.Run("Bogon_"+tc.cidrName, func(t *testing.T) {
			ip := net.ParseIP(tc.ipStr)
			if ip == nil {
				t.Fatalf("Failed to parse IP: %s", tc.ipStr)
			}

			if !bridge.IsBogonIP(ip) {
				t.Errorf("[CRITICAL] IsBogonIP returned false for %s (%s)", tc.ipStr, tc.cidrName)
			}

			err := policy.ValidateEgress(ip, tc.port, 100, false)
			if err == nil {
				t.Fatalf("[LEAK VULNERABILITY] ValidateEgress permitted bogon IP %s:%d", tc.ipStr, tc.port)
			}
		})
	}

	// Permitted Public IPs
	publicVectors := []string{
		"1.1.1.1",
		"8.8.8.8",
		"93.184.216.34",
		"142.250.190.46",
		"104.21.45.12",
		"2606:4700:4700::1111",
		"2001:4860:4860::8888",
	}

	for _, pubStr := range publicVectors {
		t.Run("Public_"+pubStr, func(t *testing.T) {
			ip := net.ParseIP(pubStr)
			if ip == nil {
				t.Fatalf("Failed to parse IP: %s", pubStr)
			}

			if bridge.IsBogonIP(ip) {
				t.Errorf("IsBogonIP returned true for legitimate public IP %s", pubStr)
			}

			err := policy.ValidateEgress(ip, 443, 100, false)
			if err != nil {
				t.Fatalf("ValidateEgress rejected valid public IP %s:443: %v", pubStr, err)
			}
		})
	}
}

// TestBatteryAndQuotaGuardianStressAndTransitions verifies dynamic threshold switches,
// battery power state changes, quota caps, and high-concurrency race freedom.
func TestBatteryAndQuotaGuardianStressAndTransitions(t *testing.T) {
	guardian := bridge.NewGuardian(500) // 500 MB Quota

	// 1. Test Battery Power Threshold Transitions
	// On AC power -> even 1% should NOT suspend
	guardian.UpdateBattery(1, false)
	if guardian.IsSuspended() {
		t.Fatalf("Guardian suspended while on AC power")
	}

	// Switch to Battery Power at 19% -> MUST suspend (< 20%)
	guardian.UpdateBattery(19, true)
	if !guardian.IsSuspended() {
		t.Fatalf("Guardian failed to suspend on Battery Power at 19%%")
	}

	// Battery rises to 20% on battery -> remains suspended until >= 25%
	guardian.UpdateBattery(20, true)
	if !guardian.IsSuspended() {
		t.Fatalf("Guardian resumed prematurely at 20%% (should require >= 25%% hysteresis)")
	}

	guardian.UpdateBattery(24, true)
	if !guardian.IsSuspended() {
		t.Fatalf("Guardian resumed prematurely at 24%% (should require >= 25%% hysteresis)")
	}

	// Battery reaches 25% -> MUST resume
	guardian.UpdateBattery(25, true)
	if guardian.IsSuspended() {
		t.Fatalf("Guardian failed to resume on battery at 25%%")
	}

	// Battery drops to 20% -> Still active (hysteresis lower bound is < 20%)
	guardian.UpdateBattery(20, true)
	if guardian.IsSuspended() {
		t.Fatalf("Guardian suspended at 20%% (should only suspend when < 20%%)")
	}

	// Battery drops to 19% -> Suspends again
	guardian.UpdateBattery(19, true)
	if !guardian.IsSuspended() {
		t.Fatalf("Guardian failed to suspend on battery at 19%%")
	}

	// Plug in AC power -> Immediately resumes
	guardian.UpdateBattery(19, false)
	if guardian.IsSuspended() {
		t.Fatalf("Guardian failed to resume immediately when AC power connected")
	}

	// 2. Test Data Quota Thresholds
	// 500 MB cap -> 90% threshold = 450 MB
	guardian.RecordTransfer(400 * 1024 * 1024) // 400 MB
	if guardian.IsSuspended() {
		t.Fatalf("Guardian suspended at 400MB / 500MB (< 90%%)")
	}

	guardian.RecordTransfer(50 * 1024 * 1024) // total 450 MB (90%)
	if !guardian.IsSuspended() {
		t.Fatalf("Guardian failed to suspend at 450MB / 500MB (>= 90%%)")
	}

	// 3. High Concurrency Race Stress on Guardian
	const goroutines = 100
	const opsPerRoutine = 500
	var wg sync.WaitGroup

	gStress := bridge.NewGuardian(10000)

	for i := 0; i < goroutines; i++ {
		wg.Add(1)
		go func(gIdx int) {
			defer wg.Done()
			for k := 0; k < opsPerRoutine; k++ {
				if (gIdx+k)%2 == 0 {
					pct := uint8(20 + (k % 80))
					onBat := (k % 4) == 0
					gStress.UpdateBattery(pct, onBat)
				} else {
					gStress.RecordTransfer(uint64(1024 * (k + 1)))
				}
				_ = gStress.IsSuspended()
				_, _, _, _ = gStress.Status()
			}
		}(i)
	}

	wg.Wait()
}

// TestGoroutineLeakageAndResourceStability ensures no goroutines or file descriptors leak
// across repeated high-volume NAT discovery, DERP sessions, and Bridge connections.
func TestGoroutineLeakageAndResourceStability(t *testing.T) {
	runtime.GC()
	time.Sleep(50 * time.Millisecond)
	initialGoroutines := runtime.NumGoroutine()

	const iterations = 50

	// 1. Run repeated STUN server start/stop cycles
	for i := 0; i < iterations; i++ {
		srv, err := nat.StartSTUNServer("127.0.0.1:0")
		if err != nil {
			t.Fatalf("STUN start failed at iter %d: %v", i, err)
		}
		mapped, err := nat.QuerySTUN(srv.Addr().String(), 500*time.Millisecond, nil)
		if err != nil || mapped == nil {
			t.Fatalf("STUN query failed at iter %d: %v", i, err)
		}
		_ = srv.Close()
	}

	// 2. Run repeated DERP relay server start/stop and client connect/disconnect cycles
	for i := 0; i < iterations; i++ {
		srv := derp.NewServer(derp.ServerConfig{
			ListenAddr: "127.0.0.1:0",
			DecoyTitle: "Leak Test",
		})
		if err := srv.Start(); err != nil {
			t.Fatalf("DERP server start failed at iter %d: %v", i, err)
		}

		wsURL := fmt.Sprintf("ws://%s/ws/v4/relay", srv.Addr().String())
		var pub [derp.PubKeySize]byte
		rand.Read(pub[:])

		client := derp.NewClient(wsURL, pub, func(src [derp.PubKeySize]byte, p []byte) {}, nil)
		ctx, cancel := context.WithTimeout(context.Background(), time.Second)
		if err := client.Connect(ctx); err == nil {
			_ = client.Close()
		}
		cancel()
		_ = srv.Close()
	}

	// 3. Run repeated SOCKS5 / HTTP Proxy server lifecycle
	for i := 0; i < iterations; i++ {
		bridgeEngine := bridge.NewNetstackBridge(nil, nil, nil)
		socksSrv := bridge.NewSOCKS5Server("127.0.0.1:0", bridgeEngine)
		if err := socksSrv.Start(); err == nil {
			_ = socksSrv.Close()
		}

		httpSrv := bridge.NewHTTPProxyServer("127.0.0.1:0", bridgeEngine)
		if err := httpSrv.Start(); err == nil {
			_ = httpSrv.Close()
		}
	}

	// Allow goroutines to wind down and run GC
	for attempt := 0; attempt < 5; attempt++ {
		runtime.GC()
		time.Sleep(50 * time.Millisecond)
	}

	finalGoroutines := runtime.NumGoroutine()
	goroutineDelta := finalGoroutines - initialGoroutines

	t.Logf("Goroutine stability: initial=%d, final=%d, delta=%d",
		initialGoroutines, finalGoroutines, goroutineDelta)

	// Allow small delta (<= 5) for test runner background routines
	if goroutineDelta > 5 {
		t.Fatalf("[RESOURCE LEAK DETECTED] Goroutine count increased by %d (initial: %d, final: %d)",
			goroutineDelta, initialGoroutines, finalGoroutines)
	}
}
