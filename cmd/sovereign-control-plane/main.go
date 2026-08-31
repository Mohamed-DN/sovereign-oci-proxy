package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/sovereign/proxy/v4/pkg/config"
	"github.com/sovereign/proxy/v4/pkg/control"
)

func main() {
	_ = config.LoadDotEnv()

	listenAddr := config.BindStringFlag(flag.CommandLine, "listen-addr", "SOVEREIGN_CONTROL_PLANE_LISTEN_ADDR", "0.0.0.0:8443", "Control plane API listen address")
	flag.Parse()

	log.Printf("[SOVEREIGN-CONTROL-PLANE] Initializing control plane coordinator on %s...", *listenAddr)

	server := control.NewServer(control.ServerConfig{
		ListenAddr: *listenAddr,
	})

	if err := server.Start(); err != nil {
		log.Fatalf("Failed to start control plane server: %v", err)
	}

	log.Printf("[SOVEREIGN-CONTROL-PLANE] Control plane service operational on %s", *listenAddr)
	log.Println("[SOVEREIGN-CONTROL-PLANE] - Zero Trust Dynamic ACL & Policy Engine active")
	log.Println("[SOVEREIGN-CONTROL-PLANE] - Subnet Route Distribution & High Availability active")
	log.Println("[SOVEREIGN-CONTROL-PLANE] - Continuous Posture Attestation & Quarantine active")
	log.Println("[SOVEREIGN-CONTROL-PLANE] - Management REST API & Prometheus Exporter active on /metrics")

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	<-sigChan

	log.Println("[SOVEREIGN-CONTROL-PLANE] Shutting down control plane daemon...")
	_ = server.Close()
	fmt.Println("Sovereign control plane stopped cleanly.")
}
