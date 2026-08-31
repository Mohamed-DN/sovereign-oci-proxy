package stress

import (
	"bytes"
	"crypto/rand"
	"errors"
	"fmt"
	"math"
	mrand "math/rand"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/sovereign/proxy/v4/pkg/crypto"
	"github.com/sovereign/proxy/v4/pkg/routing"
)

// ============================================================================
// 1. ADVERSARIAL NOISE PROTOCOL HANDSHAKE STRESS & FUZZING
// ============================================================================

func TestAdversarialNoiseHandshakeFuzzAndBitFlipping(t *testing.T) {
	initStatic, err := crypto.GenerateKeypair()
	if err != nil {
		t.Fatalf("Failed to generate initiator static key: %v", err)
	}
	respStatic, err := crypto.GenerateKeypair()
	if err != nil {
		t.Fatalf("Failed to generate responder static key: %v", err)
	}

	var psk [crypto.KeySize]byte
	if _, err := rand.Read(psk[:]); err != nil {
		t.Fatalf("Failed to generate PSK: %v", err)
	}

	payload0RTT := []byte("ADVERSARIAL_0RTT_PAYLOAD_TEST_DATA_1234567890")
	payloadAct2 := []byte("ADVERSARIAL_ACT2_RESPONSE_PAYLOAD_TEST_0987654321")

	// --- 1.1 Zero Session ID Rejection ---
	act1, _, err := crypto.InitHandshakeAct1(initStatic, respStatic.PublicKey, psk, payload0RTT)
	if err != nil {
		t.Fatalf("InitHandshakeAct1 failed: %v", err)
	}
	act1Bad := *act1
	act1Bad.SenderSessionID = 0
	_, _, _, err = crypto.ProcessHandshakeAct1(respStatic, psk, &act1Bad, payloadAct2)
	if err == nil {
		t.Fatalf("ProcessHandshakeAct1 MUST reject Act 1 with SenderSessionID=0, but succeeded!")
	}

	// --- 1.2 PSK Mismatch Adversarial Resistance ---
	var badPSK [crypto.KeySize]byte
	copy(badPSK[:], psk[:])
	badPSK[0] ^= 0xFF // Invert first byte

	_, _, _, err = crypto.ProcessHandshakeAct1(respStatic, badPSK, act1, payloadAct2)
	if err == nil {
		t.Fatalf("ProcessHandshakeAct1 MUST reject handshake when PSK is corrupted, but succeeded!")
	}
	if !errors.Is(err, crypto.ErrAuthFailed) {
		t.Logf("ProcessHandshakeAct1 rejected corrupted PSK with: %v", err)
	}

	// --- 1.3 Responder Static Key Mismatch ---
	wrongRespStatic, _ := crypto.GenerateKeypair()
	_, _, _, err = crypto.ProcessHandshakeAct1(wrongRespStatic, psk, act1, payloadAct2)
	if err == nil {
		t.Fatalf("ProcessHandshakeAct1 MUST reject handshake when responder key does not match intended recipient!")
	}

	// --- 1.4 Bit-Flipping Fuzzing Across All Act 1 Fields ---
	// EphemeralPub bit flipping (32 bytes)
	for byteIdx := 0; byteIdx < crypto.KeySize; byteIdx++ {
		for bit := 0; bit < 8; bit++ {
			corruptedAct1 := *act1
			corruptedAct1.EphemeralPub[byteIdx] ^= (1 << bit)
			_, _, _, err := crypto.ProcessHandshakeAct1(respStatic, psk, &corruptedAct1, payloadAct2)
			if err == nil {
				t.Fatalf("Act 1 EphemeralPub bit-flip [byte %d, bit %d] was NOT rejected by AEAD/DH!", byteIdx, bit)
			}
		}
	}

	// EncryptedStatic bit flipping (48 bytes: 32B static + 16B Poly1305 tag)
	for byteIdx := 0; byteIdx < len(act1.EncryptedStatic); byteIdx++ {
		for bit := 0; bit < 8; bit++ {
			corruptedAct1 := *act1
			corruptedAct1.EncryptedStatic[byteIdx] ^= (1 << bit)
			_, _, _, err := crypto.ProcessHandshakeAct1(respStatic, psk, &corruptedAct1, payloadAct2)
			if err == nil {
				t.Fatalf("Act 1 EncryptedStatic bit-flip [byte %d, bit %d] was NOT rejected by AEAD!", byteIdx, bit)
			}
		}
	}

	// EncryptedPayload bit flipping
	for byteIdx := 0; byteIdx < len(act1.EncryptedPayload); byteIdx++ {
		corruptedPayload := make([]byte, len(act1.EncryptedPayload))
		copy(corruptedPayload, act1.EncryptedPayload)
		corruptedPayload[byteIdx] ^= 0xAA // Flip multiple bits
		corruptedAct1 := *act1
		corruptedAct1.EncryptedPayload = corruptedPayload

		_, _, _, err := crypto.ProcessHandshakeAct1(respStatic, psk, &corruptedAct1, payloadAct2)
		if err == nil {
			t.Fatalf("Act 1 EncryptedPayload bit-flip at offset %d was NOT rejected by AEAD!", byteIdx)
		}
	}

	// --- 1.5 Bit-Flipping Fuzzing Across All Act 2 Fields ---
	act1Valid, initState, err := crypto.InitHandshakeAct1(initStatic, respStatic.PublicKey, psk, payload0RTT)
	if err != nil {
		t.Fatalf("Valid Act 1 generation failed: %v", err)
	}
	act2Valid, _, _, err := crypto.ProcessHandshakeAct1(respStatic, psk, act1Valid, payloadAct2)
	if err != nil {
		t.Fatalf("Valid Act 2 generation failed: %v", err)
	}

	// Mismatched ReceiverSessionID
	corruptedAct2 := *act2Valid
	corruptedAct2.ReceiverSessionID = initState.SenderSessionID ^ 0xDEADBEEF
	_, _, err = crypto.ProcessHandshakeAct2(initState, &corruptedAct2)
	if err == nil {
		t.Fatalf("ProcessHandshakeAct2 MUST reject mismatched ReceiverSessionID!")
	}

	// EphemeralPub bit flipping in Act 2
	for byteIdx := 0; byteIdx < crypto.KeySize; byteIdx++ {
		corruptedAct2 := *act2Valid
		corruptedAct2.EphemeralPub[byteIdx] ^= 0x55
		_, _, err := crypto.ProcessHandshakeAct2(initState, &corruptedAct2)
		if err == nil {
			t.Fatalf("Act 2 EphemeralPub corruption at byte %d was NOT rejected!", byteIdx)
		}
	}

	// EncryptedPayload bit flipping in Act 2
	for byteIdx := 0; byteIdx < len(act2Valid.EncryptedPayload); byteIdx++ {
		corruptedPayload := make([]byte, len(act2Valid.EncryptedPayload))
		copy(corruptedPayload, act2Valid.EncryptedPayload)
		corruptedPayload[byteIdx] ^= 0xFF
		corruptedAct2 := *act2Valid
		corruptedAct2.EncryptedPayload = corruptedPayload
		_, _, err := crypto.ProcessHandshakeAct2(initState, &corruptedAct2)
		if err == nil {
			t.Fatalf("Act 2 EncryptedPayload corruption at byte %d was NOT rejected!", byteIdx)
		}
	}

	// --- 1.6 Ephemeral Secret Zeroization (Memory Sanitization) ---
	// Complete a clean handshake and verify initiator ephemeral secret is wiped
	act1Clean, initStateClean, err := crypto.InitHandshakeAct1(initStatic, respStatic.PublicKey, psk, payload0RTT)
	if err != nil {
		t.Fatalf("Clean Act 1 failed: %v", err)
	}
	act2Clean, _, _, err := crypto.ProcessHandshakeAct1(respStatic, psk, act1Clean, payloadAct2)
	if err != nil {
		t.Fatalf("Clean Act 2 failed: %v", err)
	}
	_, _, err = crypto.ProcessHandshakeAct2(initStateClean, act2Clean)
	if err != nil {
		t.Fatalf("Clean ProcessHandshakeAct2 failed: %v", err)
	}

	// Verify EphemeralPriv was wiped with zeros
	var zeroKey [crypto.KeySize]byte
	if initStateClean.EphemeralPriv != zeroKey {
		t.Fatalf("Initiator ephemeral private key was NOT wiped after handshake completion!")
	}

	t.Logf("PASS: Noise IKpsk2 Handshake passed all %d adversarial bit-flip and fuzz permutations.",
		(crypto.KeySize*8)+(len(act1.EncryptedStatic)*8)+len(act1.EncryptedPayload)+crypto.KeySize+len(act2Valid.EncryptedPayload)+4)
}

