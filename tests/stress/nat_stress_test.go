package stress

import (
	"bytes"
	"context"
	"crypto/rand"
	"fmt"
	"net"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/sovereign/proxy/v4/pkg/derp"
	"github.com/sovereign/proxy/v4/pkg/nat"
)

type mockDerpSession struct {
	mu     sync.Mutex
	pubKey [derp.PubKeySize]byte
	ch     chan *derp.Frame
	closed bool
}

func (s *mockDerpSession) SendFrame(frame *derp.Frame) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.closed {
		return fmt.Errorf("session closed")
	}
	select {
	case s.ch <- frame:
		return nil
	default:
		return fmt.Errorf("channel full")
	}
}

func (s *mockDerpSession) PublicKey() [derp.PubKeySize]byte {
	return s.pubKey
}

func (s *mockDerpSession) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.closed = true
	return nil
}

// TestDERPConcurrentRelayThroughput tests high-concurrency packet routing in DERP router.
func TestDERPConcurrentRelayThroughput(t *testing.T) {
	router := derp.NewRouter()

	const numPairs = 100
	const packetsPerPair = 200

	type clientPair struct {
		aliceSess *mockDerpSession
		bobSess   *mockDerpSession
	}

	pairs := make([]clientPair, numPairs)
	for i := 0; i < numPairs; i++ {
		var aPub, bPub [derp.PubKeySize]byte
		rand.Read(aPub[:])
		rand.Read(bPub[:])

		aSess := &mockDerpSession{
			pubKey: aPub,
			ch:     make(chan *derp.Frame, packetsPerPair*4),
		}
		bSess := &mockDerpSession{
			pubKey: bPub,
			ch:     make(chan *derp.Frame, packetsPerPair*4),
		}

		router.Register(aSess)
		router.Register(bSess)

		pairs[i] = clientPair{
			aliceSess: aSess,
			bobSess:   bSess,
		}
	}

	if router.ActiveSessionsCount() != numPairs*2 {
		t.Fatalf("Expected %d active sessions, got %d", numPairs*2, router.ActiveSessionsCount())
	}

	var wg sync.WaitGroup
	var totalSent int64
	var totalReceived int64

	start := time.Now()

	// Launch sender workers
	for i := 0; i < numPairs; i++ {
		wg.Add(2)

		// Alice -> Bob
		go func(p clientPair, pairIdx int) {
			defer wg.Done()
			for k := 0; k < packetsPerPair; k++ {
				payload := []byte(fmt.Sprintf("Payload-A-to-B-pair%d-seq%d", pairIdx, k))
				err := router.RouteForward(p.aliceSess.PublicKey(), p.bobSess.PublicKey(), payload)
				if err == nil {
					atomic.AddInt64(&totalSent, 1)
				}
			}
		}(pairs[i], i)

		// Bob -> Alice
		go func(p clientPair, pairIdx int) {
			defer wg.Done()
			for k := 0; k < packetsPerPair; k++ {
				payload := []byte(fmt.Sprintf("Payload-B-to-A-pair%d-seq%d", pairIdx, k))
				err := router.RouteForward(p.bobSess.PublicKey(), p.aliceSess.PublicKey(), payload)
				if err == nil {
					atomic.AddInt64(&totalSent, 1)
				}
			}
		}(pairs[i], i)
	}

	// Drain receivers in background
	drainDone := make(chan struct{})
	go func() {
		var rxWg sync.WaitGroup
		for i := 0; i < numPairs; i++ {
			rxWg.Add(2)
			go func(p clientPair) {
				defer rxWg.Done()
				for k := 0; k < packetsPerPair; k++ {
					select {
					case frame := <-p.bobSess.ch:
						if frame != nil && len(frame.Payload) > 0 {
							atomic.AddInt64(&totalReceived, 1)
						}
					case <-time.After(2 * time.Second):
						return
					}
				}
			}(pairs[i])

			go func(p clientPair) {
				defer rxWg.Done()
				for k := 0; k < packetsPerPair; k++ {
					select {
					case frame := <-p.aliceSess.ch:
						if frame != nil && len(frame.Payload) > 0 {
							atomic.AddInt64(&totalReceived, 1)
						}
					case <-time.After(2 * time.Second):
						return
					}
				}
			}(pairs[i])
		}
		rxWg.Wait()
		close(drainDone)
	}()

	wg.Wait()
	select {
	case <-drainDone:
	case <-time.After(3 * time.Second):
		t.Fatalf("Timeout waiting for DERP receiver drain")
	}

	duration := time.Since(start)
	expectedTotal := int64(numPairs * packetsPerPair * 2)
	throughput := float64(totalReceived) / duration.Seconds()
	routed, dropped := router.Metrics()

	t.Logf("DERP Router Throughput: %d/%d frames received in %v (%.2f frames/sec, Routed: %d, Dropped: %d)",
		totalReceived, expectedTotal, duration, throughput, routed, dropped)

	if totalReceived != expectedTotal {
		t.Fatalf("DERP frame drop: expected %d frames, received %d", expectedTotal, totalReceived)
	}
	if dropped > 0 {
		t.Fatalf("Expected 0 dropped frames, got %d", dropped)
	}
}

