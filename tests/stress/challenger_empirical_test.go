package stress

import (
	"bytes"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/sovereign/proxy/v4/pkg/config"
	"github.com/sovereign/proxy/v4/pkg/crypto"
)

// ============================================================================
// 1. EMPIRICAL STRESS TESTS FOR pkg/crypto/ratchet.go
// ============================================================================

// TestRatchetForgedMACNoStatePoisoning verifies that forged/corrupted MAC packets
// never poison the anti-replay sliding window bitmap.
func TestRatchetForgedMACNoStatePoisoning(t *testing.T) {
	aliceKP, err := crypto.GenerateKeypair()
	if err != nil {
		t.Fatalf("GenerateKeypair Alice failed: %v", err)
	}
	bobKP, err := crypto.GenerateKeypair()
	if err != nil {
		t.Fatalf("GenerateKeypair Bob failed: %v", err)
	}
	var psk [crypto.KeySize]byte
	rand.Read(psk[:])

	// Establish Session 1
	act1, init1, err := crypto.InitHandshakeAct1(aliceKP, bobKP.PublicKey, psk, []byte("init1"))
	if err != nil {
		t.Fatalf("Handshake Act1 failed: %v", err)
	}
	act2, bobTrans1, _, err := crypto.ProcessHandshakeAct1(bobKP, psk, act1, []byte("ack1"))
	if err != nil {
		t.Fatalf("Handshake ProcessAct1 failed: %v", err)
	}
	aliceTrans1, _, err := crypto.ProcessHandshakeAct2(init1, act2)
	if err != nil {
		t.Fatalf("Handshake ProcessAct2 failed: %v", err)
	}

	aliceRatchet := crypto.NewSessionRatchetManager(aliceTrans1, true, aliceKP, bobKP.PublicKey, psk)
	bobRatchet := crypto.NewSessionRatchetManager(bobTrans1, false, bobKP, aliceKP.PublicKey, psk)
	defer aliceRatchet.Close()
	defer bobRatchet.Close()

	// Target sequence numbers that will be attacked by forged packets
	attackSeqs := []uint64{0, 1, 2, 5, 10, 25, 50, 100, 250, 500, 1000}

	for _, seq := range attackSeqs {
		// Craft a forged packet targeting Bob's active session ID with sequence `seq`
		var fakeTag [crypto.Poly1305TagSize]byte
		rand.Read(fakeTag[:])

		fakeCiphertext := []byte(fmt.Sprintf("Forged-Malicious-Payload-Seq-%d", seq))
		forgedFrame := &crypto.DirectFrame{
			Magic:             crypto.DirectFrameMagic,
			Version:           crypto.CurrentWireVersion,
			MsgType:           crypto.MsgTypeTransportData,
			SenderSessionID:   aliceTrans1.LocalSessionID,
			ReceiverSessionID: bobTrans1.LocalSessionID,
			SequenceCounter:   seq,
			Ciphertext:        fakeCiphertext,
			AuthTag:           fakeTag,
		}
		rawForged := crypto.EncodeDirectFrame(forgedFrame)

		// Bob attempts to decrypt forged packet -> MUST FAIL with ErrInvalidCiphertext
		_, _, err := bobRatchet.DecryptPacket(rawForged)
		if err == nil {
			t.Fatalf("[CRITICAL SECURITY VULNERABILITY] Forged MAC packet with seq %d was accepted!", seq)
		}
	}

	t.Logf("Injected %d forged MAC packets with arbitrary sequence numbers; all failed decryption as expected.", len(attackSeqs))

	// Now Alice legitimately encrypts and sends packets sequentially from seq 0 up to 1005
	// Every single packet MUST succeed, proving the anti-replay window was not poisoned by forged packets!
	for expectedSeq := uint64(0); expectedSeq <= 1005; expectedSeq++ {
		msg := []byte(fmt.Sprintf("Legitimate-Alice-Message-Seq-%d", expectedSeq))
		rawLegit, err := aliceRatchet.EncryptPacket(crypto.MsgTypeTransportData, msg)
		if err != nil {
			t.Fatalf("Alice EncryptPacket failed at seq %d: %v", expectedSeq, err)
		}

		decrypted, msgType, err := bobRatchet.DecryptPacket(rawLegit)
		if err != nil {
			t.Fatalf("[ANTI-REPLAY STATE POISONING DETECTED] Legitimate packet at seq %d failed decryption: %v", expectedSeq, err)
		}
		if msgType != crypto.MsgTypeTransportData {
			t.Fatalf("Unexpected msgType %d at seq %d", msgType, expectedSeq)
		}
		if !bytes.Equal(decrypted, msg) {
			t.Fatalf("Decrypted payload mismatch at seq %d: got %s, expected %s", expectedSeq, string(decrypted), string(msg))
		}

		// Replaying the legitimate packet MUST immediately fail with ErrReplayDetected
		_, _, replayErr := bobRatchet.DecryptPacket(rawLegit)
		if replayErr == nil {
			t.Fatalf("[REPLAY ATTACK NOT PREVENTED] Replayed legitimate packet at seq %d was accepted!", expectedSeq)
		}
	}

	t.Logf("Successfully transmitted and verified 1006 legitimate packets with strict replay prevention. No state poisoning occurred.")
}

