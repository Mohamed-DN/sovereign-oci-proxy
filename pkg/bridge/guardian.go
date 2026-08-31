package bridge

import (
	"sync"
	"time"
)

// PowerSource represents device power status
type PowerSource string

const (
	PowerACBattery PowerSource = "AC_POWER"
	PowerBattery   PowerSource = "BATTERY"
)

// Guardian tracks device battery and data quota constraints
type Guardian struct {
	mu             sync.RWMutex
	batteryPct     uint8
	onBatteryPower bool
	quotaCapMB     uint64
	transferredMB  uint64
	isSuspended    bool
	lastCheck      time.Time
}

// NewGuardian creates a new device safeguard monitor
func NewGuardian(quotaCapMB uint64) *Guardian {
	return &Guardian{
		batteryPct:     100,
		onBatteryPower: false,
		quotaCapMB:     quotaCapMB,
		lastCheck:      time.Now(),
	}
}

// UpdateBattery updates the current battery status
func (g *Guardian) UpdateBattery(pct uint8, onBattery bool) {
	g.mu.Lock()
	defer g.mu.Unlock()

	g.batteryPct = pct
	g.onBatteryPower = onBattery
	g.lastCheck = time.Now()

	if onBattery && pct < 20 {
		g.isSuspended = true
	} else if (!onBattery) || pct >= 25 {
		g.isSuspended = false
	}
}

// RecordTransfer adds bytes to the quota tracker
func (g *Guardian) RecordTransfer(bytesCount uint64) {
	g.mu.Lock()
	defer g.mu.Unlock()

	g.transferredMB += (bytesCount / (1024 * 1024))
	if g.quotaCapMB > 0 && g.transferredMB >= (g.quotaCapMB*9/10) {
		g.isSuspended = true
	}
}

// IsSuspended returns true if the bridge should pause egress operations
func (g *Guardian) IsSuspended() bool {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return g.isSuspended
}

// Status returns current guardian metrics
func (g *Guardian) Status() (batteryPct uint8, onBattery bool, suspended bool, usedMB uint64) {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return g.batteryPct, g.onBatteryPower, g.isSuspended, g.transferredMB
}
