package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/sovereign/proxy/v4/pkg/config"
	"github.com/sovereign/proxy/v4/pkg/derp"
)

func main() {
	_ = config.LoadDotEnv()

	listenAddr := config.BindStringFlag(flag.CommandLine, "listen-addr", "SOVEREIGN_RELAY_LISTEN_ADDR", "0.0.0.0:443", "DERP-v4 TCP/WebSocket listen address")
	stunAddr := config.BindStringFlag(flag.CommandLine, "stun-addr", "SOVEREIGN_STUN_LISTEN_ADDR", "0.0.0.0:3478", "STUN UDP reflection listen address")
	region := config.BindStringFlag(flag.CommandLine, "region", "SOVEREIGN_RELAY_REGION", "us-east", "Geographic cloud region identifier")
	decoyTitle := config.BindStringFlag(flag.CommandLine, "decoy-title", "SOVEREIGN_DECOY_TITLE", "Enterprise Edge Proxy Node", "Title for anti-probing decoy web page")
	flag.Parse()

	log.Printf("[SOVEREIGN-DERP-RELAY] Starting camouflaged DERP-v4 relay [Region: %s, TCP: %s, UDP STUN: %s]...", *region, *listenAddr, *stunAddr)

	server := derp.NewServer(derp.ServerConfig{
		ListenAddr: *listenAddr,
		STUNAddr:   *stunAddr,
		Region:     *region,
		DecoyTitle: *decoyTitle,
	})

	if err := server.Start(); err != nil {
		log.Fatalf("Failed to start DERP relay server: %v", err)
	}

	log.Printf("[SOVEREIGN-DERP-RELAY] DERP-v4 Relay operational with WebSocket camouflage at /ws/v4/relay")

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	<-sigChan

	log.Println("[SOVEREIGN-DERP-RELAY] Draining relay connections and shutting down...")
	_ = server.Close()
	fmt.Println("Sovereign derp relay stopped cleanly.")
}