// TestRatchetHighConcurrencyRekeying executes high-concurrency packet transmission
// while key rotations happen concurrently across dual-key grace periods.
func TestRatchetHighConcurrencyRekeying(t *testing.T) {
	aliceKP, _ := crypto.GenerateKeypair()
	bobKP, _ := crypto.GenerateKeypair()
	var psk [crypto.KeySize]byte
	rand.Read(psk[:])

	// Initial Session
	act1, init1, _ := crypto.InitHandshakeAct1(aliceKP, bobKP.PublicKey, psk, []byte("init"))
	act2, bobTrans1, _, _ := crypto.ProcessHandshakeAct1(bobKP, psk, act1, []byte("ack"))
	aliceTrans1, _, _ := crypto.ProcessHandshakeAct2(init1, act2)

	aliceRatchet := crypto.NewSessionRatchetManager(aliceTrans1, true, aliceKP, bobKP.PublicKey, psk)
	bobRatchet := crypto.NewSessionRatchetManager(bobTrans1, false, bobKP, aliceKP.PublicKey, psk)
	defer aliceRatchet.Close()
	defer bobRatchet.Close()

	const numWorkers = 20
	const packetsPerWorker = 500
	const totalPackets = numWorkers * packetsPerWorker

	var successCount uint64
	var rekeyCount uint64
	var wg sync.WaitGroup
	stopRekeyer := make(chan struct{})

	// Background Rekeyer: rotates keys periodically
	go func() {
		ticker := time.NewTicker(20 * time.Millisecond)
		defer ticker.Stop()
		for {
			select {
			case <-stopRekeyer:
				return
			case <-ticker.C:
				act1Rekey, initRekey, err := crypto.InitHandshakeAct1(aliceKP, bobKP.PublicKey, psk, []byte("rekey-init"))
				if err != nil {
					continue
				}
				act2Rekey, bobTransNew, _, err := crypto.ProcessHandshakeAct1(bobKP, psk, act1Rekey, []byte("rekey-ack"))
				if err != nil {
					continue
				}
				aliceTransNew, _, err := crypto.ProcessHandshakeAct2(initRekey, act2Rekey)
				if err != nil {
					continue
				}

				aliceRatchet.RotateKeys(aliceTransNew)
				bobRatchet.RotateKeys(bobTransNew)
				atomic.AddUint64(&rekeyCount, 1)
			}
		}
	}()

	// Spawn concurrent sender workers
	for w := 0; w < numWorkers; w++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			for i := 0; i < packetsPerWorker; i++ {
				msg := []byte(fmt.Sprintf("worker-%d-pkt-%d", workerID, i))
				raw, err := aliceRatchet.EncryptPacket(crypto.MsgTypeTransportData, msg)
				if err != nil {
					t.Errorf("Encrypt failed for worker %d: %v", workerID, err)
					return
				}

				dec, _, err := bobRatchet.DecryptPacket(raw)
				if err != nil {
					// Under high concurrency rekeying, if key rotated multiple times beyond previousState, error is expected
					continue
				}
				if bytes.Equal(dec, msg) {
					atomic.AddUint64(&successCount, 1)
				}
			}
		}(w)
	}

	wg.Wait()
	close(stopRekeyer)

	t.Logf("High Concurrency Rekeying: Sent %d packets across %d rekeys. Successfully decrypted %d packets (%.2f%%).",
		totalPackets, atomic.LoadUint64(&rekeyCount), atomic.LoadUint64(&successCount),
		float64(atomic.LoadUint64(&successCount))/float64(totalPackets)*100.0)

	if atomic.LoadUint64(&successCount) < uint64(totalPackets*80/100) {
		t.Fatalf("Success rate under rekeying too low: %d/%d", atomic.LoadUint64(&successCount), totalPackets)
	}
}