// ============================================================================
// 2. ADVERSARIAL SVRN DIRECT WIRE FRAMING STRESS
// ============================================================================

func TestAdversarialSVRNWireFramingStress(t *testing.T) {
	// --- 2.1 Magic Header Fuzzing ---
	badMagics := []uint32{
		0x00000000,
		0xFFFFFFFF,
		0x5356524F, // SVR "O"
		0x5356524D, // SVR "M"
		0x5456524E, // TVRN
		0x12345678,
	}

	for _, bm := range badMagics {
		frame := &crypto.DirectFrame{
			Magic:             bm,
			Version:           crypto.CurrentWireVersion,
			MsgType:           crypto.MsgTypeTransportData,
			SenderSessionID:   1001,
			ReceiverSessionID: 2002,
			SequenceCounter:   1,
			Ciphertext:        []byte("VALID_CIPHERTEXT_16B"),
			AuthTag:           [16]byte{0x01, 0x02, 0x03, 0x04},
		}
		raw := crypto.EncodeDirectFrame(frame)
		_, err := crypto.DecodeDirectFrame(raw)
		if err == nil {
			t.Fatalf("DecodeDirectFrame accepted invalid magic 0x%08X!", bm)
		}
		if !errors.Is(err, crypto.ErrInvalidMagic) {
			t.Logf("Rejected bad magic 0x%08X with: %v", bm, err)
		}
	}

	// --- 2.2 Wire Version Exhaustion ---
	for v := 0; v < 256; v++ {
		version := uint8(v)
		if version == crypto.CurrentWireVersion {
			continue // 0x04 is valid
		}

		frame := &crypto.DirectFrame{
			Magic:             crypto.DirectFrameMagic,
			Version:           version,
			MsgType:           crypto.MsgTypeTransportData,
			SenderSessionID:   1001,
			ReceiverSessionID: 2002,
			SequenceCounter:   1,
			Ciphertext:        []byte("VALID_CIPHERTEXT_16B"),
			AuthTag:           [16]byte{0x01, 0x02, 0x03, 0x04},
		}
		raw := crypto.EncodeDirectFrame(frame)
		_, err := crypto.DecodeDirectFrame(raw)
		if err == nil {
			t.Fatalf("DecodeDirectFrame accepted invalid version 0x%02X!", version)
		}
		if !errors.Is(err, crypto.ErrUnsupportedVersion) {
			t.Fatalf("Expected ErrUnsupportedVersion for version 0x%02X, got: %v", version, err)
		}
	}

	// --- 2.3 Buffer Length Boundary Conditions ---
	for length := 0; length < crypto.MinDirectFrameSize; length++ {
		shortBuf := make([]byte, length)
		_, err := crypto.DecodeDirectFrame(shortBuf)
		if err == nil {
			t.Fatalf("DecodeDirectFrame accepted truncated buffer of length %d (min %d)!", length, crypto.MinDirectFrameSize)
		}
		if !errors.Is(err, crypto.ErrFrameTooShort) {
			t.Fatalf("Expected ErrFrameTooShort for len %d, got: %v", length, err)
		}
	}

	// --- 2.4 Extreme Sequence and Session ID Round-Tripping ---
	testSequences := []uint64{
		0,
		1,
		1023,
		1024,
		1025,
		math.MaxUint32 - 1,
		math.MaxUint32,
		uint64(math.MaxUint32) + 1,
		math.MaxInt64,
		math.MaxUint64 - 1,
		math.MaxUint64,
	}

	testSessions := []uint32{
		1,
		100,
		65535,
		math.MaxUint32 - 1,
		math.MaxUint32,
	}

	for _, seq := range testSequences {
		for _, sID := range testSessions {
			payload := make([]byte, 128)
			_, _ = rand.Read(payload)
			var tag [16]byte
			_, _ = rand.Read(tag[:])

			orig := &crypto.DirectFrame{
				Magic:             crypto.DirectFrameMagic,
				Version:           crypto.CurrentWireVersion,
				MsgType:           crypto.MsgTypeTransportData,
				SenderSessionID:   sID,
				ReceiverSessionID: sID ^ 0xA5A5A5A5,
				SequenceCounter:   seq,
				Ciphertext:        payload,
				AuthTag:           tag,
			}

			encoded := crypto.EncodeDirectFrame(orig)
			decoded, err := crypto.DecodeDirectFrame(encoded)
			if err != nil {
				t.Fatalf("Failed to decode valid DirectFrame for seq %d, sID %d: %v", seq, sID, err)
			}

			if decoded.Magic != orig.Magic ||
				decoded.Version != orig.Version ||
				decoded.MsgType != orig.MsgType ||
				decoded.SenderSessionID != orig.SenderSessionID ||
				decoded.ReceiverSessionID != orig.ReceiverSessionID ||
				decoded.SequenceCounter != orig.SequenceCounter ||
				!bytes.Equal(decoded.Ciphertext, orig.Ciphertext) ||
				decoded.AuthTag != orig.AuthTag {
				t.Fatalf("DirectFrame corrupted during encode/decode round-trip for seq %d!", seq)
			}
		}
	}

	t.Logf("PASS: SVRN Direct Wire Framing passed all magic, version, boundary, and extreme integer round-trips.")
}

