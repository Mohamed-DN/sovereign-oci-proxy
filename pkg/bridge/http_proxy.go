package bridge

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"strconv"
	"sync"
	"time"
)

// HTTPProxyServer handles inbound HTTP CONNECT proxy requests
type HTTPProxyServer struct {
	mu         sync.Mutex
	listenAddr string
	server     *http.Server
	bridge     *NetstackBridge
	listener   net.Listener
	closed     bool
}

// NewHTTPProxyServer creates a new HTTP proxy server instance
func NewHTTPProxyServer(listenAddr string, bridge *NetstackBridge) *HTTPProxyServer {
	return &HTTPProxyServer{
		listenAddr: listenAddr,
		bridge:     bridge,
	}
}

// Start launches the HTTP proxy server
func (s *HTTPProxyServer) Start() error {
	ln, err := net.Listen("tcp", s.listenAddr)
	if err != nil {
		return fmt.Errorf("failed to listen on HTTP proxy %s: %w", s.listenAddr, err)
	}

	s.listener = ln
	s.server = &http.Server{
		Handler:      http.HandlerFunc(s.handleHTTP),
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	go func() {
		_ = s.server.Serve(ln)
	}()

	return nil
}

func (s *HTTPProxyServer) handleHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodConnect {
		http.Error(w, "Only HTTP CONNECT tunneling is supported", http.StatusMethodNotAllowed)
		return
	}

	host, portStr, err := net.SplitHostPort(r.Host)
	if err != nil {
		http.Error(w, "Invalid host:port specification", http.StatusBadRequest)
		return
	}

	port, err := strconv.Atoi(portStr)
	if err != nil {
		http.Error(w, "Invalid port number", http.StatusBadRequest)
		return
	}

	hijacker, ok := w.(http.Hijacker)
	if !ok {
		http.Error(w, "Hijacking not supported", http.StatusInternalServerError)
		return
	}

	clientConn, _, err := hijacker.Hijack()
	if err != nil {
		http.Error(w, err.Error(), http.StatusServiceUnavailable)
		return
	}

	// Send 200 Connection Established
	_, _ = clientConn.Write([]byte("HTTP/1.1 200 Connection Established\r\n\r\n"))

	// Hand over to NetstackBridge
	_ = s.bridge.DialAndPipe(context.Background(), clientConn, host, port)
}

// Addr returns the listening address
func (s *HTTPProxyServer) Addr() net.Addr {
	if s.listener != nil {
		return s.listener.Addr()
	}
	return nil
}

// Close shuts down the HTTP proxy server
func (s *HTTPProxyServer) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.closed = true
	if s.server != nil {
		return s.server.Close()
	}
	return nil
}
