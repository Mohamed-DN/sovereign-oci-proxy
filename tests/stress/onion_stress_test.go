package stress

import (
	"bytes"
	"crypto/rand"
	"fmt"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/sovereign/proxy/v4/pkg/crypto"
	"github.com/sovereign/proxy/v4/pkg/routing"
)

// TestOnionPaddingInvariant verifies that all encoded OnionCells are strictly 1420 bytes.
func TestOnionPaddingInvariant(t *testing.T) {
	testSizes := []int{0, 1, 10, 64, 128, 256, 512, 1024, routing.MaxCellPayloadSize}

	for _, size := range testSizes {
		payload := make([]byte, size)
		if size > 0 {
			rand.Read(payload)
		}

		cell := &routing.OnionCell{
			CircuitID: 99999,
			Command:   routing.CellCmdRelayData,
			StreamID:  12345,
			Digest:    0xDEADBEEF,
			Payload:   payload,
		}

		raw, err := routing.EncodeCell(cell)
		if err != nil {
			t.Fatalf("EncodeCell failed for size %d: %v", size, err)
		}

		if len(raw) != routing.OnionCellFixedSize {
			t.Fatalf("Padding invariant violated! Expected %d bytes, got %d for payload size %d",
				routing.OnionCellFixedSize, len(raw), size)
		}

		decoded, err := routing.DecodeCell(raw)
		if err != nil {
			t.Fatalf("DecodeCell failed for size %d: %v", size, err)
		}

		if decoded.CircuitID != 99999 || decoded.Command != routing.CellCmdRelayData || decoded.StreamID != 12345 {
			t.Fatalf("Decoded header mismatch for size %d", size)
		}

		if !bytes.Equal(decoded.Payload, payload) {
			t.Fatalf("Decoded payload mismatch for size %d: got len %d, expected len %d",
				size, len(decoded.Payload), len(payload))
		}
	}

	// Boundary test: payload > MaxCellPayloadSize should error
	overflowCell := &routing.OnionCell{
		CircuitID: 1,
		Command:   routing.CellCmdRelayData,
		Payload:   make([]byte, routing.MaxCellPayloadSize+1),
	}
	_, err := routing.EncodeCell(overflowCell)
	if err == nil {
		t.Fatalf("EncodeCell should reject payload exceeding MaxCellPayloadSize")
	}

	t.Logf("Onion Cell 1420-Byte Padding Invariant PASSED across all payload sizes (0 to %d bytes).",
		routing.MaxCellPayloadSize)
}