// ============================================================================
// 3. ADVERSARIAL ANTI-REPLAY SLIDING WINDOW DEEP STRESS
// ============================================================================

func TestAdversarialAntiReplaySlidingWindowDeepStress(t *testing.T) {
	window := crypto.NewAntiReplayWindow()

	// --- 3.1 Initial Sequence Zero Support ---
	if !window.Check(0) {
		t.Fatalf("Initial sequence 0 Check failed")
	}
	if !window.CheckAndAdd(0) {
		t.Fatalf("Initial sequence 0 CheckAndAdd failed")
	}
	// Duplicate 0 must fail
	if window.Check(0) {
		t.Fatalf("Duplicate sequence 0 Check succeeded!")
	}
	if window.CheckAndAdd(0) {
		t.Fatalf("Duplicate sequence 0 CheckAndAdd succeeded!")
	}

	// --- 3.2 Exact Window Edge Arithmetic ---
	// Move maxSeq to 1024
	if !window.CheckAndAdd(1024) {
		t.Fatalf("Sequence 1024 CheckAndAdd failed")
	}

	// Sequence 1: diff = 1024 - 1 = 1023 (Inside 1024 window, word 15, bit 63)
	if !window.Check(1) {
		t.Fatalf("Sequence 1 (diff=1023) MUST be inside the 1024 window, but Check returned false!")
	}
	if !window.CheckAndAdd(1) {
		t.Fatalf("Sequence 1 (diff=1023) MUST be accepted into window, but CheckAndAdd returned false!")
	}
	// Duplicate 1 must be rejected
	if window.CheckAndAdd(1) {
		t.Fatalf("Duplicate sequence 1 was accepted!")
	}

	// Sequence 0: diff = 1024 - 0 = 1024 (Outside 1024 window: diff >= 1024)
	if window.Check(0) {
		t.Fatalf("Sequence 0 (diff=1024) MUST be outside the window, but Check returned true!")
	}
	if window.CheckAndAdd(0) {
		t.Fatalf("Sequence 0 (diff=1024) MUST be rejected as too old, but CheckAndAdd returned true!")
	}

	// --- 3.3 Reverse Ingestion of Exactly 1024 Packets ---
	wReverse := crypto.NewAntiReplayWindow()
	baseSeq := uint64(5000)
	if !wReverse.CheckAndAdd(baseSeq) {
		t.Fatalf("Base seq %d failed", baseSeq)
	}

	// Ingest from 4999 down to 3977 (total 1023 packets within window: diff 1 to 1023)
	for s := baseSeq - 1; s >= baseSeq-1023; s-- {
		if !wReverse.Check(s) {
			t.Fatalf("Reverse sequence %d (diff=%d) rejected by Check!", s, baseSeq-s)
		}
		if !wReverse.CheckAndAdd(s) {
			t.Fatalf("Reverse sequence %d (diff=%d) rejected by CheckAndAdd!", s, baseSeq-s)
		}
	}

	// Verify all 1024 sequences are now marked as duplicates
	for s := baseSeq; s >= baseSeq-1023; s-- {
		if wReverse.Check(s) {
			t.Fatalf("Second pass: sequence %d should be duplicate but Check succeeded!", s)
		}
		if wReverse.CheckAndAdd(s) {
			t.Fatalf("Second pass: sequence %d should be duplicate but CheckAndAdd succeeded!", s)
		}
	}

	// Seq baseSeq - 1024 (diff=1024) must be dropped
	if wReverse.CheckAndAdd(baseSeq - 1024) {
		t.Fatalf("Sequence %d (diff=1024) should be dropped as too old!", baseSeq-1024)
	}

	// --- 3.4 Pseudo-Random Shuffled Permutation Ingestion ---
	wShuffled := crypto.NewAntiReplayWindow()
	startSeq := uint64(10000)
	seqCount := 1024

	// Generate sequences [10000 .. 11023]
	seqs := make([]uint64, seqCount)
	for i := 0; i < seqCount; i++ {
		seqs[i] = startSeq + uint64(i)
	}

	// Fisher-Yates Shuffle
	rng := mrand.New(mrand.NewSource(42))
	for i := len(seqs) - 1; i > 0; i-- {
		j := rng.Intn(i + 1)
		seqs[i], seqs[j] = seqs[j], seqs[i]
	}

	// Ingest shuffled sequences
	for idx, s := range seqs {
		if !wShuffled.CheckAndAdd(s) {
			t.Fatalf("Shuffled packet #%d (seq %d) rejected on first ingestion!", idx, s)
		}
	}

	// Ingest all 1024 shuffled sequences again -> MUST ALL BE REJECTED
	for idx, s := range seqs {
		if wShuffled.CheckAndAdd(s) {
			t.Fatalf("Shuffled packet #%d (seq %d) accepted on replay pass!", idx, s)
		}
	}

	// --- 3.5 Massive Forward Jump & Bitmap Clearing ---
	wMega := crypto.NewAntiReplayWindow()
	wMega.CheckAndAdd(100)
	wMega.CheckAndAdd(90)

	megaSeq := uint64(1000000)
	if !wMega.CheckAndAdd(megaSeq) {
		t.Fatalf("Mega forward jump to %d failed", megaSeq)
	}

	// Sequence 100 is now diff = 999900 (far beyond 1024)
	if wMega.CheckAndAdd(100) {
		t.Fatalf("Old sequence 100 accepted after mega forward jump!")
	}
	// Duplicate megaSeq rejected
	if wMega.CheckAndAdd(megaSeq) {
		t.Fatalf("Duplicate megaSeq %d accepted!", megaSeq)
	}
	// megaSeq - 1 is valid (diff = 1)
	if !wMega.CheckAndAdd(megaSeq - 1) {
		t.Fatalf("Sequence %d (diff=1) rejected after mega forward jump!", megaSeq-1)
	}

	// --- 3.6 Extreme 64-bit Sequence Numbers Near MaxUint64 ---
	wExtreme := crypto.NewAntiReplayWindow()
	nearMax := uint64(math.MaxUint64 - 500)
	if !wExtreme.CheckAndAdd(nearMax) {
		t.Fatalf("NearMax seq %d failed", nearMax)
	}
	if !wExtreme.CheckAndAdd(math.MaxUint64) {
		t.Fatalf("MaxUint64 seq failed")
	}
	// diff = MaxUint64 - nearMax = 500 (Inside 1024 window)
	// Duplicate nearMax rejected
	if wExtreme.CheckAndAdd(nearMax) {
		t.Fatalf("Duplicate nearMax accepted!")
	}
	// Untried seq inside window
	midSeq := nearMax + 250
	if !wExtreme.CheckAndAdd(midSeq) {
		t.Fatalf("Mid-range sequence %d failed near MaxUint64 boundary", midSeq)
	}

	// --- 3.7 High Concurrency Race Condition Test ---
	wConcurrent := crypto.NewAntiReplayWindow()
	var acceptedCount int64
	var rejectedCount int64
	var wg sync.WaitGroup

	numGoroutines := 50
	opsPerGoroutine := 1000
	uniqueKeys := 2000

	for g := 0; g < numGoroutines; g++ {
		wg.Add(1)
		go func(gID int) {
			defer wg.Done()
			localRng := mrand.New(mrand.NewSource(int64(gID * 10007)))
			for i := 0; i < opsPerGoroutine; i++ {
				// Pick a random sequence number in [1..2000]
				seq := uint64(localRng.Intn(uniqueKeys) + 1)
				if wConcurrent.CheckAndAdd(seq) {
					atomic.AddInt64(&acceptedCount, 1)
				} else {
					atomic.AddInt64(&rejectedCount, 1)
				}
			}
		}(g)
	}
	wg.Wait()

	totalOps := int64(numGoroutines * opsPerGoroutine)
	if acceptedCount+rejectedCount != totalOps {
		t.Fatalf("Total operations mismatch: got %d, expected %d", acceptedCount+rejectedCount, totalOps)
	}
	if acceptedCount > int64(uniqueKeys) {
		t.Fatalf("Accepted unique sequences (%d) exceeded total possible unique keys (%d)!", acceptedCount, uniqueKeys)
	}

	t.Logf("PASS: Anti-Replay Sliding Window passed exact edges, reverse ingestion (1024), shuffled permutation (1024), mega-jumps, MaxUint64 boundary, and concurrent race (%d ops, %d accepted, %d rejected).",
		totalOps, acceptedCount, rejectedCount)
}