// TestSymmetricNATRandomPortAndDERPFallback tests NAT traversal strategy selection and DERP fallback.
func TestSymmetricNATRandomPortAndDERPFallback(t *testing.T) {
	// Node A: Symmetric NAT (Random port mapping)
	localDesc := &nat.NATDescriptor{
		Type:         nat.NATTypeSymmetric,
		PublicAddr1:  &net.UDPAddr{IP: net.ParseIP("198.51.100.10"), Port: 41234},
		PublicAddr2:  &net.UDPAddr{IP: net.ParseIP("198.51.100.10"), Port: 48991},
		IsSequential: false,
		PortDelta:    0,
	}

	// Node B: Symmetric NAT (Random port mapping)
	remoteDesc := &nat.NATDescriptor{
		Type:         nat.NATTypeSymmetric,
		PublicAddr1:  &net.UDPAddr{IP: net.ParseIP("203.0.113.50"), Port: 37812},
		PublicAddr2:  &net.UDPAddr{IP: net.ParseIP("203.0.113.50"), Port: 52109},
		IsSequential: false,
		PortDelta:    0,
	}

	// Strategy selection
	strat := nat.SelectStrategy(localDesc, remoteDesc)
	if strat != nat.StrategyBirthdaySpray && strat != nat.StrategyDERPFallback {
		t.Fatalf("Expected BirthdaySpray or DERPFallback for Symmetric-Symmetric, got %s", strat)
	}

	// Measure fallback transition timing
	start := time.Now()
	laddr, _ := net.ResolveUDPAddr("udp4", "127.0.0.1:0")
	conn, err := net.ListenUDP("udp4", laddr)
	if err != nil {
		t.Fatalf("Failed to listen UDP: %v", err)
	}
	defer conn.Close()

	coord := nat.NewDiscoCoordinator([]string{"127.0.0.1:3478"}, conn)
	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()

	_, finalStrat, err := coord.PunchHole(ctx, remoteDesc)
	transitionDuration := time.Since(start)

	t.Logf("Symmetric NAT Traversal attempt resolved to strategy '%s' in %v (Err: %v)",
		finalStrat, transitionDuration, err)

	if finalStrat != nat.StrategyDERPFallback {
		t.Fatalf("Expected final strategy to be DERP_FALLBACK on failed punch, got %s", finalStrat)
	}
}

// TestSequentialPredictionHolePunching verifies sequential symmetric port prediction strategy.
func TestSequentialPredictionHolePunching(t *testing.T) {
	// Node A: Full Cone NAT
	localDesc := &nat.NATDescriptor{
		Type:         nat.NATTypeFullCone,
		PublicAddr1:  &net.UDPAddr{IP: net.ParseIP("198.51.100.10"), Port: 41234},
		PublicAddr2:  &net.UDPAddr{IP: net.ParseIP("198.51.100.10"), Port: 41234},
		IsSequential: false,
	}

	// Node B: Symmetric NAT with sequential delta (+2)
	remoteDesc := &nat.NATDescriptor{
		Type:         nat.NATTypeSymmetric,
		PublicAddr1:  &net.UDPAddr{IP: net.ParseIP("203.0.113.50"), Port: 40000},
		PublicAddr2:  &net.UDPAddr{IP: net.ParseIP("203.0.113.50"), Port: 40002},
		IsSequential: true,
		PortDelta:    2,
	}

	strat := nat.SelectStrategy(localDesc, remoteDesc)
	if strat != nat.StrategySequentialPrediction {
		t.Fatalf("Expected StrategySequentialPrediction, got %s", strat)
	}
	t.Logf("Sequential NAT strategy correctly selected: %s", strat)
}

// TestSTUNBindingHighLoad tests STUN message encoding and reflection under load.
func TestSTUNBindingHighLoad(t *testing.T) {
	const count = 10000
	var validEncodes int

	start := time.Now()
	for i := 0; i < count; i++ {
		msg, err := nat.NewSTUNBindingRequest()
		if err != nil {
			t.Fatalf("NewSTUNBindingRequest error: %v", err)
		}
		raw := msg.Encode()
		decoded, err := nat.DecodeSTUN(raw)
		if err != nil {
			t.Fatalf("Decode error: %v", err)
		}
		if !bytes.Equal(decoded.TransactionID[:], msg.TransactionID[:]) {
			t.Fatalf("Transaction ID mismatch")
		}
		validEncodes++
	}
	dur := time.Since(start)
	t.Logf("STUN High Load: %d messages encoded/decoded in %v (%.2f msgs/sec)",
		validEncodes, dur, float64(validEncodes)/dur.Seconds())
}
