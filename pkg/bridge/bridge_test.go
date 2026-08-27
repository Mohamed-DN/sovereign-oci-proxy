package bridge

import (
	"bufio"
	"fmt"
	"io"
	"net"
	"strings"
	"testing"
)

func TestBogonAndPortIsolation(t *testing.T) {
	policy := NewSandboxPolicyEngine(SandboxPolicyConfig{AllowLAN: false})

	// Test Bogon IP rejections
	bogonIPs := []string{
		"10.0.0.1",
		"10.254.1.1",
		"172.16.0.5",
		"172.31.255.255",
		"192.168.1.1",
		"127.0.0.1",
		"169.254.169.254",
		"100.64.0.1",
		"224.0.0.1",
		"fc00::1",
		"fe80::1",
	}

	for _, ipStr := range bogonIPs {
		ip := net.ParseIP(ipStr)
		if !IsBogonIP(ip) {
			t.Fatalf("Expected IsBogonIP to be true for %s", ipStr)
		}

		err := policy.ValidateEgress(ip, 443, 100, false)
		if err == nil {
			t.Fatalf("Expected ValidateEgress to fail for Bogon IP %s", ipStr)
		}
	}

	// Test Public IP acceptance
	publicIP := net.ParseIP("93.184.216.34") // example.com
	if IsBogonIP(publicIP) {
		t.Fatalf("Public IP should not be Bogon: %s", publicIP.String())
	}

	if err := policy.ValidateEgress(publicIP, 443, 100, false); err != nil {
		t.Fatalf("Expected ValidateEgress to pass for public IP 443, got: %v", err)
	}

	// Test Blocked Ports
	blockedList := []int{25, 465, 587, 135, 137, 138, 139, 445, 22, 23, 3389, 1900}
	for _, port := range blockedList {
		if !IsBlockedPort(port) {
			t.Fatalf("Expected IsBlockedPort to be true for port %d", port)
		}

		err := policy.ValidateEgress(publicIP, port, 100, false)
		if err == nil {
			t.Fatalf("Expected ValidateEgress to fail for blocked port %d", port)
		}
	}
}

func TestGuardianBatteryAndQuota(t *testing.T) {
	guardian := NewGuardian(100) // 100 MB quota

	// Initial on AC power
	guardian.UpdateBattery(15, false)
	if guardian.IsSuspended() {
		t.Fatalf("Should not suspend on AC power even if battery is 15 percent")
	}

	// On Battery Power with low battery
	guardian.UpdateBattery(19, true)
	if !guardian.IsSuspended() {
		t.Fatalf("Should suspend when on battery power with < 20 percent")
	}

	// Recovered on battery
	guardian.UpdateBattery(50, true)
	if guardian.IsSuspended() {
		t.Fatalf("Should resume when battery >= 25 percent")
	}

	// Quota exhaustion (90% of 100MB = 90MB)
	guardian.RecordTransfer(95 * 1024 * 1024)
	if !guardian.IsSuspended() {
		t.Fatalf("Should suspend when data quota exceeds 90 percent")
	}
}

func TestUserIntentParsing(t *testing.T) {
	intent1 := ParseUserIntent("user-country-us")
	if intent1.Mode != "COUNTRY" || intent1.TargetParam != "US" {
		t.Fatalf("Expected COUNTRY US, got %+v", intent1)
	}

	intent2 := ParseUserIntent("user-host-pk_abc123")
	if intent2.Mode != "HOST" || intent2.TargetParam != "pk_abc123" {
		t.Fatalf("Expected HOST pk_abc123, got %+v", intent2)
	}

	intent3 := ParseUserIntent("user-onion-3hop")
	if intent3.Mode != "ONION" {
		t.Fatalf("Expected ONION, got %+v", intent3)
	}
}

