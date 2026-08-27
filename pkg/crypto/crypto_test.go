package crypto

import (
	"bytes"
	"crypto/rand"
	"testing"
)

func TestKeypairAndDH(t *testing.T) {
	aliceKP, err := GenerateKeypair()
	if err != nil {
		t.Fatalf("GenerateKeypair alice failed: %v", err)
	}

	bobKP, err := GenerateKeypair()
	if err != nil {
		t.Fatalf("GenerateKeypair bob failed: %v", err)
	}

	dhAlice, err := DH(aliceKP.PrivateKey, bobKP.PublicKey)
	if err != nil {
		t.Fatalf("DH alice failed: %v", err)
	}

	dhBob, err := DH(bobKP.PrivateKey, aliceKP.PublicKey)
	if err != nil {
		t.Fatalf("DH bob failed: %v", err)
	}

	if !bytes.Equal(dhAlice[:], dhBob[:]) {
		t.Fatalf("DH shared secrets do not match! Alice: %x, Bob: %x", dhAlice, dhBob)
	}
}

func TestChaCha20Poly1305AEAD(t *testing.T) {
	var key [KeySize]byte
	rand.Read(key[:])

	nonce := ConstructNonce(42)
	plaintext := []byte("SovereignProxy-v4-SecretPayload")
	ad := []byte("context-authenticated-data")

	sealed, err := ChaCha20Poly1305Seal(key, nonce, plaintext, ad)
	if err != nil {
		t.Fatalf("Seal failed: %v", err)
	}

	opened, err := ChaCha20Poly1305Open(key, nonce, sealed, ad)
	if err != nil {
		t.Fatalf("Open failed: %v", err)
	}

	if !bytes.Equal(opened, plaintext) {
		t.Fatalf("Plaintext mismatch: got %s, expected %s", string(opened), string(plaintext))
	}

	// Corrupted ciphertext test
	corrupted := append([]byte(nil), sealed...)
	corrupted[0] ^= 0xFF
	_, err = ChaCha20Poly1305Open(key, nonce, corrupted, ad)
	if err == nil {
		t.Fatalf("Open should fail with corrupted ciphertext!")
	}
}

func TestAntiReplaySlidingWindow(t *testing.T) {
	window := NewAntiReplayWindow()

	// Initial packet
	if !window.CheckAndAdd(100) {
		t.Fatalf("Packet 100 should be accepted")
	}

	// Duplicate packet
	if window.CheckAndAdd(100) {
		t.Fatalf("Duplicate packet 100 should be rejected")
	}

	// In-window out-of-order packets
	if !window.CheckAndAdd(90) {
		t.Fatalf("Packet 90 should be accepted")
	}
	if window.CheckAndAdd(90) {
		t.Fatalf("Duplicate packet 90 should be rejected")
	}
	if !window.CheckAndAdd(50) {
		t.Fatalf("Packet 50 should be accepted")
	}

	// Ahead of window
	if !window.CheckAndAdd(500) {
		t.Fatalf("Packet 500 should be accepted")
	}

	// Valid in current window (500 - 100 = 400 < 1024)
	if !window.CheckAndAdd(450) {
		t.Fatalf("Packet 450 should be accepted")
	}

	// Massive leap forward
	if !window.CheckAndAdd(5000) {
		t.Fatalf("Packet 5000 should be accepted")
	}

	// Old packet outside 1024 window (5000 - 1024 = 3976)
	if window.CheckAndAdd(3900) {
		t.Fatalf("Packet 3900 should be rejected as too old")
	}

	// Valid recent packet
	if !window.CheckAndAdd(4500) {
		t.Fatalf("Packet 4500 should be accepted")
	}
}

