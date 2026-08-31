package bridge

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"net/http"
	"sync"
	"time"
)

var (
	ErrDNSLookupFailed = errors.New("DoH DNS query failed on all upstream resolvers")
)

type dohResponse struct {
	Status int `json:"Status"`
	Answer []struct {
		Name string `json:"name"`
		Type int    `json:"type"`
		TTL  int    `json:"TTL"`
		Data string `json:"data"`
	} `json:"Answer"`
}

type dnsCacheEntry struct {
	ips       []net.IP
	expiresAt time.Time
}

// DoHResolver resolves hostnames using encrypted DNS-over-HTTPS
type DoHResolver struct {
	mu         sync.RWMutex
	upstreams  []string
	httpClient *http.Client
	cache      map[string]*dnsCacheEntry
}

// NewDoHResolver creates a new DoH resolver with Cloudflare and Quad9 default endpoints
func NewDoHResolver(upstreams []string) *DoHResolver {
	if len(upstreams) == 0 {
		upstreams = []string{
			"https://1.1.1.1/dns-query",
			"https://dns.quad9.net/dns-query",
		}
	}

	return &DoHResolver{
		upstreams: upstreams,
		cache:     make(map[string]*dnsCacheEntry),
		httpClient: &http.Client{
			Timeout: 5 * time.Second,
		},
	}
}

// ResolveIPs queries the DoH upstreams for IPv4/IPv6 addresses of a domain name
func (r *DoHResolver) ResolveIPs(ctx context.Context, domain string) ([]net.IP, error) {
	// If already an IP address, return directly
	if ip := net.ParseIP(domain); ip != nil {
		return []net.IP{ip}, nil
	}

	// Check cache
	r.mu.RLock()
	cached, ok := r.cache[domain]
	if ok && time.Now().Before(cached.expiresAt) {
		ips := cached.ips
		r.mu.RUnlock()
		return ips, nil
	}
	r.mu.RUnlock()

	var lastErr error
	for _, upstream := range r.upstreams {
		reqURL := fmt.Sprintf("%s?name=%s&type=A", upstream, domain)
		req, err := http.NewRequestWithContext(ctx, "GET", reqURL, nil)
		if err != nil {
			lastErr = err
			continue
		}
		req.Header.Set("Accept", "application/dns-json")

		resp, err := r.httpClient.Do(req)
		if err != nil {
			lastErr = err
			continue
		}

		if resp.StatusCode != http.StatusOK {
			resp.Body.Close()
			lastErr = fmt.Errorf("upstream returned status %d", resp.StatusCode)
			continue
		}

		var dohResp dohResponse
		err = json.NewDecoder(resp.Body).Decode(&dohResp)
		resp.Body.Close()
		if err != nil {
			lastErr = err
			continue
		}

		var ips []net.IP
		ttl := 300
		for _, ans := range dohResp.Answer {
			if ans.Type == 1 { // Type A (IPv4)
				if ip := net.ParseIP(ans.Data); ip != nil {
					ips = append(ips, ip)
					if ans.TTL > 0 && ans.TTL < ttl {
						ttl = ans.TTL
					}
				}
			}
		}

		if len(ips) > 0 {
			r.mu.Lock()
			r.cache[domain] = &dnsCacheEntry{
				ips:       ips,
				expiresAt: time.Now().Add(time.Duration(ttl) * time.Second),
			}
			r.mu.Unlock()
			return ips, nil
		}
	}

	// Fallback to standard Go net.DefaultResolver if DoH unavailable in test/local environments
	addrs, err := net.DefaultResolver.LookupIP(ctx, "ip4", domain)
	if err == nil && len(addrs) > 0 {
		return addrs, nil
	}

	if lastErr != nil {
		return nil, fmt.Errorf("%w: %v", ErrDNSLookupFailed, lastErr)
	}
	return nil, ErrDNSLookupFailed
}
