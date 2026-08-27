package config

import (
	"flag"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestLayeredPrecedence_String(t *testing.T) {
	cm := &ConfigManager{}

	flagVal := "flag-override"
	envKey := "TEST_PRECEDENCE_STR"
	envVal := "env-value"
	yamlVal := "yaml-value"
	defaultVal := "in-code-default"

	_ = os.Setenv(envKey, envVal)
	defer os.Unsetenv(envKey)

	// Layer 1: CLI Flag beats all
	if res := cm.ResolveString(flagVal, true, envKey, yamlVal, defaultVal); res != "flag-override" {
		t.Errorf("expected flag-override, got %s", res)
	}

	// Layer 2: Env beats YAML and Default (when flag not set)
	if res := cm.ResolveString("", false, envKey, yamlVal, defaultVal); res != "env-value" {
		t.Errorf("expected env-value, got %s", res)
	}

	// Layer 3: YAML beats Default (when flag and env not set)
	_ = os.Unsetenv(envKey)
	if res := cm.ResolveString("", false, envKey, yamlVal, defaultVal); res != "yaml-value" {
		t.Errorf("expected yaml-value, got %s", res)
	}

	// Layer 4: Default when nothing else set
	if res := cm.ResolveString("", false, envKey, "", defaultVal); res != "in-code-default" {
		t.Errorf("expected in-code-default, got %s", res)
	}
}

func TestLayeredPrecedence_IntAndBool(t *testing.T) {
	cm := &ConfigManager{}

	envKeyInt := "TEST_PRECEDENCE_INT"
	envKeyBool := "TEST_PRECEDENCE_BOOL"

	_ = os.Setenv(envKeyInt, "8080")
	_ = os.Setenv(envKeyBool, "true")
	defer os.Unsetenv(envKeyInt)
	defer os.Unsetenv(envKeyBool)

	// Int Layer 1 vs Layer 2 vs Layer 3 vs Layer 4
	if res := cm.ResolveInt(9000, true, envKeyInt, 80, 22); res != 9000 {
		t.Errorf("expected flag 9000, got %d", res)
	}
	if res := cm.ResolveInt(0, false, envKeyInt, 80, 22); res != 8080 {
		t.Errorf("expected env 8080, got %d", res)
	}
	_ = os.Unsetenv(envKeyInt)
	if res := cm.ResolveInt(0, false, envKeyInt, 80, 22); res != 80 {
		t.Errorf("expected yaml 80, got %d", res)
	}
	if res := cm.ResolveInt(0, false, envKeyInt, 0, 22); res != 22 {
		t.Errorf("expected default 22, got %d", res)
	}

	// Bool Layer 1 vs Layer 2 vs Layer 3 vs Layer 4
	if res := cm.ResolveBool(false, true, envKeyBool, true, true); res != false {
		t.Errorf("expected flag false, got %t", res)
	}
	if res := cm.ResolveBool(false, false, envKeyBool, false, false); res != true {
		t.Errorf("expected env true, got %t", res)
	}
	_ = os.Unsetenv(envKeyBool)
	if res := cm.ResolveBool(false, false, envKeyBool, true, false); res != true {
		t.Errorf("expected yaml true, got %t", res)
	}
	if res := cm.ResolveBool(false, false, envKeyBool, false, false); res != false {
		t.Errorf("expected default false, got %t", res)
	}
}

func TestFlagBindingsWithEnv(t *testing.T) {
	fs := flag.NewFlagSet("test-flags", flag.ContinueOnError)

	_ = os.Setenv("TEST_FLAG_PORT", "9999")
	_ = os.Setenv("TEST_FLAG_ENABLE", "true")
	_ = os.Setenv("TEST_FLAG_TIMEOUT", "10s")
	defer func() {
		os.Unsetenv("TEST_FLAG_PORT")
		os.Unsetenv("TEST_FLAG_ENABLE")
		os.Unsetenv("TEST_FLAG_TIMEOUT")
	}()

	portPtr := BindIntFlag(fs, "port", "TEST_FLAG_PORT", 8080, "Test port")
	enablePtr := BindBoolFlag(fs, "enable", "TEST_FLAG_ENABLE", false, "Test enable")
	timeoutPtr := BindDurationFlag(fs, "timeout", "TEST_FLAG_TIMEOUT", 1*time.Second, "Test timeout")

	// Parse with no arguments -> defaults to env
	if err := fs.Parse([]string{}); err != nil {
		t.Fatalf("failed to parse flags: %v", err)
	}

	if *portPtr != 9999 {
		t.Errorf("expected port 9999 from env, got %d", *portPtr)
	}
	if !*enablePtr {
		t.Errorf("expected enable true from env, got %t", *enablePtr)
	}
	if *timeoutPtr != 10*time.Second {
		t.Errorf("expected timeout 10s from env, got %v", *timeoutPtr)
	}

	// Parse with explicit CLI arguments -> CLI overrides env
	fs2 := flag.NewFlagSet("test-flags-2", flag.ContinueOnError)
	portPtr2 := BindIntFlag(fs2, "port", "TEST_FLAG_PORT", 8080, "Test port")
	if err := fs2.Parse([]string{"--port", "7777"}); err != nil {
		t.Fatalf("failed to parse flags: %v", err)
	}
	if *portPtr2 != 7777 {
		t.Errorf("expected CLI override 7777, got %d", *portPtr2)
	}
}

func TestNewConfigManagerWithFile(t *testing.T) {
	tmpDir := t.TempDir()
	envPath := filepath.Join(tmpDir, ".env")
	yamlPath := filepath.Join(tmpDir, "mesh-cluster.yaml")

	_ = os.WriteFile(envPath, []byte("SOV_MGR_TEST_ENV=from_dotenv\n"), 0600)
	_ = os.WriteFile(yamlPath, []byte(sampleValidConfig), 0600)

	cm, err := NewConfigManager(yamlPath, envPath)
	if err != nil {
		t.Fatalf("NewConfigManager failed: %v", err)
	}

	if cm.MeshConfig == nil {
		t.Fatalf("MeshConfig is nil")
	}

	summary := RedactedClusterSummary(cm.MeshConfig)
	if !strings.Contains(summary, "test-mesh-cluster") {
		t.Errorf("expected summary to contain test-mesh-cluster, got %s", summary)
	}
}