func TestNoiseIKpsk2Handshake(t *testing.T) {
	aliceStatic, err := GenerateKeypair()
	if err != nil {
		t.Fatalf("GenerateKeypair Alice failed: %v", err)
	}

	bobStatic, err := GenerateKeypair()
	if err != nil {
		t.Fatalf("GenerateKeypair Bob failed: %v", err)
	}

	var psk [KeySize]byte
	rand.Read(psk[:])

	payload0RTT := []byte("0-RTT-Alice-Hello-World")
	payloadAct2 := []byte("Act2-Bob-Welcome-Cookie")

	// Act 1: Alice -> Bob
	act1Pkt, initState, err := InitHandshakeAct1(aliceStatic, bobStatic.PublicKey, psk, payload0RTT)
	if err != nil {
		t.Fatalf("InitHandshakeAct1 failed: %v", err)
	}

	// Bob processes Act 1 and generates Act 2
	act2Pkt, bobTransport, decrypted0RTT, err := ProcessHandshakeAct1(bobStatic, psk, act1Pkt, payloadAct2)
	if err != nil {
		t.Fatalf("ProcessHandshakeAct1 failed: %v", err)
	}

	if !bytes.Equal(decrypted0RTT, payload0RTT) {
		t.Fatalf("0-RTT payload mismatch: got %s, expected %s", string(decrypted0RTT), string(payload0RTT))
	}

	// Alice processes Act 2
	aliceTransport, decryptedAct2, err := ProcessHandshakeAct2(initState, act2Pkt)
	if err != nil {
		t.Fatalf("ProcessHandshakeAct2 failed: %v", err)
	}

	if !bytes.Equal(decryptedAct2, payloadAct2) {
		t.Fatalf("Act 2 payload mismatch: got %s, expected %s", string(decryptedAct2), string(payloadAct2))
	}

	// Verify key synchronization: Alice.SendKey == Bob.RecvKey and Alice.RecvKey == Bob.SendKey
	if !bytes.Equal(aliceTransport.SendKey[:], bobTransport.RecvKey[:]) {
		t.Fatalf("Alice SendKey != Bob RecvKey")
	}
	if !bytes.Equal(aliceTransport.RecvKey[:], bobTransport.SendKey[:]) {
		t.Fatalf("Alice RecvKey != Bob SendKey")
	}
}

func TestDirectFrameAndRatchet(t *testing.T) {
	aliceStatic, _ := GenerateKeypair()
	bobStatic, _ := GenerateKeypair()
	var psk [KeySize]byte

	act1Pkt, initState, _ := InitHandshakeAct1(aliceStatic, bobStatic.PublicKey, psk, []byte("init"))
	act2Pkt, bobTransport, _, _ := ProcessHandshakeAct1(bobStatic, psk, act1Pkt, []byte("ack"))
	aliceTransport, _, _ := ProcessHandshakeAct2(initState, act2Pkt)

	aliceRatchet := NewSessionRatchetManager(aliceTransport, true, aliceStatic, bobStatic.PublicKey, psk)
	bobRatchet := NewSessionRatchetManager(bobTransport, false, bobStatic, aliceStatic.PublicKey, psk)

	defer aliceRatchet.Close()
	defer bobRatchet.Close()

	// Alice sends message to Bob
	msg1 := []byte("Secret Mesh Transport Data: Alice to Bob")
	encryptedFrame, err := aliceRatchet.EncryptPacket(MsgTypeTransportData, msg1)
	if err != nil {
		t.Fatalf("Alice EncryptPacket failed: %v", err)
	}

	decrypted, msgType, err := bobRatchet.DecryptPacket(encryptedFrame)
	if err != nil {
		t.Fatalf("Bob DecryptPacket failed: %v", err)
	}

	if msgType != MsgTypeTransportData {
		t.Fatalf("Expected MsgTypeTransportData, got %d", msgType)
	}
	if !bytes.Equal(decrypted, msg1) {
		t.Fatalf("Decrypted payload mismatch: got %s, expected %s", string(decrypted), string(msg1))
	}

	// Replay attack test on Bob
	_, _, err = bobRatchet.DecryptPacket(encryptedFrame)
	if err == nil {
		t.Fatalf("Replaying same frame to Bob should fail anti-replay window")
	}

	// Bob replies to Alice
	msg2 := []byte("Response from Bob to Alice")
	encryptedFrame2, err := bobRatchet.EncryptPacket(MsgTypeTransportData, msg2)
	if err != nil {
		t.Fatalf("Bob EncryptPacket failed: %v", err)
	}

	decrypted2, msgType2, err := aliceRatchet.DecryptPacket(encryptedFrame2)
	if err != nil {
		t.Fatalf("Alice DecryptPacket failed: %v", err)
	}

	if msgType2 != MsgTypeTransportData {
		t.Fatalf("Expected MsgTypeTransportData, got %d", msgType2)
	}
	if !bytes.Equal(decrypted2, msg2) {
		t.Fatalf("Decrypted reply payload mismatch: got %s, expected %s", string(decrypted2), string(msg2))
	}
}

