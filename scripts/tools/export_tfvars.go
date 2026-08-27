//go:build tools
// +build tools

package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/sovereign/proxy/v4/pkg/config"
)

func main() {
	configPath := flag.String("config", "configs/mesh-cluster.yaml", "Path to mesh-cluster.yaml")
	outDir := flag.String("out-dir", "terraform/environments/prod-multi-cloud", "Output directory for tfvars.json files")
	flag.Parse()

	cfg, err := config.LoadMeshConfig(*configPath)
	if err != nil {
		log.Fatalf("Failed to load mesh configuration: %v", err)
	}

	if err := os.MkdirAll(*outDir, 0755); err != nil {
		log.Fatalf("Failed to create output directory: %v", err)
	}

	// Export OCI
	if ociBytes, err := cfg.ExportOCITFVars(); err == nil {
		_ = os.WriteFile(filepath.Join(*outDir, "oci.tfvars.json"), ociBytes, 0644)
	}
	// Export AWS
	if awsBytes, err := cfg.ExportAWSTFVars(); err == nil {
		_ = os.WriteFile(filepath.Join(*outDir, "aws.tfvars.json"), awsBytes, 0644)
	}
	// Export GCP
	if gcpBytes, err := cfg.ExportGCPTFVars(); err == nil {
		_ = os.WriteFile(filepath.Join(*outDir, "gcp.tfvars.json"), gcpBytes, 0644)
	}
	// Export DO
	if doBytes, err := cfg.ExportDOTFVars(); err == nil {
		_ = os.WriteFile(filepath.Join(*outDir, "do.tfvars.json"), doBytes, 0644)
	}
	// Export Hetzner
	if hetznerBytes, err := cfg.ExportHetznerTFVars(); err == nil {
		_ = os.WriteFile(filepath.Join(*outDir, "hetzner.tfvars.json"), hetznerBytes, 0644)
	}
	// Export Vultr
	if vultrBytes, err := cfg.ExportVultrTFVars(); err == nil {
		_ = os.WriteFile(filepath.Join(*outDir, "vultr.tfvars.json"), vultrBytes, 0644)
	}

	fmt.Printf("Successfully exported Terraform variable definitions to %s\n", *outDir)
}
