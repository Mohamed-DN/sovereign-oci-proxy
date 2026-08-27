package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"sync"
	"time"
)

var honeypotBanner = []byte("HTTP/1.1 200 OK\r\nServer: nginx/1.26.1\r\nDate: " + time.Now().Format(time.RFC1123) + "\r\nContent-Type: text/html\r\nContent-Length: 52\r\nConnection: close\r\n\r\n<html><body><h1>System Operational</h1></body></html>\r\n")

// SecurityDaemon coordinates honeypot listeners, threat scoring, rate limiting, and firewall execution.
type SecurityDaemon struct {
	config    *Config
	whitelist *WhitelistManager
	limiter   *DualTokenBucketLimiter
	scorer    *ThreatScorer
	firewall  FirewallDriver
	notifier  *NotificationPool

	listener net.Listener
	wg       sync.WaitGroup
	ctx      context.Context
	cancel   context.CancelFunc
}

// NewSecurityDaemon initializes the daemon and all sub-components.
func NewSecurityDaemon(cfg *Config) (*SecurityDaemon, error) {
	wm, err := NewWhitelistManager(cfg.WhitelistedCIDRs)
	if err != nil {
		return nil, fmt.Errorf("failed to init whitelist: %w", err)
	}

	limiter := NewDualTokenBucketLimiter(
		cfg.PerIPTokenCapacity,
		cfg.PerIPRefillRate,
		cfg.SubnetTokenCap,
		cfg.SubnetRefillRate,
	)

	scorer := NewThreatScorer(cfg.ThreatScoreBan, cfg.ScoreHalfLife, cfg.BanDuration)

	driver, err := NewFirewallDriver(cfg.FirewallDriver, cfg.DryRun)
	if err != nil {
		return nil, fmt.Errorf("failed to init firewall driver: %w", err)
	}

	notifier := NewNotificationPool(cfg.NtfyURL, cfg.NtfyTopic, cfg.WorkerPoolSize, cfg.EventQueueCapacity)

	ctx, cancel := context.WithCancel(context.Background())

	return &SecurityDaemon{
		config:    cfg,
		whitelist: wm,
		limiter:   limiter,
		scorer:    scorer,
		firewall:  driver,
		notifier:  notifier,
		ctx:       ctx,
		cancel:    cancel,
	}, nil
}

// Start binds the TCP listener and begins accepting honeypot probes.
func (sd *SecurityDaemon) Start() error {
	addr := fmt.Sprintf("%s:%d", sd.config.ListenAddr, sd.config.HoneypotPort)
	l, err := net.Listen("tcp", addr)
	if err != nil {
		return fmt.Errorf("failed to listen on %s: %w", addr, err)
	}
	sd.listener = l

	log.Printf("[Security Daemon] Honeypot listener active on %s (Driver: %s, BanThreshold: %d)",
		addr, sd.config.FirewallDriver, sd.config.ThreatScoreBan)

	sd.wg.Add(1)
	go sd.acceptLoop()

	return nil
}

func (sd *SecurityDaemon) acceptLoop() {
	defer sd.wg.Done()

	for {
		conn, err := sd.listener.Accept()
		if err != nil {
			select {
			case <-sd.ctx.Done():
				return
			default:
				log.Printf("[Security Daemon] Accept error: %v", err)
				time.Sleep(10 * time.Millisecond)
				continue
			}
		}

		sd.wg.Add(1)
		go sd.handleConnection(conn)
	}
}

func (sd *SecurityDaemon) handleConnection(conn net.Conn) {
	defer sd.wg.Done()
	defer conn.Close()

	// Set fast I/O deadlines to prevent slowloris holding connections open
	_ = conn.SetDeadline(time.Now().Add(3 * time.Second))

	// Extract remote IP
	remoteAddr := conn.RemoteAddr().String()
	host, _, err := net.SplitHostPort(remoteAddr)
	if err != nil {
		return
	}
	ip := net.ParseIP(host)
	if ip == nil {
		return
	}

	// Step 1: Whitelist & Bogon Check
	if sd.whitelist.IsWhitelisted(ip) {
		// Whitelisted IP connected to honeypot; respond politely and do not score or ban
		_, _ = conn.Write(honeypotBanner)
		return
	}

	// Step 2: Token Bucket Rate Limit Check (Prevent DoS from flood)
	allowed := sd.limiter.Allow(ip)
	if !allowed {
		// Excessive rate: Drop immediately without banner to save bandwidth & CPU
		return
	}

	// Send fake server banner
	_, _ = conn.Write(honeypotBanner)

	// Step 3: Threat Scoring (+30 points per honeypot port probe)
	score, shouldBan := sd.scorer.RecordThreat(ip, 35.0)

	// Step 4: Non-blocking Firewall Ban & Notification Trigger
	if shouldBan {
		go func(targetIP net.IP, targetScore float64) {
			banned, _ := sd.firewall.IsBanned(sd.ctx, targetIP)
			if !banned {
				log.Printf("[Security Daemon] BANNING IP %s (Score: %.1f >= %d)", targetIP.String(), targetScore, sd.config.ThreatScoreBan)
				_ = sd.firewall.Ban(sd.ctx, targetIP, sd.config.BanDuration, "Honeypot probe threshold exceeded")
				sd.notifier.Dispatch(NotificationEvent{
					IP:        targetIP.String(),
					Reason:    "Honeypot probe threshold exceeded",
					Score:     targetScore,
					Timestamp: time.Now(),
				})
			}
		}(ip, score)
	}
}

// Stop gracefully shuts down the security daemon.
func (sd *SecurityDaemon) Stop() error {
	sd.cancel()
	if sd.listener != nil {
		_ = sd.listener.Close()
	}
	sd.wg.Wait()

	sd.limiter.Close()
	sd.scorer.Close()
	sd.notifier.Close()
	_ = sd.firewall.Close()

	log.Printf("[Security Daemon] Shutdown complete.")
	return nil
}