func TestDualKeyGracePeriodRekey(t *testing.T) {
	aliceStatic, _ := GenerateKeypair()
	bobStatic, _ := GenerateKeypair()
	var psk [KeySize]byte

	// Establish session 1
	act1Pkt, initState, _ := InitHandshakeAct1(aliceStatic, bobStatic.PublicKey, psk, []byte("init1"))
	act2Pkt, bobTransport1, _, _ := ProcessHandshakeAct1(bobStatic, psk, act1Pkt, []byte("ack1"))
	aliceTransport1, _, _ := ProcessHandshakeAct2(initState, act2Pkt)

	aliceRatchet := NewSessionRatchetManager(aliceTransport1, true, aliceStatic, bobStatic.PublicKey, psk)
	bobRatchet := NewSessionRatchetManager(bobTransport1, false, bobStatic, aliceStatic.PublicKey, psk)
	defer aliceRatchet.Close()
	defer bobRatchet.Close()

	// Alice prepares a packet encrypted under Session 1
	pktInFlight, err := aliceRatchet.EncryptPacket(MsgTypeTransportData, []byte("In-flight packet"))
	if err != nil {
		t.Fatalf("Encrypt failed: %v", err)
	}

	// Establish session 2 (Rekey)
	act1Pkt2, initState2, _ := InitHandshakeAct1(aliceStatic, bobStatic.PublicKey, psk, []byte("init2"))
	act2Pkt2, bobTransport2, _, _ := ProcessHandshakeAct1(bobStatic, psk, act1Pkt2, []byte("ack2"))
	aliceTransport2, _, _ := ProcessHandshakeAct2(initState2, act2Pkt2)

	// Rotate keys on both sides
	aliceRatchet.RotateKeys(aliceTransport2)
	bobRatchet.RotateKeys(bobTransport2)

	// Bob receives the in-flight packet encrypted with session 1 key within grace period
	decrypted, _, err := bobRatchet.DecryptPacket(pktInFlight)
	if err != nil {
		t.Fatalf("Bob failed to decrypt in-flight packet during grace period: %v", err)
	}
	if string(decrypted) != "In-flight packet" {
		t.Fatalf("Decrypted in-flight payload mismatch: %s", string(decrypted))
	}

	// Verify that the new session's packet with Seq 0 is also decrypted successfully
	pktNewSession, err := aliceRatchet.EncryptPacket(MsgTypeTransportData, []byte("New session packet 0"))
	if err != nil {
		t.Fatalf("Alice EncryptPacket failed for new session: %v", err)
	}

	decryptedNew, _, err := bobRatchet.DecryptPacket(pktNewSession)
	if err != nil {
		t.Fatalf("Bob failed to decrypt new session packet 0 after in-flight packet: %v", err)
	}
	if string(decryptedNew) != "New session packet 0" {
		t.Fatalf("Decrypted new session payload mismatch: %s", string(decryptedNew))
	}
}

func TestAntiReplayIsolationAcrossRekeyAndMacFailure(t *testing.T) {
	aliceStatic, _ := GenerateKeypair()
	bobStatic, _ := GenerateKeypair()
	var psk [KeySize]byte

	act1Pkt, initState, _ := InitHandshakeAct1(aliceStatic, bobStatic.PublicKey, psk, []byte("init"))
	act2Pkt, bobTransport, _, _ := ProcessHandshakeAct1(bobStatic, psk, act1Pkt, []byte("ack"))
	aliceTransport, _, _ := ProcessHandshakeAct2(initState, act2Pkt)

	aliceRatchet := NewSessionRatchetManager(aliceTransport, true, aliceStatic, bobStatic.PublicKey, psk)
	bobRatchet := NewSessionRatchetManager(bobTransport, false, bobStatic, aliceStatic.PublicKey, psk)
	defer aliceRatchet.Close()
	defer bobRatchet.Close()

	// 1. Create a corrupted packet with Seq 0
	corruptedFrame, err := aliceRatchet.EncryptPacket(MsgTypeTransportData, []byte("Tampered data"))
	if err != nil {
		t.Fatalf("Encrypt failed: %v", err)
	}
	corruptedFrame[len(corruptedFrame)-1] ^= 0xFF // Corrupt tag

	// Bob attempts to decrypt corrupted packet -> should fail MAC verification
	_, _, err = bobRatchet.DecryptPacket(corruptedFrame)
	if err == nil {
		t.Fatalf("Corrupted packet should fail decryption")
	}

	// 2. Now send valid packet with Seq 1
	validPkt1, err := aliceRatchet.EncryptPacket(MsgTypeTransportData, []byte("Valid packet 1"))
	if err != nil {
		t.Fatalf("Encrypt failed: %v", err)
	}

	dec, _, err := bobRatchet.DecryptPacket(validPkt1)
	if err != nil {
		t.Fatalf("Valid packet 1 was rejected after MAC failure: %v", err)
	}
	if string(dec) != "Valid packet 1" {
		t.Fatalf("Decrypted payload mismatch: %s", string(dec))
	}

	// 3. Replaying valid packet 1 must fail
	_, _, err = bobRatchet.DecryptPacket(validPkt1)
	if err == nil {
		t.Fatalf("Replayed packet 1 should have been rejected")
	}
}