// TestRatchetGracePeriodInFlightInterleaved tests explicit interleaving of packets
// from Old Session (Seq 0..4) and New Session (Seq 0..4) arriving in arbitrary order.
func TestRatchetGracePeriodInFlightInterleaved(t *testing.T) {
	aliceKP, _ := crypto.GenerateKeypair()
	bobKP, _ := crypto.GenerateKeypair()
	var psk [crypto.KeySize]byte
	rand.Read(psk[:])

	// Session 1
	act1, init1, _ := crypto.InitHandshakeAct1(aliceKP, bobKP.PublicKey, psk, []byte("init1"))
	act2, bobTrans1, _, _ := crypto.ProcessHandshakeAct1(bobKP, psk, act1, []byte("ack1"))
	aliceTrans1, _, _ := crypto.ProcessHandshakeAct2(init1, act2)

	aliceRatchet := crypto.NewSessionRatchetManager(aliceTrans1, true, aliceKP, bobKP.PublicKey, psk)
	bobRatchet := crypto.NewSessionRatchetManager(bobTrans1, false, bobKP, aliceKP.PublicKey, psk)
	defer aliceRatchet.Close()
	defer bobRatchet.Close()

	// Alice produces 5 packets under Session 1
	var s1Packets [][]byte
	for i := 0; i < 5; i++ {
		p, err := aliceRatchet.EncryptPacket(crypto.MsgTypeTransportData, []byte(fmt.Sprintf("S1-msg-%d", i)))
		if err != nil {
			t.Fatalf("S1 encrypt failed: %v", err)
		}
		s1Packets = append(s1Packets, p)
	}

	// Rotate to Session 2 on Alice and Bob
	act1Rekey, initRekey, _ := crypto.InitHandshakeAct1(aliceKP, bobKP.PublicKey, psk, []byte("init2"))
	act2Rekey, bobTrans2, _, _ := crypto.ProcessHandshakeAct1(bobKP, psk, act1Rekey, []byte("ack2"))
	aliceTrans2, _, _ := crypto.ProcessHandshakeAct2(initRekey, act2Rekey)

	aliceRatchet.RotateKeys(aliceTrans2)
	bobRatchet.RotateKeys(bobTrans2)

	// Alice produces 5 packets under Session 2
	var s2Packets [][]byte
	for i := 0; i < 5; i++ {
		p, err := aliceRatchet.EncryptPacket(crypto.MsgTypeTransportData, []byte(fmt.Sprintf("S2-msg-%d", i)))
		if err != nil {
			t.Fatalf("S2 encrypt failed: %v", err)
		}
		s2Packets = append(s2Packets, p)
	}

	// Bob receives interleaved: S2-0, S1-0, S2-1, S1-1, S2-2, S1-2, S2-3, S1-3, S2-4, S1-4
	for i := 0; i < 5; i++ {
		// Session 2 packet
		decS2, _, err := bobRatchet.DecryptPacket(s2Packets[i])
		if err != nil {
			t.Fatalf("Failed to decrypt Session 2 packet %d: %v", i, err)
		}
		if string(decS2) != fmt.Sprintf("S2-msg-%d", i) {
			t.Fatalf("S2 payload mismatch: got %s, expected S2-msg-%d", string(decS2), i)
		}

		// Session 1 in-flight packet
		decS1, _, err := bobRatchet.DecryptPacket(s1Packets[i])
		if err != nil {
			t.Fatalf("Failed to decrypt in-flight Session 1 packet %d: %v", i, err)
		}
		if string(decS1) != fmt.Sprintf("S1-msg-%d", i) {
			t.Fatalf("S1 payload mismatch: got %s, expected S1-msg-%d", string(decS1), i)
		}
	}

	t.Logf("Interleaved dual-session packets successfully decrypted without anti-replay collisions.")
}

