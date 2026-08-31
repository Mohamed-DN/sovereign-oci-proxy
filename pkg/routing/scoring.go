package routing

const (
	WeightBandwidth  = 35.0
	WeightRTT        = 30.0
	WeightLoss       = 20.0
	WeightReputation = 15.0
	WeightJitter     = 0.05
	MinUsableScore   = 40.0
)

// NodeMetrics encapsulates real-time performance telemetry for path scoring
type NodeMetrics struct {
	AvailableBandwidthMbps float64 `json:"avail_bw_mbps"`
	MaxBandwidthMbps       float64 `json:"max_bw_mbps"`
	RTTms                  float64 `json:"rtt_ms"`
	PacketLossRate         float64 `json:"loss_rate"`    // 0.0 - 1.0
	ReputationScore        float64 `json:"reputation"`   // 0.0 - 1.0
	RTTJitterSigma         float64 `json:"jitter_sigma"` // standard deviation of RTT
}

// CalculatePathScore computes the dynamic multi-factor quality score for a node candidate
func CalculatePathScore(m NodeMetrics) float64 {
	// 1. Bandwidth Factor [0, 1]
	bwRatio := 0.0
	if m.MaxBandwidthMbps > 0 {
		bwRatio = m.AvailableBandwidthMbps / m.MaxBandwidthMbps
		if bwRatio > 1.0 {
			bwRatio = 1.0
		}
	}

	// 2. RTT Factor: 100 / (RTT + 1), scaled such that 0ms -> 1.0, 99ms -> 0.01
	rttRatio := 100.0 / (m.RTTms + 1.0)
	if rttRatio > 1.0 {
		rttRatio = 1.0
	}

	// 3. Loss Factor: 1.0 - LossRate
	lossRatio := 1.0 - m.PacketLossRate
	if lossRatio < 0.0 {
		lossRatio = 0.0
	}

	// 4. Reputation Factor
	repRatio := m.ReputationScore
	if repRatio > 1.0 {
		repRatio = 1.0
	} else if repRatio < 0.0 {
		repRatio = 0.0
	}

	// 5. Jitter Penalty
	jitterPenalty := WeightJitter * m.RTTJitterSigma

	rawScore := (WeightBandwidth * bwRatio) +
		(WeightRTT * rttRatio) +
		(WeightLoss * lossRatio) +
		(WeightReputation * repRatio) -
		jitterPenalty

	if rawScore < 0.0 {
		return 0.0
	}
	if rawScore > 100.0 {
		return 100.0
	}
	return rawScore
}

// IsNodeEligible checks if a candidate meets the minimum score threshold
func IsNodeEligible(m NodeMetrics) bool {
	return CalculatePathScore(m) >= MinUsableScore
}