// Test3HopOnionLayerPeelingIntegrity stress-tests complete 3-hop circuit encryption and sequential peeling.
func Test3HopOnionLayerPeelingIntegrity(t *testing.T) {
	entryKP, _ := crypto.GenerateKeypair()
	middleKP, _ := crypto.GenerateKeypair()
	exitKP, _ := crypto.GenerateKeypair()

	entryHop := &routing.OnionHop{HopIndex: 0, NodeID: "entry-node-01", PublicKey: entryKP.PublicKey}
	middleHop := &routing.OnionHop{HopIndex: 1, NodeID: "middle-node-02", PublicKey: middleKP.PublicKey}
	exitHop := &routing.OnionHop{HopIndex: 2, NodeID: "exit-node-03", PublicKey: exitKP.PublicKey}

	circuit, err := routing.Build3HopCircuit(0xCAFE0001, entryHop, middleHop, exitHop)
	if err != nil {
		t.Fatalf("Build3HopCircuit failed: %v", err)
	}

	const targetAddr = "104.21.45.12:443"
	originalData := []byte("GET /sensitive-anti-censorship-payload HTTP/1.1\r\nHost: target.org\r\n\r\n")

	rawCell, err := circuit.EncryptLayeredData(42, targetAddr, originalData)
	if err != nil {
		t.Fatalf("EncryptLayeredData failed: %v", err)
	}

	if len(rawCell) != routing.OnionCellFixedSize {
		t.Fatalf("Raw onion cell size is %d, expected %d", len(rawCell), routing.OnionCellFixedSize)
	}

	cell, err := routing.DecodeCell(rawCell)
	if err != nil {
		t.Fatalf("DecodeCell failed: %v", err)
	}

	// 1. Peel Layer 1 (Entry Hop)
	peel1, err := routing.PeelLayer(entryKP.PrivateKey, 1, cell.Payload)
	if err != nil {
		t.Fatalf("Peel Layer 1 failed: %v", err)
	}
	if peel1.IsExit {
		t.Fatalf("Entry hop cannot be exit")
	}
	if !bytes.Equal(peel1.NextHopPub[:], middleKP.PublicKey[:]) {
		t.Fatalf("Layer 1 NextHopPub mismatch: expected middleKP, got %x", peel1.NextHopPub)
	}

	// 2. Peel Layer 2 (Middle Hop)
	peel2, err := routing.PeelLayer(middleKP.PrivateKey, 2, peel1.InnerPayload)
	if err != nil {
		t.Fatalf("Peel Layer 2 failed: %v", err)
	}
	if peel2.IsExit {
		t.Fatalf("Middle hop cannot be exit")
	}
	if !bytes.Equal(peel2.NextHopPub[:], exitKP.PublicKey[:]) {
		t.Fatalf("Layer 2 NextHopPub mismatch: expected exitKP, got %x", peel2.NextHopPub)
	}

	// 3. Peel Layer 3 (Exit Hop)
	peel3, err := routing.PeelLayer(exitKP.PrivateKey, 3, peel2.InnerPayload)
	if err != nil {
		t.Fatalf("Peel Layer 3 failed: %v", err)
	}
	if !peel3.IsExit {
		t.Fatalf("Exit hop must be marked as IsExit")
	}
	if peel3.TargetAddr != targetAddr {
		t.Fatalf("Target address mismatch: expected %s, got %s", targetAddr, peel3.TargetAddr)
	}
	if !bytes.Equal(peel3.InnerPayload, originalData) {
		t.Fatalf("Decapsulated data mismatch: got %s, expected %s", string(peel3.InnerPayload), string(originalData))
	}

	t.Logf("3-Hop Onion Layer Decapsulation Integrity Verified: Client -> Entry -> Middle -> Exit -> Target (%s)",
		targetAddr)
}

// TestCorruptedIntermediateLayerAdversarialStress tests tamper detection on any onion layer.
func TestCorruptedIntermediateLayerAdversarialStress(t *testing.T) {
	entryKP, _ := crypto.GenerateKeypair()
	middleKP, _ := crypto.GenerateKeypair()
	exitKP, _ := crypto.GenerateKeypair()

	entryHop := &routing.OnionHop{HopIndex: 0, NodeID: "entry-01", PublicKey: entryKP.PublicKey}
	middleHop := &routing.OnionHop{HopIndex: 1, NodeID: "middle-02", PublicKey: middleKP.PublicKey}
	exitHop := &routing.OnionHop{HopIndex: 2, NodeID: "exit-03", PublicKey: exitKP.PublicKey}

	circuit, _ := routing.Build3HopCircuit(1, entryHop, middleHop, exitHop)
	rawCell, err := circuit.EncryptLayeredData(1, "1.1.1.1:443", []byte("secret-payload"))
	if err != nil {
		t.Fatalf("EncryptLayeredData failed: %v", err)
	}

	cell, _ := routing.DecodeCell(rawCell)

	// Attack 1: Corrupt Layer 1 ciphertext (Entry hop tampering)
	corruptedL1 := append([]byte(nil), cell.Payload...)
	corruptedL1[len(corruptedL1)-5] ^= 0xAA
	_, err = routing.PeelLayer(entryKP.PrivateKey, 1, corruptedL1)
	if err == nil {
		t.Fatalf("PeelLayer 1 should fail when Layer 1 ciphertext is tampered")
	}

	// Attack 2: Wrong hop private key on Layer 1
	wrongKP, _ := crypto.GenerateKeypair()
	_, err = routing.PeelLayer(wrongKP.PrivateKey, 1, cell.Payload)
	if err == nil {
		t.Fatalf("PeelLayer 1 should fail when decrypted with unauthorized private key")
	}

	// Peel Layer 1 legitimately
	peel1, err := routing.PeelLayer(entryKP.PrivateKey, 1, cell.Payload)
	if err != nil {
		t.Fatalf("Peel Layer 1 error: %v", err)
	}

	// Attack 3: Corrupt Layer 2 ciphertext (Middle hop tampering)
	corruptedL2 := append([]byte(nil), peel1.InnerPayload...)
	corruptedL2[len(corruptedL2)-3] ^= 0x55
	_, err = routing.PeelLayer(middleKP.PrivateKey, 2, corruptedL2)
	if err == nil {
		t.Fatalf("PeelLayer 2 should fail when Layer 2 ciphertext is tampered")
	}

	// Peel Layer 2 legitimately
	peel2, err := routing.PeelLayer(middleKP.PrivateKey, 2, peel1.InnerPayload)
	if err != nil {
		t.Fatalf("Peel Layer 2 error: %v", err)
	}

	// Attack 4: Corrupt Layer 3 ciphertext (Exit hop tampering)
	corruptedL3 := append([]byte(nil), peel2.InnerPayload...)
	corruptedL3[len(corruptedL3)-1] ^= 0xFF
	_, err = routing.PeelLayer(exitKP.PrivateKey, 3, corruptedL3)
	if err == nil {
		t.Fatalf("PeelLayer 3 should fail when Layer 3 ciphertext is tampered")
	}

	t.Logf("Tamper & Corruption Adversarial Stress Tests: 100%% of corrupted layers were rejected by ChaCha20-Poly1305 AEAD.")
}