func TestSOCKS5AndHTTPProxyServers(t *testing.T) {
	// Create mock echo backend on loopback for testing
	echoLn, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("Echo listen failed: %v", err)
	}
	defer echoLn.Close()

	go func() {
		for {
			c, err := echoLn.Accept()
			if err != nil {
				return
			}
			go func(conn net.Conn) {
				defer conn.Close()
				_, _ = io.Copy(conn, conn)
			}(c)
		}
	}()

	echoTCPPort := echoLn.Addr().(*net.TCPAddr).Port

	// Setup netstack bridge with allowLAN=true specifically for unit test localhost verification
	policy := NewSandboxPolicyEngine(SandboxPolicyConfig{AllowLAN: true})
	bridge := NewNetstackBridge(policy, nil, nil)

	// Start SOCKS5 Server
	socksServer := NewSOCKS5Server("127.0.0.1:0", bridge)
	if err := socksServer.Start(); err != nil {
		t.Fatalf("SOCKS5 start failed: %v", err)
	}
	defer socksServer.Close()

	// Start HTTP Proxy Server
	httpServer := NewHTTPProxyServer("127.0.0.1:0", bridge)
	if err := httpServer.Start(); err != nil {
		t.Fatalf("HTTP proxy start failed: %v", err)
	}
	defer httpServer.Close()

	// 1. Verify SOCKS5 Client Connection
	socksConn, err := net.Dial("tcp", socksServer.Addr().String())
	if err != nil {
		t.Fatalf("Dial SOCKS5 failed: %v", err)
	}
	defer socksConn.Close()

	// SOCKS5 Handshake with NoAuth
	_, _ = socksConn.Write([]byte{0x05, 0x01, 0x00})
	var authResp [2]byte
	_, _ = io.ReadFull(socksConn, authResp[:])
	if authResp[0] != 0x05 || authResp[1] != 0x00 {
		t.Fatalf("SOCKS5 auth negotiation failed: %v", authResp)
	}

	// SOCKS5 Connect to Echo Server
	req := []byte{
		0x05, 0x01, 0x00, 0x01, // IPv4
		127, 0, 0, 1,
		byte(echoTCPPort >> 8), byte(echoTCPPort),
	}
	_, _ = socksConn.Write(req)
	var connResp [10]byte
	_, _ = io.ReadFull(socksConn, connResp[:])
	if connResp[1] != 0x00 {
		t.Fatalf("SOCKS5 connect failed with code %d", connResp[1])
	}

	// Send echo payload over SOCKS5
	testMsg := "Hello from SOCKS5 Tunnel!"
	_, _ = socksConn.Write([]byte(testMsg))
	buf := make([]byte, len(testMsg))
	_, _ = io.ReadFull(socksConn, buf)
	if string(buf) != testMsg {
		t.Fatalf("Echo mismatch via SOCKS5: got %s, expected %s", string(buf), testMsg)
	}

	// 2. Verify HTTP CONNECT Client Connection
	httpConn, err := net.Dial("tcp", httpServer.Addr().String())
	if err != nil {
		t.Fatalf("Dial HTTP proxy failed: %v", err)
	}
	defer httpConn.Close()

	connectReq := fmt.Sprintf("CONNECT 127.0.0.1:%d HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n\r\n", echoTCPPort, echoTCPPort)
	_, _ = httpConn.Write([]byte(connectReq))

	reader := bufio.NewReader(httpConn)
	statusLine, err := reader.ReadString('\n')
	if err != nil || !strings.Contains(statusLine, "200") {
		t.Fatalf("HTTP CONNECT failed: %s, err: %v", statusLine, err)
	}
	// Read empty line
	_, _ = reader.ReadString('\n')

	// Send echo payload over HTTP CONNECT tunnel
	httpMsg := "Hello from HTTP CONNECT Tunnel!"
	_, _ = httpConn.Write([]byte(httpMsg))
	buf2 := make([]byte, len(httpMsg))
	_, _ = io.ReadFull(reader, buf2)
	if string(buf2) != httpMsg {
		t.Fatalf("Echo mismatch via HTTP CONNECT: got %s, expected %s", string(buf2), httpMsg)
	}
}
