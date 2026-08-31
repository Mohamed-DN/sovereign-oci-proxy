package main

import (
	"math"
	"net"
	"sync"
	"time"
)

// tokenBucket represents an individual rate-limiting bucket.
type tokenBucket struct {
	tokens     float64
	capacity   float64
	refillRate float64 // tokens per second
	lastRefill time.Time
}

func newTokenBucket(capacity float64, refillRate float64) *tokenBucket {
	return &tokenBucket{
		tokens:     capacity,
		capacity:   capacity,
		refillRate: refillRate,
		lastRefill: time.Now(),
	}
}

func (tb *tokenBucket) allow(cost float64) bool {
	now := time.Now()
	elapsed := now.Sub(tb.lastRefill).Seconds()
	tb.lastRefill = now

	tb.tokens = math.Min(tb.capacity, tb.tokens+(elapsed*tb.refillRate))
	if tb.tokens >= cost {
		tb.tokens -= cost
		return true
	}
	return false
}

// DualTokenBucketLimiter implements rate limiting per IP and per /24 subnet.
type DualTokenBucketLimiter struct {
	mu           sync.Mutex
	ipBuckets    map[string]*tokenBucket
	subnetBucket map[string]*tokenBucket

	ipCap        float64
	ipRefill     float64
	subnetCap    float64
	subnetRefill float64

	stopChan chan struct{}
}

// NewDualTokenBucketLimiter creates a new DualTokenBucketLimiter.
func NewDualTokenBucketLimiter(ipCap int, ipRefill float64, subnetCap int, subnetRefill float64) *DualTokenBucketLimiter {
	limiter := &DualTokenBucketLimiter{
		ipBuckets:    make(map[string]*tokenBucket),
		subnetBucket: make(map[string]*tokenBucket),
		ipCap:        float64(ipCap),
		ipRefill:     ipRefill,
		subnetCap:    float64(subnetCap),
		subnetRefill: subnetRefill,
		stopChan:     make(chan struct{}),
	}

	// Start periodic cleanup of stale buckets
	go limiter.cleanupLoop()

	return limiter
}

// Allow checks if the given IP is allowed to proceed under both IP and subnet rate limits.
func (l *DualTokenBucketLimiter) Allow(ip net.IP) bool {
	if ip == nil {
		return false
	}

	l.mu.Lock()
	defer l.mu.Unlock()

	ipStr := ip.String()
	subnetStr := getSubnet24Key(ip)

	// Check IP bucket
	tbIP, exists := l.ipBuckets[ipStr]
	if !exists {
		tbIP = newTokenBucket(l.ipCap, l.ipRefill)
		l.ipBuckets[ipStr] = tbIP
	}

	// Check Subnet bucket
	tbSubnet, existsSubnet := l.subnetBucket[subnetStr]
	if !existsSubnet {
		tbSubnet = newTokenBucket(l.subnetCap, l.subnetRefill)
		l.subnetBucket[subnetStr] = tbSubnet
	}

	// Both must allow
	if tbIP.allow(1.0) && tbSubnet.allow(1.0) {
		return true
	}

	return false
}

func getSubnet24Key(ip net.IP) string {
	ipv4 := ip.To4()
	if ipv4 != nil {
		return net.IPv4(ipv4[0], ipv4[1], ipv4[2], 0).String() + "/24"
	}
	// For IPv6, use /48
	ipv6 := ip.To16()
	if ipv6 != nil {
		var mask net.IPMask = net.CIDRMask(48, 128)
		return ip.Mask(mask).String() + "/48"
	}
	return "unknown"
}

func (l *DualTokenBucketLimiter) cleanupLoop() {
	ticker := time.NewTicker(10 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-l.stopChan:
			return
		case now := <-ticker.C:
			l.mu.Lock()
			cutoff := now.Add(-30 * time.Minute)
			for k, tb := range l.ipBuckets {
				if tb.lastRefill.Before(cutoff) && tb.tokens >= tb.capacity {
					delete(l.ipBuckets, k)
				}
			}
			for k, tb := range l.subnetBucket {
				if tb.lastRefill.Before(cutoff) && tb.tokens >= tb.capacity {
					delete(l.subnetBucket, k)
				}
			}
			l.mu.Unlock()
		}
	}
}

// Close stops background maintenance routines.
func (l *DualTokenBucketLimiter) Close() {
	select {
	case <-l.stopChan:
	default:
		close(l.stopChan)
	}
}
