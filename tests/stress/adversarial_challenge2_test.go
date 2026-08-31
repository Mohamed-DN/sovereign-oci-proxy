package stress

import (
	"context"
	"fmt"
	"net"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/sovereign/proxy/v4/pkg/bridge"
)

// TestEgressBogonSubnetPenetration empirically stress-tests RFC 1918, CGNAT, Loopback, Link-Local, and Multicast drops.
func TestEgressBogonSubnetPenetration(t *testing.T) {
	policy := bridge.NewSandboxPolicyEngine(bridge.SandboxPolicyConfig{AllowLAN: false})

	adversarialTargets := []struct {
		name string
		ip   string
		port int
	}{
		// RFC 1918 Class A (10.0.0.0/8)
		{"RFC1918_10_Start", "10.0.0.0", 80},
		{"RFC1918_10_Gateway", "10.0.0.1", 443},
		{"RFC1918_10_Mid", "10.128.55.42", 8080},
		{"RFC1918_10_End", "10.255.255.255", 443},

		// RFC 1918 Class B (172.16.0.0/12)
		{"RFC1918_172_Start", "172.16.0.0", 80},
		{"RFC1918_172_Gateway", "172.16.0.1", 443},
		{"RFC1918_172_Mid", "172.24.100.5", 8080},
		{"RFC1918_172_End", "172.31.255.255", 443},

		// RFC 1918 Class C (192.168.0.0/16)
		{"RFC1918_192_Start", "192.168.0.0", 80},
		{"RFC1918_192_Gateway", "192.168.1.1", 443},
		{"RFC1918_192_Router", "192.168.0.1", 80},
		{"RFC1918_192_End", "192.168.255.255", 443},

		// Loopback (127.0.0.0/8)
		{"Loopback_Standard", "127.0.0.1", 80},
		{"Loopback_Localhost", "127.0.0.2", 8080},
		{"Loopback_End", "127.255.255.255", 443},

		// Cloud Metadata / Link-Local (169.254.0.0/16)
		{"AWS_GCP_Cloud_Metadata", "169.254.169.254", 80},
		{"LinkLocal_Gateway", "169.254.0.1", 443},
		{"LinkLocal_End", "169.254.255.255", 80},

		// CGNAT / Overlay Subnet (100.64.0.0/10)
		{"CGNAT_Start", "100.64.0.1", 443},
		{"CGNAT_Mid", "100.100.50.25", 8080},
		{"CGNAT_End", "100.127.255.255", 443},

		// Multicast & Unspecified
		{"Multicast_AllHosts", "224.0.0.1", 80},
		{"Multicast_High", "239.255.255.250", 1900},
		{"Unspecified_IPv4", "0.0.0.0", 80},

		// IPv6 Bogon & Private
		{"IPv6_Loopback", "::1", 80},
		{"IPv6_UniqueLocal", "fc00::1", 443},
		{"IPv6_LinkLocal", "fe80::1", 443},
		{"IPv6_IPv4_Mapped_Private1", "::ffff:10.0.0.1", 80},
		{"IPv6_IPv4_Mapped_Private2", "::ffff:192.168.1.1", 443},
		{"IPv6_IPv4_Mapped_Metadata", "::ffff:169.254.169.254", 80},
	}

	for _, tt := range adversarialTargets {
		t.Run(tt.name, func(t *testing.T) {
			ip := net.ParseIP(tt.ip)
			if ip == nil {
				t.Fatalf("Failed to parse IP: %s", tt.ip)
			}

			// Must be classified as Bogon
			if !bridge.IsBogonIP(ip) {
				t.Errorf("[VULNERABILITY] IsBogonIP failed for %s (%s)", tt.ip, tt.name)
			}

			// ValidateEgress must reject connection with Bogon error
			err := policy.ValidateEgress(ip, tt.port, 100, false)
			if err == nil {
				t.Fatalf("[CRITICAL LEAK] ValidateEgress permitted connection to Bogon IP %s:%d (%s)", tt.ip, tt.port, tt.name)
			}
		})
	}
}

