package stress

import (
	"bytes"
	"crypto/rand"
	"fmt"
	"math/big"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/sovereign/proxy/v4/pkg/crypto"
)

// TestNoiseHandshakeConcurrency stress-tests parallel Noise_IKpsk2 handshakes.
func TestNoiseHandshakeConcurrency(t *testing.T) {
	const numConcurrent = 2000
	var wg sync.WaitGroup
	var successCount int64
	var failCount int64

	start := time.Now()

	for i := 0; i < numConcurrent; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()

			aliceKP, err := crypto.GenerateKeypair()
			if err != nil {
				atomic.AddInt64(&failCount, 1)
				return
			}
			bobKP, err := crypto.GenerateKeypair()
			if err != nil {
				atomic.AddInt64(&failCount, 1)
				return
			}

			var psk [crypto.KeySize]byte
			rand.Read(psk[:])

			payload0RTT := []byte(fmt.Sprintf("0-RTT-Payload-worker-%d", idx))
			payloadAct2 := []byte(fmt.Sprintf("Act2-Response-worker-%d", idx))

			// Act 1
			act1, initState, err := crypto.InitHandshakeAct1(aliceKP, bobKP.PublicKey, psk, payload0RTT)
			if err != nil {
				atomic.AddInt64(&failCount, 1)
				return
			}

			// Responder Process Act 1
			act2, bobTransport, dec0RTT, err := crypto.ProcessHandshakeAct1(bobKP, psk, act1, payloadAct2)
			if err != nil {
				atomic.AddInt64(&failCount, 1)
				return
			}
			if !bytes.Equal(dec0RTT, payload0RTT) {
				atomic.AddInt64(&failCount, 1)
				return
			}

			// Initiator Process Act 2
			aliceTransport, decAct2, err := crypto.ProcessHandshakeAct2(initState, act2)
			if err != nil {
				atomic.AddInt64(&failCount, 1)
				return
			}
			if !bytes.Equal(decAct2, payloadAct2) {
				atomic.AddInt64(&failCount, 1)
				return
			}

			// Verify symmetric key alignment
			if !bytes.Equal(aliceTransport.SendKey[:], bobTransport.RecvKey[:]) ||
				!bytes.Equal(aliceTransport.RecvKey[:], bobTransport.SendKey[:]) {
				atomic.AddInt64(&failCount, 1)
				return
			}

			atomic.AddInt64(&successCount, 1)
		}(i)
	}

	wg.Wait()
	duration := time.Since(start)
	throughput := float64(successCount) / duration.Seconds()

	t.Logf("Noise Handshake Concurrency: %d/%d passed in %v (Throughput: %.2f handshakes/sec, Failures: %d)",
		successCount, numConcurrent, duration, throughput, failCount)

	if failCount > 0 {
		t.Fatalf("Handshake concurrency failed: %d errors encountered", failCount)
	}
	if successCount != int64(numConcurrent) {
		t.Fatalf("Expected %d successful handshakes, got %d", numConcurrent, successCount)
	}
}