// ============================================================================
// 4. ADVERSARIAL 3-HOP ONION ROUTING & FIXED PADDING STRESS
// ============================================================================

func TestAdversarial3HopOnionRoutingStress(t *testing.T) {
	// --- 4.1 Fixed 1420-Byte Padding Invariant Across Payload Sweep ---
	sweepLengths := []int{0, 1, 2, 3, 7, 15, 31, 63, 127, 255, 511, 1023, 1200, 1300, 1400, 1406}

	for _, pLen := range sweepLengths {
		rawPayload := make([]byte, pLen)
		if pLen > 0 {
			_, _ = rand.Read(rawPayload)
		}

		cell := &routing.OnionCell{
			CircuitID: 9999,
			Command:   routing.CellCmdRelayData,
			StreamID:  777,
			Digest:    0xDEADBEEF,
			Payload:   rawPayload,
		}

		encoded, err := routing.EncodeCell(cell)
		if err != nil {
			t.Fatalf("EncodeCell failed for valid payload length %d: %v", pLen, err)
		}

		if len(encoded) != routing.OnionCellFixedSize {
			t.Fatalf("OnionCellFixedSize VIOLATION! Payload len %d resulted in cell size %d (expected %d)",
				pLen, len(encoded), routing.OnionCellFixedSize)
		}

		decoded, err := routing.DecodeCell(encoded)
		if err != nil {
			t.Fatalf("DecodeCell failed for payload len %d: %v", pLen, err)
		}

		if decoded.CircuitID != cell.CircuitID ||
			decoded.Command != cell.Command ||
			decoded.StreamID != cell.StreamID ||
			decoded.Digest != cell.Digest ||
			!bytes.Equal(decoded.Payload, cell.Payload) {
			t.Fatalf("Decoded OnionCell does not match original for payload length %d!", pLen)
		}
	}

	// --- 4.2 Payload Overflow Boundary Enforcement ---
	overflowLengths := []int{1407, 1408, 1500, 2048, 65535}
	for _, ovLen := range overflowLengths {
		overflowPayload := make([]byte, ovLen)
		cell := &routing.OnionCell{
			CircuitID: 101,
			Command:   routing.CellCmdRelayData,
			StreamID:  1,
			Payload:   overflowPayload,
		}
		_, err := routing.EncodeCell(cell)
		if err == nil {
			t.Fatalf("EncodeCell MUST fail for overflow payload length %d, but succeeded!", ovLen)
		}
		if !errors.Is(err, routing.ErrCellPayloadOverflow) {
			t.Fatalf("Expected ErrCellPayloadOverflow for len %d, got: %v", ovLen, err)
		}
	}

	// --- 4.3 Malformed Cell Length Decoding ---
	badLengths := []int{0, 1, 13, 14, 100, 1419, 1421, 1500}
	for _, bl := range badLengths {
		badBuf := make([]byte, bl)
		_, err := routing.DecodeCell(badBuf)
		if err == nil {
			t.Fatalf("DecodeCell MUST fail for buffer of length %d != 1420!", bl)
		}
		if !errors.Is(err, routing.ErrInvalidCellSize) {
			t.Fatalf("Expected ErrInvalidCellSize for len %d, got: %v", bl, err)
		}
	}

	// --- 4.4 Full 3-Hop Onion Layer Decapsulation & Privacy Isolation ---
	hop0KP, _ := crypto.GenerateKeypair()
	hop1KP, _ := crypto.GenerateKeypair()
	hop2KP, _ := crypto.GenerateKeypair()

	hop0 := &routing.OnionHop{HopIndex: 0, NodeID: "entry-node-0", PublicKey: hop0KP.PublicKey}
	hop1 := &routing.OnionHop{HopIndex: 1, NodeID: "middle-node-1", PublicKey: hop1KP.PublicKey}
	hop2 := &routing.OnionHop{HopIndex: 2, NodeID: "exit-node-2", PublicKey: hop2KP.PublicKey}

	circuitID := uint32(0x55AA1122)
	circuit, err := routing.Build3HopCircuit(circuitID, hop0, hop1, hop2)
	if err != nil {
		t.Fatalf("Build3HopCircuit failed: %v", err)
	}

	targetAddr := "1.1.1.1:443"
	secretData := []byte("DEEP_ADVERSARIAL_ORIGIN_OBFUSCATED_PAYLOAD")

	cellBytes, err := circuit.EncryptLayeredData(42, targetAddr, secretData)
	if err != nil {
		t.Fatalf("EncryptLayeredData failed: %v", err)
	}
	if len(cellBytes) != routing.OnionCellFixedSize {
		t.Fatalf("Final Encrypted Layered Cell size must be exactly %d, got %d", routing.OnionCellFixedSize, len(cellBytes))
	}

	decodedCell, err := routing.DecodeCell(cellBytes)
	if err != nil {
		t.Fatalf("DecodeCell failed: %v", err)
	}

	// Peeling Layer 1 (Entry Hop 0)
	peel1, err := routing.PeelLayer(hop0KP.PrivateKey, 1, decodedCell.Payload)
	if err != nil {
		t.Fatalf("Hop 0 failed to peel Layer 1: %v", err)
	}
	if peel1.IsExit {
		t.Fatalf("Hop 0 must NOT report IsExit=true!")
	}
	if peel1.NextHopPub != hop1KP.PublicKey {
		t.Fatalf("Hop 0 next hop public key mismatch: expected %x, got %x", hop1KP.PublicKey, peel1.NextHopPub)
	}

	// Peeling Layer 2 (Intermediate Hop 1)
	peel2, err := routing.PeelLayer(hop1KP.PrivateKey, 2, peel1.InnerPayload)
	if err != nil {
		t.Fatalf("Hop 1 failed to peel Layer 2: %v", err)
	}
	if peel2.IsExit {
		t.Fatalf("Hop 1 must NOT report IsExit=true!")
	}
	if peel2.NextHopPub != hop2KP.PublicKey {
		t.Fatalf("Hop 1 next hop public key mismatch: expected %x, got %x", hop2KP.PublicKey, peel2.NextHopPub)
	}

	// Peeling Layer 3 (Exit Hop 2)
	peel3, err := routing.PeelLayer(hop2KP.PrivateKey, 3, peel2.InnerPayload)
	if err != nil {
		t.Fatalf("Hop 2 failed to peel Layer 3: %v", err)
	}
	if !peel3.IsExit {
		t.Fatalf("Hop 2 MUST report IsExit=true!")
	}
	if peel3.TargetAddr != targetAddr {
		t.Fatalf("Hop 2 TargetAddr mismatch: expected %s, got %s", targetAddr, peel3.TargetAddr)
	}
	if !bytes.Equal(peel3.InnerPayload, secretData) {
		t.Fatalf("Hop 2 InnerPayload mismatch: expected %q, got %q", secretData, peel3.InnerPayload)
	}

	// --- 4.5 Adversarial Forward Secrecy: Out-of-Order Peeling Resistance ---
	// Hop 1 attempts to peel Layer 1 directly -> MUST FAIL
	_, err = routing.PeelLayer(hop1KP.PrivateKey, 1, decodedCell.Payload)
	if err == nil {
		t.Fatalf("Hop 1 was able to peel Layer 1 without Hop 0 private key! (Forward Secrecy Breach)")
	}

	// Hop 2 attempts to peel Layer 1 directly -> MUST FAIL
	_, err = routing.PeelLayer(hop2KP.PrivateKey, 1, decodedCell.Payload)
	if err == nil {
		t.Fatalf("Hop 2 was able to peel Layer 1 without Hop 0 private key! (Forward Secrecy Breach)")
	}

	// Hop 0 attempts to peel Layer 2 directly -> MUST FAIL
	_, err = routing.PeelLayer(hop0KP.PrivateKey, 2, peel1.InnerPayload)
	if err == nil {
		t.Fatalf("Hop 0 was able to peel Layer 2 without Hop 1 private key! (Privacy Breach)")
	}

	// --- 4.6 Tampered Ciphertext AEAD Integrity at Every Hop ---
	// Tamper Layer 1 payload
	tamperedPayload1 := make([]byte, len(decodedCell.Payload))
	copy(tamperedPayload1, decodedCell.Payload)
	tamperedPayload1[len(tamperedPayload1)-1] ^= 0x01
	_, err = routing.PeelLayer(hop0KP.PrivateKey, 1, tamperedPayload1)
	if err == nil {
		t.Fatalf("Hop 0 accepted tampered Layer 1 ciphertext!")
	}

	// Tamper Layer 2 payload
	tamperedPayload2 := make([]byte, len(peel1.InnerPayload))
	copy(tamperedPayload2, peel1.InnerPayload)
	tamperedPayload2[len(tamperedPayload2)-1] ^= 0x01
	_, err = routing.PeelLayer(hop1KP.PrivateKey, 2, tamperedPayload2)
	if err == nil {
		t.Fatalf("Hop 1 accepted tampered Layer 2 ciphertext!")
	}

	// Tamper Layer 3 payload
	tamperedPayload3 := make([]byte, len(peel2.InnerPayload))
	copy(tamperedPayload3, peel2.InnerPayload)
	tamperedPayload3[len(tamperedPayload3)-1] ^= 0x01
	_, err = routing.PeelLayer(hop2KP.PrivateKey, 3, tamperedPayload3)
	if err == nil {
		t.Fatalf("Hop 2 accepted tampered Layer 3 ciphertext!")
	}

	// --- 4.7 Timing Jitter Distribution Empirical Validation ---
	sampleCount := 5000
	samples := make([]time.Duration, sampleCount)
	var totalJitter time.Duration
	for i := 0; i < sampleCount; i++ {
		j := circuit.ComputeJitterDelay()
		if j < 2*time.Millisecond || j > 20*time.Millisecond {
			t.Fatalf("Jitter delay %v outside expected range [2ms, 20ms]!", j)
		}
		samples[i] = j
		totalJitter += j
	}

	avgJitter := totalJitter / time.Duration(sampleCount)
	if avgJitter < 5*time.Millisecond || avgJitter > 16*time.Millisecond {
		t.Fatalf("Average jitter %v deviated significantly from expected uniform mean (~11ms)", avgJitter)
	}

	t.Logf("PASS: 3-Hop Onion Routing passed fixed 1420B padding invariant, overflow guards, out-of-order peeling barriers, tamper detection at all hops, and timing jitter distribution (avg %v).", avgJitter)
}

