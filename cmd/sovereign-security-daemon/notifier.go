package main

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"
)

// NotificationEvent represents an alert message to be dispatched asynchronously.
type NotificationEvent struct {
	IP        string
	Reason    string
	Score     float64
	Timestamp time.Time
}

// NotificationPool handles non-blocking webhook/Ntfy notification dispatching.
type NotificationPool struct {
	webhookURL string
	topic      string
	eventChan  chan NotificationEvent
	workerWg   sync.WaitGroup
	ctx        context.Context
	cancel     context.CancelFunc
	client     *http.Client

	mu          sync.Mutex
	lastAlerted map[string]time.Time
}

// NewNotificationPool creates a worker pool of the specified size.
func NewNotificationPool(webhookURL string, topic string, workerCount int, queueCapacity int) *NotificationPool {
	if workerCount <= 0 {
		workerCount = 2
	}
	if queueCapacity <= 0 {
		queueCapacity = 1000
	}

	ctx, cancel := context.WithCancel(context.Background())
	pool := &NotificationPool{
		webhookURL:  webhookURL,
		topic:       topic,
		eventChan:   make(chan NotificationEvent, queueCapacity),
		ctx:         ctx,
		cancel:      cancel,
		client:      &http.Client{Timeout: 5 * time.Second},
		lastAlerted: make(map[string]time.Time),
	}

	for i := 0; i < workerCount; i++ {
		pool.workerWg.Add(1)
		go pool.workerLoop(i)
	}

	return pool
}

// Dispatch queues a notification event. If the queue is full, it drops or logs without blocking.
func (np *NotificationPool) Dispatch(ev NotificationEvent) {
	if np.webhookURL == "" && np.topic == "" {
		return // Notifications disabled
	}

	// Rate limit notifications per IP: at most 1 alert per IP every 10 minutes
	np.mu.Lock()
	last, exists := np.lastAlerted[ev.IP]
	if exists && time.Since(last) < 10*time.Minute {
		np.mu.Unlock()
		return
	}
	np.lastAlerted[ev.IP] = time.Now()
	np.mu.Unlock()

	select {
	case np.eventChan <- ev:
	default:
		log.Printf("[Notifier] Warning: notification queue full, dropping alert for IP %s", ev.IP)
	}
}

func (np *NotificationPool) workerLoop(id int) {
	defer np.workerWg.Done()

	for {
		select {
		case <-np.ctx.Done():
			return
		case ev, ok := <-np.eventChan:
			if !ok {
				return
			}
			np.sendAlert(ev)
		}
	}
}

func (np *NotificationPool) sendAlert(ev NotificationEvent) {
	msg := fmt.Sprintf("🍯 SOVEREIGN DEFENSE: Threat detected from %s (Score: %.1f, Reason: %s) at %s",
		ev.IP, ev.Score, ev.Reason, ev.Timestamp.UTC().Format(time.RFC3339))

	var targetURL string
	if np.webhookURL != "" {
		targetURL = np.webhookURL
		if np.topic != "" && !strings.HasSuffix(targetURL, "/"+np.topic) {
			targetURL = fmt.Sprintf("%s/%s", strings.TrimRight(targetURL, "/"), np.topic)
		}
	} else if np.topic != "" {
		targetURL = fmt.Sprintf("https://ntfy.sh/%s", np.topic)
	} else {
		return
	}

	req, err := http.NewRequestWithContext(np.ctx, http.MethodPost, targetURL, bytes.NewBufferString(msg))
	if err != nil {
		log.Printf("[Notifier] Error creating request: %v", err)
		return
	}
	req.Header.Set("Title", "Sovereign Proxy Active Defense")
	req.Header.Set("Priority", "high")
	req.Header.Set("Tags", "warning,shield")

	resp, err := np.client.Do(req)
	if err != nil {
		log.Printf("[Notifier] Error sending alert to %s: %v", targetURL, err)
		return
	}
	defer resp.Body.Close()
}

// Close gracefully stops the worker pool and flushes/cancels operations.
func (np *NotificationPool) Close() {
	np.cancel()
	close(np.eventChan)
	np.workerWg.Wait()
}