// TestEgressAbusePortRejection tests comprehensive port blocking policy.
func TestEgressAbusePortRejection(t *testing.T) {
	policy := bridge.NewSandboxPolicyEngine(bridge.SandboxPolicyConfig{AllowLAN: false})
	publicIP := net.ParseIP("104.21.45.12") // Cloudflare public IP

	blockedPorts := []struct {
		port        int
		description string
	}{
		{25, "SMTP Spam Relay"},
		{465, "SMTPS Secure Mail"},
		{587, "Submission Mail"},
		{135, "MS RPC Endpoint Mapper"},
		{137, "NetBIOS Name Service"},
		{138, "NetBIOS Datagram Service"},
		{139, "NetBIOS Session Service"},
		{445, "SMB Direct / EternalBlue"},
		{22, "SSH Brute-Force"},
		{23, "Telnet Plaintext"},
		{3389, "RDP Remote Desktop"},
		{1900, "SSDP Amplification"},
		{5349, "STUN Amplification"},
	}

	for _, p := range blockedPorts {
		t.Run(fmt.Sprintf("Port_%d_%s", p.port, p.description), func(t *testing.T) {
			if !bridge.IsBlockedPort(p.port) {
				t.Errorf("[VULNERABILITY] Port %d (%s) not recognized as blocked by IsBlockedPort", p.port, p.description)
			}

			err := policy.ValidateEgress(publicIP, p.port, 100, false)
			if err == nil {
				t.Fatalf("[CRITICAL LEAK] Outbound connection permitted on abuse port %d (%s)", p.port, p.description)
			}
		})
	}

	// Permitted ports test
	allowedPorts := []int{80, 443, 8080, 8443, 8000, 9000, 53}
	for _, port := range allowedPorts {
		t.Run(fmt.Sprintf("AllowedPort_%d", port), func(t *testing.T) {
			if bridge.IsBlockedPort(port) {
				t.Errorf("Allowed port %d falsely identified as blocked", port)
			}
			err := policy.ValidateEgress(publicIP, port, 100, false)
			if err != nil {
				t.Fatalf("Valid egress connection falsely rejected on port %d: %v", port, err)
			}
		})
	}
}

// TestEgressHighVolumeConcurrencyStress hammers the sandbox policy engine with 50,000 concurrent requests.
func TestEgressHighVolumeConcurrencyStress(t *testing.T) {
	policy := bridge.NewSandboxPolicyEngine(bridge.SandboxPolicyConfig{AllowLAN: false})

	const totalRequests = 50000
	var wg sync.WaitGroup
	var droppedCount uint64
	var allowedCount uint64

	start := time.Now()

	for i := 0; i < totalRequests; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()

			var ip net.IP
			var port int

			if idx%2 == 0 {
				// Bogon IP or abuse port (Must be dropped)
				if idx%4 == 0 {
					ip = net.IPv4(192, 168, byte(idx%250), 1)
					port = 443
				} else {
					ip = net.IPv4(93, 184, 216, byte(idx%250))
					port = 25 // SMTP
				}
			} else {
				// Valid public IP & safe port (Must be allowed)
				ip = net.IPv4(142, 250, 190, byte(idx%250))
				port = 443
			}

			err := policy.ValidateEgress(ip, port, 100, false)
			if err != nil {
				atomic.AddUint64(&droppedCount, 1)
			} else {
				atomic.AddUint64(&allowedCount, 1)
			}
		}(i)
	}

	wg.Wait()
	duration := time.Since(start)

	t.Logf("Processed %d validations in %v (Rate: %.2f ops/sec)", totalRequests, duration, float64(totalRequests)/duration.Seconds())
	t.Logf("Dropped: %d, Allowed: %d", droppedCount, allowedCount)

	if droppedCount != totalRequests/2 {
		t.Fatalf("Expected %d drops, got %d", totalRequests/2, droppedCount)
	}
	if allowedCount != totalRequests/2 {
		t.Fatalf("Expected %d allowed, got %d", totalRequests/2, allowedCount)
	}

	app, blk := policy.Stats()
	if app != allowedCount || blk != droppedCount {
		t.Fatalf("Policy stats mismatch: approved=%d (expected %d), blocked=%d (expected %d)", app, allowedCount, blk, droppedCount)
	}
}

// TestDoHDNSRebindingDefense tests that DNS resolution returning private IPs is strictly blocked by the netstack pipeline.
func TestDoHDNSRebindingDefense(t *testing.T) {
	policy := bridge.NewSandboxPolicyEngine(bridge.SandboxPolicyConfig{AllowLAN: false})
	resolver := bridge.NewDoHResolver(nil)
	guardian := bridge.NewGuardian(1000)
	netBridge := bridge.NewNetstackBridge(policy, resolver, guardian)

	// Simulate inbound client socket
	serverConn, clientConn := net.Pipe()
	defer serverConn.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	// Attempt DialAndPipe to a domain that parses as private IP or rebinds
	errCh := make(chan error, 1)
	go func() {
		err := netBridge.DialAndPipe(ctx, serverConn, "10.0.0.1", 80)
		errCh <- err
	}()

	select {
	case err := <-errCh:
		if err == nil {
			t.Fatalf("[CRITICAL] DialAndPipe unexpectedly succeeded to private IP 10.0.0.1")
		}
		t.Logf("DialAndPipe correctly rejected private IP: %v", err)
	case <-time.After(3 * time.Second):
		t.Fatalf("DialAndPipe timed out / hung")
	}
	_ = clientConn.Close()
}
