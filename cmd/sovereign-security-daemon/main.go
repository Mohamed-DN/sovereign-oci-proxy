package main

import (
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	configPath := flag.String("config", "", "Path to JSON configuration file")
	port := flag.Int("port", 0, "Honeypot TCP listening port override")
	driver := flag.String("driver", "", "Firewall driver (mock, ipset, nftables, ufw-batch)")
	dryRun := flag.Bool("dry-run", false, "Simulate actions without applying kernel firewall bans")
	flag.Parse()

	log.Printf("[Security Daemon] Initializing Sovereign Proxy v4.0 Active Defense Daemon...")

	cfg, err := LoadConfig(*configPath)
	if err != nil {
		log.Fatalf("[Security Daemon] Failed to load configuration: %v", err)
	}

	if *port > 0 {
		cfg.HoneypotPort = *port
	}
	if *driver != "" {
		cfg.FirewallDriver = *driver
	}
	if *dryRun {
		cfg.DryRun = true
	}

	daemon, err := NewSecurityDaemon(cfg)
	if err != nil {
		log.Fatalf("[Security Daemon] Failed to create daemon: %v", err)
	}

	if err := daemon.Start(); err != nil {
		log.Fatalf("[Security Daemon] Failed to start daemon: %v", err)
	}

	// Trap termination signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	sig := <-sigChan
	log.Printf("[Security Daemon] Received signal %v, shutting down gracefully...", sig)

	if err := daemon.Stop(); err != nil {
		log.Printf("[Security Daemon] Error during shutdown: %v", err)
	}
}