// TestAntiReplayAdversarialStress stress-tests the 1024-packet sliding window.
func TestAntiReplayAdversarialStress(t *testing.T) {
	window := crypto.NewAntiReplayWindow()

	// 1. Monotonic stream with duplicates
	const totalPackets = 50000
	var accepted int
	var rejectedDuplicates int

	for seq := uint64(1); seq <= totalPackets; seq++ {
		if window.CheckAndAdd(seq) {
			accepted++
		} else {
			t.Fatalf("Unexpected rejection of fresh monotonic seq %d", seq)
		}

		// Replay attempt immediately
		if !window.CheckAndAdd(seq) {
			rejectedDuplicates++
		} else {
			t.Fatalf("Failed to reject immediate duplicate seq %d", seq)
		}
	}

	if accepted != totalPackets || rejectedDuplicates != totalPackets {
		t.Fatalf("Expected %d accepted & %d rejected, got %d & %d",
			totalPackets, totalPackets, accepted, rejectedDuplicates)
	}

	// 2. Out-of-order randomized permutations within window
	window.Reset()
	baseSeq := uint64(5000)
	window.CheckAndAdd(baseSeq)

	// In-window sequence numbers [baseSeq - 500 .. baseSeq - 1]
	seqList := make([]uint64, 0, 500)
	for s := baseSeq - 500; s < baseSeq; s++ {
		seqList = append(seqList, s)
	}

	// Fisher-Yates shuffle
	for i := len(seqList) - 1; i > 0; i-- {
		nBig, _ := rand.Int(rand.Reader, big.NewInt(int64(i+1)))
		j := int(nBig.Int64())
		seqList[i], seqList[j] = seqList[j], seqList[i]
	}

	for _, s := range seqList {
		if !window.CheckAndAdd(s) {
			t.Fatalf("Failed to accept valid out-of-order in-window seq %d", s)
		}
		// Duplicate check
		if window.CheckAndAdd(s) {
			t.Fatalf("Failed to reject duplicate out-of-order seq %d", s)
		}
	}

	// 3. Boundary leap forward & old packet rejection
	window.Reset()
	window.CheckAndAdd(10000)

	// Exactly at window boundary (10000 - 1023 = 8977: inside window)
	if !window.CheckAndAdd(8977) {
		t.Fatalf("Seq 8977 (diff 1023) should be inside 1024-bit window")
	}

	// Outside window boundary (10000 - 1024 = 8976: outside window)
	if window.CheckAndAdd(8976) {
		t.Fatalf("Seq 8976 (diff 1024) should be outside 1024-bit window")
	}
	if window.CheckAndAdd(5000) {
		t.Fatalf("Seq 5000 (diff 5000) should be rejected as too old")
	}

	// Massive leap forward to 1,000,000
	if !window.CheckAndAdd(1000000) {
		t.Fatalf("Massive leap forward to 1000000 should be accepted")
	}

	// All previous sequence numbers should now be rejected
	if window.CheckAndAdd(10000) {
		t.Fatalf("Seq 10000 should now be outside window after leap")
	}
	if window.CheckAndAdd(1000000 - 1024) {
		t.Fatalf("Seq %d should be outside window", 1000000-1024)
	}
	if !window.CheckAndAdd(1000000 - 1023) {
		t.Fatalf("Seq %d should be accepted (within 1023 of maxSeq)", 1000000-1023)
	}

	t.Logf("Anti-Replay Sliding Window adversarial stress tests PASSED successfully.")
}

// TestAntiReplayConcurrentRace verifies thread-safety of AntiReplayWindow under high concurrency.
func TestAntiReplayConcurrentRace(t *testing.T) {
	window := crypto.NewAntiReplayWindow()
	const numWorkers = 50
	const seqsPerWorker = 1000

	var wg sync.WaitGroup
	var totalAccepted int64
	var totalRejected int64

	for w := 0; w < numWorkers; w++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			for s := 1; s <= seqsPerWorker; s++ {
				seq := uint64(s) // All workers race on the exact same sequence numbers
				if window.CheckAndAdd(seq) {
					atomic.AddInt64(&totalAccepted, 1)
				} else {
					atomic.AddInt64(&totalRejected, 1)
				}
			}
		}(w)
	}

	wg.Wait()

	t.Logf("AntiReplay Concurrent Race: Accepted=%d, Rejected=%d (Expected Accepted=%d, Expected Rejected=%d)",
		totalAccepted, totalRejected, seqsPerWorker, (numWorkers-1)*seqsPerWorker)

	if totalAccepted != int64(seqsPerWorker) {
		t.Fatalf("Race condition detected! Exactly %d unique seqs should be accepted, got %d",
			seqsPerWorker, totalAccepted)
	}
	if totalRejected != int64((numWorkers-1)*seqsPerWorker) {
		t.Fatalf("Race condition detected! Exactly %d duplicates should be rejected, got %d",
			(numWorkers-1)*seqsPerWorker, totalRejected)
	}
}

