package config

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

const (
	// DefaultK8sSecretDir is the standard mounted secrets directory in containerized environments.
	DefaultK8sSecretDir = "/var/run/secrets/sovereign"
)

// SecretDir override for testing and custom deployments.
var customSecretDir = ""

// SetSecretDir allows configuring a custom secret directory path.
func SetSecretDir(dir string) {
	customSecretDir = dir
}

// GetSecretDir returns the active secret directory path.
func GetSecretDir() string {
	if customSecretDir != "" {
		return customSecretDir
	}
	if envDir := os.Getenv("SOVEREIGN_SECRETS_DIR"); envDir != "" {
		return envDir
	}
	return DefaultK8sSecretDir
}

// ParseDotEnv parses raw .env content into a key-value map.
// Supports comments (#), export statements, double/single quotes, and whitespace trimming.
func ParseDotEnv(content string) map[string]string {
	result := make(map[string]string)
	lines := strings.Split(content, "\n")

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}

		// Handle export prefix e.g. "export KEY=VAL"
		if strings.HasPrefix(trimmed, "export ") {
			trimmed = strings.TrimSpace(strings.TrimPrefix(trimmed, "export "))
		}

		// Strip inline comments if not inside quotes
		if idx := strings.Index(trimmed, " #"); idx != -1 {
			// Check if quote is before the comment
			quoteCount := 0
			for _, r := range trimmed[:idx] {
				if r == '"' || r == '\'' {
					quoteCount++
				}
			}
			if quoteCount%2 == 0 {
				trimmed = strings.TrimSpace(trimmed[:idx])
			}
		}

		eqIdx := strings.Index(trimmed, "=")
		if eqIdx == -1 {
			continue
		}

		key := strings.TrimSpace(trimmed[:eqIdx])
		val := strings.TrimSpace(trimmed[eqIdx+1:])

		// Unquote strings if wrapped in quotes
		if len(val) >= 2 {
			if (val[0] == '"' && val[len(val)-1] == '"') || (val[0] == '\'' && val[len(val)-1] == '\'') {
				val = val[1 : len(val)-1]
			}
		}

		if key != "" {
			result[key] = val
		}
	}

	return result
}

// LoadDotEnv searches and loads environment variables from the given file paths in order.
// If no paths are given, it searches for ".env" and "/etc/sovereign/sovereign.env".
// Does NOT override variables already set in the active process environment.
func LoadDotEnv(paths ...string) error {
	if len(paths) == 0 {
		paths = []string{
			".env",
			"../.env",
			"../../.env",
			"/etc/sovereign/sovereign.env",
			"/opt/sovereign/config/node.env",
		}
	}

	for _, p := range paths {
		if p == "" {
			continue
		}
		data, err := os.ReadFile(p)
		if err != nil {
			// Non-fatal if file does not exist
			continue
		}

		parsed := ParseDotEnv(string(data))
		for k, v := range parsed {
			// Only set if not already set in OS environment
			if _, exists := os.LookupEnv(k); !exists {
				// Expand nested env variables in value
				expandedVal := ExpandEnv(v)
				_ = os.Setenv(k, expandedVal)
			}
		}
	}

	return nil
}

// GetEnv retrieves the value of the environment variable named by key, or fallback if empty.
func GetEnv(key, fallback string) string {
	if val, exists := os.LookupEnv(key); exists && strings.TrimSpace(val) != "" {
		return val
	}
	return fallback
}

// GetEnvInt retrieves an integer environment variable or returns fallback.
func GetEnvInt(key string, fallback int) int {
	valStr := GetEnv(key, "")
	if valStr == "" {
		return fallback
	}
	if val, err := strconv.Atoi(strings.TrimSpace(valStr)); err == nil {
		return val
	}
	return fallback
}

// GetEnvBool retrieves a boolean environment variable (true, 1, yes, on) or returns fallback.
func GetEnvBool(key string, fallback bool) bool {
	valStr := GetEnv(key, "")
	if valStr == "" {
		return fallback
	}
	lower := strings.ToLower(strings.TrimSpace(valStr))
	if lower == "true" || lower == "1" || lower == "yes" || lower == "on" {
		return true
	}
	if lower == "false" || lower == "0" || lower == "no" || lower == "off" {
		return false
	}
	return fallback
}

// GetEnvDuration retrieves a time.Duration environment variable (e.g. "15s", "1h") or returns fallback.
func GetEnvDuration(key string, fallback time.Duration) time.Duration {
	valStr := GetEnv(key, "")
	if valStr == "" {
		return fallback
	}
	if d, err := time.ParseDuration(strings.TrimSpace(valStr)); err == nil {
		return d
	}
	return fallback
}

// GetEnvSlice retrieves a comma-separated list of strings from an environment variable.
func GetEnvSlice(key string, fallback []string) []string {
	valStr := GetEnv(key, "")
	if valStr == "" {
		return fallback
	}
	parts := strings.Split(valStr, ",")
	var result []string
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p != "" {
			result = append(result, p)
		}
	}
	if len(result) == 0 {
		return fallback
	}
	return result
}

// GetSecret loads a secret token/key using the Zero-Plaintext Resolution Protocol:
// 1. Direct environment variable (e.g. REALITY_PRIVATE_KEY)
// 2. Mounted Kubernetes/Vault secret file (/var/run/secrets/sovereign/<KEY>)
// 3. Fallback value if provided
// 4. Cryptographically secure random token generation (if default is empty).
func GetSecret(key, defaultValue string) string {
	// 1. Check OS Environment
	if val, exists := os.LookupEnv(key); exists && strings.TrimSpace(val) != "" {
		return strings.TrimSpace(val)
	}

	// 2. Check Mounted Secret File
	secretFile := filepath.Join(GetSecretDir(), key)
	if data, err := os.ReadFile(secretFile); err == nil && len(strings.TrimSpace(string(data))) > 0 {
		return strings.TrimSpace(string(data))
	}

	// 3. Check Default Value
	if strings.TrimSpace(defaultValue) != "" {
		return defaultValue
	}

	// 4. Generate Crypto-Secure Random Hex Token
	randomBytes := make([]byte, 32)
	if _, err := rand.Read(randomBytes); err == nil {
		return hex.EncodeToString(randomBytes)
	}

	// Ultimate fallback if entropy source fails
	return fmt.Sprintf("sec_%d", time.Now().UnixNano())
}

// MaskSecret returns a masked representation of a secret suitable for logs (e.g. abc****xyz).
func MaskSecret(raw string) string {
	raw = strings.TrimSpace(raw)
	if len(raw) == 0 {
		return "<empty>"
	}
	if len(raw) <= 6 {
		return "******"
	}
	prefix := raw[:3]
	suffix := raw[len(raw)-3:]
	return fmt.Sprintf("%s****%s", prefix, suffix)
}
