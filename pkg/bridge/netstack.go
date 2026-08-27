package bridge

import (
	"context"
	"fmt"
	"io"
	"net"
	"strconv"
	"sync"
	"sync/atomic"
	"time"
)

// NetstackBridge coordinates userspace sandboxed outbound dialing and stream piping
type NetstackBridge struct {
	mu            sync.RWMutex
	policy        *SandboxPolicyEngine
	resolver      *DoHResolver
	guardian      *Guardian
	activeStreams int64
	bytesSent     uint64
	bytesRecv     uint64
	dialer        *net.Dialer
}

// NewNetstackBridge initializes a new sandboxed userspace bridge
func NewNetstackBridge(policy *SandboxPolicyEngine, resolver *DoHResolver, guardian *Guardian) *NetstackBridge {
	if policy == nil {
		policy = NewSandboxPolicyEngine(SandboxPolicyConfig{})
	}
	if resolver == nil {
		resolver = NewDoHResolver(nil)
	}
	if guardian == nil {
		guardian = NewGuardian(0)
	}

	return &NetstackBridge{
		policy:   policy,
		resolver: resolver,
		guardian: guardian,
		dialer: &net.Dialer{
			Timeout:   10 * time.Second,
			KeepAlive: 30 * time.Second,
		},
	}
}

// DialAndPipe forwards traffic from an inbound client connection to a destination host:port
func (b *NetstackBridge) DialAndPipe(ctx context.Context, clientConn net.Conn, targetHost string, targetPort int) error {
	defer clientConn.Close()

	// 1. Guardian check
	if b.guardian.IsSuspended() {
		return ErrEgressNotPermitted
	}

	// 2. Resolve target IP via Anti-Leak DoH Resolver
	ips, err := b.resolver.ResolveIPs(ctx, targetHost)
	if err != nil {
		return fmt.Errorf("DNS resolution failed for %s: %w", targetHost, err)
	}

	if len(ips) == 0 {
		return fmt.Errorf("no IP addresses found for %s", targetHost)
	}

	targetIP := ips[0]

	// 3. Validate sandbox policy (Bogon IP, blocked ports, battery)
	batPct, onBat, _, _ := b.guardian.Status()
	if err := b.policy.ValidateEgress(targetIP, targetPort, batPct, onBat); err != nil {
		return err
	}

	// 4. Dial destination
	targetAddr := net.JoinHostPort(targetIP.String(), strconv.Itoa(targetPort))
	outboundConn, err := b.dialer.DialContext(ctx, "tcp", targetAddr)
	if err != nil {
		return fmt.Errorf("outbound dial to %s failed: %w", targetAddr, err)
	}
	defer outboundConn.Close()

	atomic.AddInt64(&b.activeStreams, 1)
	defer atomic.AddInt64(&b.activeStreams, -1)

	// 5. Bidirectional copy
	errCh := make(chan error, 2)

	go func() {
		n, err := io.Copy(outboundConn, clientConn)
		atomic.AddUint64(&b.bytesSent, uint64(n))
		b.guardian.RecordTransfer(uint64(n))
		errCh <- err
	}()

	go func() {
		n, err := io.Copy(clientConn, outboundConn)
		atomic.AddUint64(&b.bytesRecv, uint64(n))
		b.guardian.RecordTransfer(uint64(n))
		errCh <- err
	}()

	// Wait for one stream direction to complete or error
	select {
	case <-errCh:
	case <-ctx.Done():
		return ctx.Err()
	}

	return nil
}

// Stats returns stream counts and byte metrics
func (b *NetstackBridge) Stats() (active int64, tx uint64, rx uint64) {
	return atomic.LoadInt64(&b.activeStreams), atomic.LoadUint64(&b.bytesSent), atomic.LoadUint64(&b.bytesRecv)
}