// ============================================================================
// 5. ADVERSARIAL DUAL-KEY RATCHET RE-KEYING UNDER LOAD
// ============================================================================

func TestAdversarialDualKeyRatchetRekeyUnderLoad(t *testing.T) {
	initStatic, _ := crypto.GenerateKeypair()
	respStatic, _ := crypto.GenerateKeypair()
	var psk [crypto.KeySize]byte
	_, _ = rand.Read(psk[:])

	// Handshake Session 1
	act1_1, initH1, err := crypto.InitHandshakeAct1(initStatic, respStatic.PublicKey, psk, nil)
	if err != nil {
		t.Fatalf("Act 1 S1 failed: %v", err)
	}
	act2_1, respState1, _, err := crypto.ProcessHandshakeAct1(respStatic, psk, act1_1, nil)
	if err != nil {
		t.Fatalf("Act 2 S1 failed: %v", err)
	}
	initState1, _, err := crypto.ProcessHandshakeAct2(initH1, act2_1)
	if err != nil {
		t.Fatalf("Finalize S1 failed: %v", err)
	}

	initMgr := crypto.NewSessionRatchetManager(initState1, true, initStatic, respStatic.PublicKey, psk)
	respMgr := crypto.NewSessionRatchetManager(respState1, false, respStatic, initStatic.PublicKey, psk)

	// Send 50 packets on Session 1
	for i := 0; i < 50; i++ {
		msg := []byte(fmt.Sprintf("S1_PACKET_NUM_%d", i))
		enc, err := initMgr.EncryptPacket(crypto.MsgTypeTransportData, msg)
		if err != nil {
			t.Fatalf("Encrypt packet S1 #%d failed: %v", i, err)
		}
		dec, msgType, err := respMgr.DecryptPacket(enc)
		if err != nil {
			t.Fatalf("Decrypt packet S1 #%d failed: %v", i, err)
		}
		if msgType != crypto.MsgTypeTransportData || !bytes.Equal(dec, msg) {
			t.Fatalf("Decrypted message mismatch on S1 #%d!", i)
		}
	}

	// Prepare buffered in-flight packets on Session 1 before rekeying
	inFlightCount := 10
	inFlightPackets := make([][]byte, inFlightCount)
	inFlightPlaintexts := make([][]byte, inFlightCount)
	for i := 0; i < inFlightCount; i++ {
		inFlightPlaintexts[i] = []byte(fmt.Sprintf("IN_FLIGHT_S1_PACKET_%d", i))
		enc, err := initMgr.EncryptPacket(crypto.MsgTypeTransportData, inFlightPlaintexts[i])
		if err != nil {
			t.Fatalf("In-flight encrypt failed: %v", err)
		}
		inFlightPackets[i] = enc
	}

	// Re-key: Negotiate Session 2
	act1_2, initH2, err := crypto.InitHandshakeAct1(initStatic, respStatic.PublicKey, psk, nil)
	if err != nil {
		t.Fatalf("Act 1 S2 failed: %v", err)
	}
	act2_2, respState2, _, err := crypto.ProcessHandshakeAct1(respStatic, psk, act1_2, nil)
	if err != nil {
		t.Fatalf("Act 2 S2 failed: %v", err)
	}
	initState2, _, err := crypto.ProcessHandshakeAct2(initH2, act2_2)
	if err != nil {
		t.Fatalf("Finalize S2 failed: %v", err)
	}

	// Rotate keys on both sides
	initMgr.RotateKeys(initState2)
	respMgr.RotateKeys(respState2)

	// Send 50 packets on Session 2
	for i := 0; i < 50; i++ {
		msg := []byte(fmt.Sprintf("S2_PACKET_NUM_%d", i))
		enc, err := initMgr.EncryptPacket(crypto.MsgTypeTransportData, msg)
		if err != nil {
			t.Fatalf("Encrypt packet S2 #%d failed: %v", i, err)
		}
		dec, msgType, err := respMgr.DecryptPacket(enc)
		if err != nil {
			t.Fatalf("Decrypt packet S2 #%d failed: %v", i, err)
		}
		if msgType != crypto.MsgTypeTransportData || !bytes.Equal(dec, msg) {
			t.Fatalf("Decrypted message mismatch on S2 #%d!", i)
		}
	}

	// Now deliver the delayed in-flight packets from Session 1 during the dual-key grace period
	for i := 0; i < inFlightCount; i++ {
		dec, _, err := respMgr.DecryptPacket(inFlightPackets[i])
		if err != nil {
			t.Fatalf("DualKeyGracePeriod failed to decrypt in-flight packet #%d: %v", i, err)
		}
		if !bytes.Equal(dec, inFlightPlaintexts[i]) {
			t.Fatalf("In-flight plaintext mismatch on packet #%d!", i)
		}
	}

	// Attempt to replay the in-flight Session 1 packets -> MUST FAIL
	for i := 0; i < inFlightCount; i++ {
		_, _, err := respMgr.DecryptPacket(inFlightPackets[i])
		if err == nil {
			t.Fatalf("DualKeyGracePeriod permitted replay of in-flight packet #%d!", i)
		}
		if !errors.Is(err, crypto.ErrReplayDetected) {
			t.Fatalf("Expected ErrReplayDetected on in-flight replay #%d, got: %v", i, err)
		}
	}

	// Close session and verify wipe
	initMgr.Close()
	respMgr.Close()

	_, err = initMgr.EncryptPacket(crypto.MsgTypeTransportData, []byte("POST_CLOSE"))
	if err == nil || !errors.Is(err, crypto.ErrSessionClosed) {
		t.Fatalf("EncryptPacket after Close MUST fail with ErrSessionClosed, got: %v", err)
	}

	t.Logf("PASS: Dual-key ratchet re-keying successfully handled interleaved in-flight packets across sessions with zero anti-replay collisions.")
}