// TestSingleKeyRotationGracePeriod verifies single session rekeying under normal packet ordering.
func TestSingleKeyRotationGracePeriod(t *testing.T) {
	aliceKP, _ := crypto.GenerateKeypair()
	bobKP, _ := crypto.GenerateKeypair()
	var psk [crypto.KeySize]byte
	rand.Read(psk[:])

	// Initial Handshake (Session 1)
	act1, init1, _ := crypto.InitHandshakeAct1(aliceKP, bobKP.PublicKey, psk, []byte("init1"))
	act2, bobTrans1, _, _ := crypto.ProcessHandshakeAct1(bobKP, psk, act1, []byte("ack1"))
	aliceTrans1, _, _ := crypto.ProcessHandshakeAct2(init1, act2)

	aliceRatchet := crypto.NewSessionRatchetManager(aliceTrans1, true, aliceKP, bobKP.PublicKey, psk)
	bobRatchet := crypto.NewSessionRatchetManager(bobTrans1, false, bobKP, aliceKP.PublicKey, psk)
	defer aliceRatchet.Close()
	defer bobRatchet.Close()

	// Send normal packets in session 1
	for i := 0; i < 5; i++ {
		msg := []byte(fmt.Sprintf("Session 1 Message %d", i))
		pkt, err := aliceRatchet.EncryptPacket(crypto.MsgTypeTransportData, msg)
		if err != nil {
			t.Fatalf("Session 1 encrypt error: %v", err)
		}
		dec, _, err := bobRatchet.DecryptPacket(pkt)
		if err != nil || !bytes.Equal(dec, msg) {
			t.Fatalf("Session 1 decrypt mismatch: %v", err)
		}
	}

	// Prepare Rekey (Session 2)
	act1Rekey, initRekey, _ := crypto.InitHandshakeAct1(aliceKP, bobKP.PublicKey, psk, []byte("init2"))
	act2Rekey, bobTrans2, _, _ := crypto.ProcessHandshakeAct1(bobKP, psk, act1Rekey, []byte("ack2"))
	aliceTrans2, _, _ := crypto.ProcessHandshakeAct2(initRekey, act2Rekey)

	aliceRatchet.RotateKeys(aliceTrans2)
	bobRatchet.RotateKeys(bobTrans2)

	// Send packets in session 2
	for i := 0; i < 5; i++ {
		msg := []byte(fmt.Sprintf("Session 2 Message %d", i))
		pkt, err := aliceRatchet.EncryptPacket(crypto.MsgTypeTransportData, msg)
		if err != nil {
			t.Fatalf("Session 2 encrypt error: %v", err)
		}
		dec, _, err := bobRatchet.DecryptPacket(pkt)
		if err != nil || !bytes.Equal(dec, msg) {
			t.Fatalf("Session 2 decrypt mismatch: %v", err)
		}
	}

	t.Logf("Single key rotation with clean session handoff PASSED.")
}

// TestVulnerabilityAntiReplayPrematureStateMutationOnRekey documents the premature state mutation vulnerability.
func TestVulnerabilityAntiReplayPrematureStateMutationOnRekey(t *testing.T) {
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

	// Alice creates in-flight packet with Seq 0 under Session 1
	inFlightPkt, err := aliceRatchet.EncryptPacket(crypto.MsgTypeTransportData, []byte("In-Flight-Seq-0"))
	if err != nil {
		t.Fatalf("Encrypt failed: %v", err)
	}

	// Session 2 established before in-flight packet arrives
	act1Rekey, initRekey, _ := crypto.InitHandshakeAct1(aliceKP, bobKP.PublicKey, psk, []byte("init2"))
	act2Rekey, bobTrans2, _, _ := crypto.ProcessHandshakeAct1(bobKP, psk, act1Rekey, []byte("ack2"))
	aliceTrans2, _, _ := crypto.ProcessHandshakeAct2(initRekey, act2Rekey)

	aliceRatchet.RotateKeys(aliceTrans2)
	bobRatchet.RotateKeys(bobTrans2)

	// Bob receives in-flight packet from Session 1
	dec1, _, err := bobRatchet.DecryptPacket(inFlightPkt)
	if err != nil {
		t.Fatalf("Failed to decrypt in-flight packet during grace period: %v", err)
	}
	if string(dec1) != "In-Flight-Seq-0" {
		t.Fatalf("Decrypted in-flight payload mismatch: got %s, expected In-Flight-Seq-0", string(dec1))
	}
	t.Logf("Decrypted in-flight packet: %s", string(dec1))

	// Now Alice sends Seq 0 of Session 2
	newSessionPkt, err := aliceRatchet.EncryptPacket(crypto.MsgTypeTransportData, []byte("New-Session-Seq-0"))
	if err != nil {
		t.Fatalf("New encrypt failed: %v", err)
	}

	dec2, _, err := bobRatchet.DecryptPacket(newSessionPkt)
	if err != nil {
		t.Fatalf("Session 2 packet Seq 0 was incorrectly rejected: %v", err)
	}
	if string(dec2) != "New-Session-Seq-0" {
		t.Fatalf("Decrypted Session 2 payload mismatch: got %s, expected New-Session-Seq-0", string(dec2))
	}
	t.Logf("Session 2 packet Seq 0 successfully decrypted without anti-replay state corruption.")
}