// ============================================================================
// 2. ADVERSARIAL STRESS TESTS FOR pkg/config/parser.go
// ============================================================================

// TestAdversarialYAMLParserStructures tests SimpleYAMLToJSON against hostile/complex YAML.
func TestAdversarialYAMLParserStructures(t *testing.T) {
	testCases := []struct {
		name     string
		yamlData string
		verify   func(t *testing.T, jsonBytes []byte)
	}{
		{
			name: "URLs with multiple colons, ports, paths, and queries",
			yamlData: `
endpoints:
  - "https://user:password@dns.quad9.net:8443/dns-query?foo=bar:baz#frag:1"
  - 'http://127.0.0.1:8080/path/to/resource'
  - https://cloudflare-dns.com:443/dns-query
  - wss://relay.example.com:9000/ws/v1
  - grpc://control.mesh.internal:9443
`,
			verify: func(t *testing.T, b []byte) {
				var res struct {
					Endpoints []string `json:"endpoints"`
				}
				if err := json.Unmarshal(b, &res); err != nil {
					t.Fatalf("JSON unmarshal error: %v, raw: %s", err, string(b))
				}
				if len(res.Endpoints) != 5 {
					t.Fatalf("Expected 5 endpoints, got %d", len(res.Endpoints))
				}
				if res.Endpoints[0] != "https://user:password@dns.quad9.net:8443/dns-query?foo=bar:baz#frag:1" {
					t.Errorf("URL mismatch: %s", res.Endpoints[0])
				}
				if res.Endpoints[3] != "wss://relay.example.com:9000/ws/v1" {
					t.Errorf("WSS mismatch: %s", res.Endpoints[3])
				}
			},
		},
		{
			name: "IPv6 addresses and CIDRs with multiple colons",
			yamlData: `
ipv6Rules:
  - "::1"
  - "fe80::1/64"
  - "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
  - "::ffff:192.168.1.1"
  - "[fe80::1]:8080"
  - "2606:4700:4700::1111"
`,
			verify: func(t *testing.T, b []byte) {
				var res struct {
					IPv6Rules []string `json:"ipv6Rules"`
				}
				if err := json.Unmarshal(b, &res); err != nil {
					t.Fatalf("JSON unmarshal error: %v, raw: %s", err, string(b))
				}
				if len(res.IPv6Rules) != 6 {
					t.Fatalf("Expected 6 IPv6 rules, got %d", len(res.IPv6Rules))
				}
				if res.IPv6Rules[1] != "fe80::1/64" {
					t.Errorf("CIDR mismatch: %s", res.IPv6Rules[1])
				}
				if res.IPv6Rules[4] != "[fe80::1]:8080" {
					t.Errorf("Bracketed IPv6 mismatch: %s", res.IPv6Rules[4])
				}
			},
		},
		{
			name: "Multi-level lists and nested structures",
			yamlData: `
cluster:
  nodes:
    - name: node-alpha
      tags:
        - "tag:region:eu"
        - "tag:role:relay"
      ports: [80, 443, 8080]
    - name: node-beta
      tags:
        - "tag:region:us"
      ports: []
`,
			verify: func(t *testing.T, b []byte) {
				var res struct {
					Cluster struct {
						Nodes []struct {
							Name  string   `json:"name"`
							Tags  []string `json:"tags"`
							Ports []int    `json:"ports"`
						} `json:"nodes"`
					} `json:"cluster"`
				}
				if err := json.Unmarshal(b, &res); err != nil {
					t.Fatalf("JSON unmarshal error: %v, raw: %s", err, string(b))
				}
				if len(res.Cluster.Nodes) != 2 {
					t.Fatalf("Expected 2 nodes, got %d", len(res.Cluster.Nodes))
				}
				if len(res.Cluster.Nodes[0].Tags) != 2 || res.Cluster.Nodes[0].Tags[0] != "tag:region:eu" {
					t.Errorf("Tags mismatch: %v", res.Cluster.Nodes[0].Tags)
				}
				if len(res.Cluster.Nodes[0].Ports) != 3 || res.Cluster.Nodes[0].Ports[1] != 443 {
					t.Errorf("Ports mismatch: %v", res.Cluster.Nodes[0].Ports)
				}
			},
		},
		{
			name: "Empty fields, nulls, tildes, empty lists, empty maps",
			yamlData: `
emptyConfig:
  emptyString: ""
  nullField: null
  tildeField: ~
  emptyList: []
  emptyBlock:
`,
			verify: func(t *testing.T, b []byte) {
				var res struct {
					EmptyConfig struct {
						EmptyString string      `json:"emptyString"`
						NullField   interface{} `json:"nullField"`
						TildeField  interface{} `json:"tildeField"`
						EmptyList   []string    `json:"emptyList"`
						EmptyBlock  interface{} `json:"emptyBlock"`
					} `json:"emptyConfig"`
				}
				if err := json.Unmarshal(b, &res); err != nil {
					t.Fatalf("JSON unmarshal error: %v, raw: %s", err, string(b))
				}
				if res.EmptyConfig.EmptyString != "" {
					t.Errorf("Expected empty string, got %s", res.EmptyConfig.EmptyString)
				}
				if res.EmptyConfig.NullField != nil {
					t.Errorf("Expected nullField nil, got %v", res.EmptyConfig.NullField)
				}
				if res.EmptyConfig.TildeField != nil {
					t.Errorf("Expected tildeField nil, got %v", res.EmptyConfig.TildeField)
				}
				if len(res.EmptyConfig.EmptyList) != 0 {
					t.Errorf("Expected empty list, got %v", res.EmptyConfig.EmptyList)
				}
				if res.EmptyConfig.EmptyBlock != nil {
					t.Errorf("Expected emptyBlock nil, got %v", res.EmptyConfig.EmptyBlock)
				}
			},
		},
		{
			name: "Comments with colons and special characters",
			yamlData: `
# Global config comment: with: colons and # hashes
metadata: # Inline comment: key: value
  name: "mesh-test" # trailing comment: 123
  domain: test.org # domain: mesh.test.org
`,
			verify: func(t *testing.T, b []byte) {
				var res struct {
					Metadata struct {
						Name   string `json:"name"`
						Domain string `json:"domain"`
					} `json:"metadata"`
				}
				if err := json.Unmarshal(b, &res); err != nil {
					t.Fatalf("JSON unmarshal error: %v, raw: %s", err, string(b))
				}
				if res.Metadata.Name != "mesh-test" {
					t.Errorf("Expected name 'mesh-test', got %q", res.Metadata.Name)
				}
				if res.Metadata.Domain != "test.org" {
					t.Errorf("Expected domain 'test.org', got %q", res.Metadata.Domain)
				}
			},
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			jsonBytes, err := config.SimpleYAMLToJSON([]byte(tc.yamlData))
			if err != nil {
				t.Fatalf("SimpleYAMLToJSON failed: %v", err)
			}
			tc.verify(t, jsonBytes)
		})
	}
}