// TestHighConcurrencyOnionRouting stress-tests simultaneous 3-hop onion circuit operations.
func TestHighConcurrencyOnionRouting(t *testing.T) {
	const numCircuits = 500
	var wg sync.WaitGroup
	var successCount int64
	var failCount int64

	start := time.Now()

	for i := 0; i < numCircuits; i++ {
		wg.Add(1)
		go func(circuitID uint32) {
			defer wg.Done()

			eKP, _ := crypto.GenerateKeypair()
			mKP, _ := crypto.GenerateKeypair()
			xKP, _ := crypto.GenerateKeypair()

			eHop := &routing.OnionHop{HopIndex: 0, NodeID: fmt.Sprintf("e-%d", circuitID), PublicKey: eKP.PublicKey}
			mHop := &routing.OnionHop{HopIndex: 1, NodeID: fmt.Sprintf("m-%d", circuitID), PublicKey: mKP.PublicKey}
			xHop := &routing.OnionHop{HopIndex: 2, NodeID: fmt.Sprintf("x-%d", circuitID), PublicKey: xKP.PublicKey}

			circuit, err := routing.Build3HopCircuit(circuitID, eHop, mHop, xHop)
			if err != nil {
				atomic.AddInt64(&failCount, 1)
				return
			}

			payload := []byte(fmt.Sprintf("Parallel-Onion-Payload-%d", circuitID))
			rawCell, err := circuit.EncryptLayeredData(circuitID, "93.184.216.34:80", payload)
			if err != nil || len(rawCell) != routing.OnionCellFixedSize {
				atomic.AddInt64(&failCount, 1)
				return
			}

			cell, err := routing.DecodeCell(rawCell)
			if err != nil {
				atomic.AddInt64(&failCount, 1)
				return
			}

			p1, err := routing.PeelLayer(eKP.PrivateKey, 1, cell.Payload)
			if err != nil {
				atomic.AddInt64(&failCount, 1)
				return
			}

			p2, err := routing.PeelLayer(mKP.PrivateKey, 2, p1.InnerPayload)
			if err != nil {
				atomic.AddInt64(&failCount, 1)
				return
			}

			p3, err := routing.PeelLayer(xKP.PrivateKey, 3, p2.InnerPayload)
			if err != nil || !bytes.Equal(p3.InnerPayload, payload) {
				atomic.AddInt64(&failCount, 1)
				return
			}

			atomic.AddInt64(&successCount, 1)
		}(uint32(i + 1))
	}

	wg.Wait()
	dur := time.Since(start)
	throughput := float64(successCount) / dur.Seconds()

	t.Logf("High Concurrency 3-Hop Onion Routing: %d/%d circuits built & peeled in %v (%.2f circuits/sec, Failures: %d)",
		successCount, numCircuits, dur, throughput, failCount)

	if failCount > 0 || successCount != numCircuits {
		t.Fatalf("Onion routing concurrency test failed: %d errors", failCount)
	}
}
