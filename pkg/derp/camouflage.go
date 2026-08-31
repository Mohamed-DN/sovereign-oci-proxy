package derp

import (
	"fmt"
	"net/http"
)

const (
	RelayWebSocketPath = "/ws/v4/relay"
	DefaultDecoyTitle  = "Enterprise Cloud Mirror - Edge Relay"
)

// DecoyHandler serves authentic static HTML responses to scanner probes on non-relay paths
type DecoyHandler struct {
	Title string
}

// NewDecoyHandler creates a new static decoy HTTP handler
func NewDecoyHandler(title string) *DecoyHandler {
	if title == "" {
		title = DefaultDecoyTitle
	}
	return &DecoyHandler{Title: title}
}

func (h *DecoyHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Server", "nginx/1.24.0 (Ubuntu)")
	w.Header().Set("Content-Type", "text/html; charset=UTF-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("X-Frame-Options", "DENY")
	w.Header().Set("Cache-Control", "public, max-age=3600")

	w.WriteHeader(http.StatusOK)
	html := fmt.Sprintf(`<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>%s</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 40px; background-color: #f4f6f8; color: #24292e; }
        .container { max-width: 800px; margin: 0 auto; background: #ffffff; padding: 40px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        h1 { font-size: 24px; border-bottom: 1px solid #eaecef; padding-bottom: 12px; margin-top: 0; }
        p { line-height: 1.6; color: #586069; }
        .status-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold; background-color: #2ea44f; color: white; margin-bottom: 20px; }
        footer { margin-top: 40px; font-size: 12px; color: #6a737d; text-align: center; border-top: 1px solid #eaecef; padding-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <span class="status-badge">Operational</span>
        <h1>%s</h1>
        <p>This edge cluster node provides high-availability distributed object delivery and secure telemetry proxy services for multi-region infrastructure fabrics.</p>
        <p>All ingress traffic is monitored and rate-limited. Unauthorized vulnerability scans or brute force probing attempts are automatically scrubbed by edge mitigation filters.</p>
        <footer>
            &copy; 2026 NeroNet / DARKNERO.COM. All rights reserved. Generated: HTTP/1.1 200 OK.
        </footer>
    </div>
</body>
</html>`, h.Title, h.Title)

	_, _ = w.Write([]byte(html))
}