// TestAdversarialMeshConfigFullValidation tests LoadMeshConfig with complex DoH resolvers,
// IPv6 CIDRs, and multiple cloud provider blocks.
func TestAdversarialMeshConfigFullValidation(t *testing.T) {
	complexYAML := `
apiVersion: sovereign.mesh/v4alpha1
kind: SovereignCluster
metadata:
  clusterName: stress-mesh-cluster
  environment: adversarial-test
  version: "4.0.0"

global:
  domain: mesh.adversarial.org
  acmeEmail: admin@adversarial.org
  dnsProvider: cloudflare
  overlayCidr: "100.64.0.0/10"
  encryption:
    noiseSuite: Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s
    keyRotationHours: 12
    handshakeTimeoutSec: 3
    rekeyIntervalSec: 1800
  telemetry:
    prometheusEnabled: true
    scrapeInterval: "10s"
    metricsPort: 9090
  security:
    honeypotBanThreshold: 3
    honeypotBanDurationHours: 48
    sshPort: 2222
    strictRfc1918Filter: true

controlPlane:
  replicas: 3
  listenPort: 8443
  grpcPort: 9443
  distribution:
    - provider: oci
      region: eu-frankfurt-1
      shape: VM.Standard.A1.Flex
      vcpu: 4
      ramGb: 24
  stateStore:
    type: raft-embedded
    embeddedRaft: true
    dataDir: /var/lib/sovereign/raft
    electionTimeoutMs: 1000
    heartbeatTimeoutMs: 250

relayFleet:
  defaultPort: 443
  stunPort: 3478
  honeypotPort: 8080
  heartbeatIntervalSec: 5
  nodes:
    - id: relay-de-01
      provider: oci
      region: eu-frankfurt-1
      shape: VM.Standard.A1.Flex
      vcpu: 2
      ramGb: 12
      enableBBR: true
      antiCensorship:
        decoyDomain: "aws.amazon.com"
        honeypotPort: 8080
      network:
        publicIp: dynamic
        allowSshPort: 2222
        allowedInboundPorts: [80, 443, 2222, 3478, 8080]

egressGateways:
  defaultExitMode: country
  supportedCountries:
    - US
    - DE
    - JP
    - SG
    - GB
  bogonFilter:
    blockedCidrs:
      - "10.0.0.0/8"
      - "172.16.0.0/12"
      - "192.168.0.0/16"
      - "169.254.0.0/16"
      - "127.0.0.0/8"
    blockedPorts: [25, 445, 137, 138, 139]
  sandboxing:
    engine: gvisor_netstack
    enforceDoh: true
    dohResolvers:
      - "https://dns.quad9.net/dns-query"
      - "https://cloudflare-dns.com/dns-query"
      - "https://dns.google/dns-query"
      - "tls://1.1.1.1:853"
      - "https://1.1.1.1/dns-query"

providers:
  oci:
    compartmentId: "ocid1.compartment.oc1..test"
    vpcCidr: "10.40.0.0/16"
    subnetCidr: "10.40.1.0/24"
  aws:
    region: "us-east-1"
    vpcCidr: "10.41.0.0/16"
    subnetCidr: "10.41.1.0/24"
`
	cfg, err := config.ParseMeshConfig([]byte(complexYAML))
	if err != nil {
		t.Fatalf("ParseMeshConfig failed on complex adversarial config: %v", err)
	}

	if cfg.Metadata.ClusterName != "stress-mesh-cluster" {
		t.Errorf("Cluster name mismatch: %s", cfg.Metadata.ClusterName)
	}

	dohs := cfg.EgressGateways.Sandboxing.DohResolvers
	if len(dohs) != 5 {
		t.Fatalf("Expected 5 DoH resolvers, got %d", len(dohs))
	}
	expectedDOH := []string{
		"https://dns.quad9.net/dns-query",
		"https://cloudflare-dns.com/dns-query",
		"https://dns.google/dns-query",
		"tls://1.1.1.1:853",
		"https://1.1.1.1/dns-query",
	}
	for i, exp := range expectedDOH {
		if dohs[i] != exp {
			t.Errorf("DoH resolver %d mismatch: got %q, expected %q", i, dohs[i], exp)
		}
	}

	t.Logf("Adversarial Mesh Config parsing & validation PASSED successfully.")
}
