package routing

import (
	"crypto/rand"
	"encoding/binary"
	"errors"
	"fmt"
	"time"

	"github.com/sovereign/proxy/v4/pkg/crypto"
)

var (
	ErrCircuitHopMismatch = errors.New("3-hop onion circuit requires exactly 3 distinct hops")
	ErrPeelFailed         = errors.New("failed to peel onion layer: authentication tag mismatch")
)

// OnionHop represents one hop in an onion circuit
type OnionHop struct {
	HopIndex  int
	NodeID    string
	PublicKey [crypto.KeySize]byte
	SharedKey [crypto.KeySize]byte
}

// OnionCircuit represents an established 3-hop obfuscation circuit
type OnionCircuit struct {
	CircuitID    uint32
	Hops         [3]*OnionHop
	EphemeralKP  *crypto.Keypair
	CreatedAt    time.Time
	MinJitterMs  int
	MaxJitterMs  int
}

// Build3HopCircuit constructs a layered circuit using client's ephemeral key and hops' public keys
func Build3HopCircuit(circuitID uint32, entry, intermediate, exit *OnionHop) (*OnionCircuit, error) {
	if entry == nil || intermediate == nil || exit == nil {
		return nil, ErrCircuitHopMismatch
	}

	ephKP, err := crypto.GenerateKeypair()
	if err != nil {
		return nil, fmt.Errorf("failed to generate circuit ephemeral keypair: %w", err)
	}

	// Compute shared secrets with each hop
	k1, err := crypto.DH(ephKP.PrivateKey, entry.PublicKey)
	if err != nil {
		return nil, fmt.Errorf("entry DH failed: %w", err)
	}
	entry.SharedKey = k1

	k2, err := crypto.DH(ephKP.PrivateKey, intermediate.PublicKey)
	if err != nil {
		return nil, fmt.Errorf("intermediate DH failed: %w", err)
	}
	intermediate.SharedKey = k2

	k3, err := crypto.DH(ephKP.PrivateKey, exit.PublicKey)
	if err != nil {
		return nil, fmt.Errorf("exit DH failed: %w", err)
	}
	exit.SharedKey = k3

	return &OnionCircuit{
		CircuitID:   circuitID,
		Hops:        [3]*OnionHop{entry, intermediate, exit},
		EphemeralKP: ephKP,
		CreatedAt:   time.Now(),
		MinJitterMs: 2,
		MaxJitterMs: 20,
	}, nil
}

// LayeredPayloadLayout:
// Layer 3 (Exit): [IsExit=0x01 (1B)] [TargetLen (2B)] [TargetAddr] [DataLen (2B)] [Data]
// Layer 2 (Intermediate): [IsExit=0x00 (1B)] [NextHopPub (32B)] [Layer3Ciphertext]
// Layer 1 (Entry): [IsExit=0x00 (1B)] [NextHopPub (32B)] [Layer2Ciphertext]

// EncryptLayeredData seals data into a 3-hop onion cell
func (c *OnionCircuit) EncryptLayeredData(streamID uint32, targetAddr string, payload []byte) ([]byte, error) {
	nonce0 := crypto.ConstructNonce(0)

	// 1. Layer 3 (Exit Hop)
	layer3Plain := make([]byte, 1+2+len(targetAddr)+2+len(payload))
	layer3Plain[0] = 0x01 // IsExit
	binary.BigEndian.PutUint16(layer3Plain[1:3], uint16(len(targetAddr)))
	copy(layer3Plain[3:3+len(targetAddr)], []byte(targetAddr))
	dataOffset := 3 + len(targetAddr)
	binary.BigEndian.PutUint16(layer3Plain[dataOffset:dataOffset+2], uint16(len(payload)))
	copy(layer3Plain[dataOffset+2:], payload)

	layer3Cipher, err := crypto.ChaCha20Poly1305Seal(c.Hops[2].SharedKey, nonce0, layer3Plain, []byte("onion-layer-3"))
	if err != nil {
		return nil, fmt.Errorf("layer 3 seal failed: %w", err)
	}

	// 2. Layer 2 (Intermediate Hop)
	layer2Plain := make([]byte, 1+crypto.KeySize+len(layer3Cipher))
	layer2Plain[0] = 0x00 // Not exit
	copy(layer2Plain[1:33], c.Hops[2].PublicKey[:])
	copy(layer2Plain[33:], layer3Cipher)

	layer2Cipher, err := crypto.ChaCha20Poly1305Seal(c.Hops[1].SharedKey, nonce0, layer2Plain, []byte("onion-layer-2"))
	if err != nil {
		return nil, fmt.Errorf("layer 2 seal failed: %w", err)
	}

	// 3. Layer 1 (Entry Hop)
	layer1Plain := make([]byte, 1+crypto.KeySize+len(layer2Cipher))
	layer1Plain[0] = 0x00 // Not exit
	copy(layer1Plain[1:33], c.Hops[1].PublicKey[:])
	copy(layer1Plain[33:], layer2Cipher)

	layer1Cipher, err := crypto.ChaCha20Poly1305Seal(c.Hops[0].SharedKey, nonce0, layer1Plain, []byte("onion-layer-1"))
	if err != nil {
		return nil, fmt.Errorf("layer 1 seal failed: %w", err)
	}

	// Pack client ephemeral public key (32B) + Layer 1 Ciphertext into OnionCell
	cellPayload := make([]byte, crypto.KeySize+len(layer1Cipher))
	copy(cellPayload[0:32], c.EphemeralKP.PublicKey[:])
	copy(cellPayload[32:], layer1Cipher)

	cell := &OnionCell{
		CircuitID: c.CircuitID,
		Command:   CellCmdRelayData,
		StreamID:  streamID,
		Digest:    0,
		Payload:   cellPayload,
	}

	return EncodeCell(cell)
}

// PeelResult represents peeled layer output at each intermediate or exit hop
type PeelResult struct {
	IsExit       bool
	NextHopPub   [crypto.KeySize]byte
	TargetAddr   string
	InnerPayload []byte
}

// PeelLayer decrypts one layer of the onion at an intermediate or exit hop
func PeelLayer(hopPrivKey [crypto.KeySize]byte, layerIndex int, cellPayload []byte) (*PeelResult, error) {
	if len(cellPayload) < crypto.KeySize+16 {
		return nil, errors.New("cell payload too small to contain ephemeral key and ciphertext")
	}

	var clientEphPub [crypto.KeySize]byte
	copy(clientEphPub[:], cellPayload[0:32])
	ciphertext := cellPayload[32:]

	sharedKey, err := crypto.DH(hopPrivKey, clientEphPub)
	if err != nil {
		return nil, fmt.Errorf("DH computation failed during peel: %w", err)
	}

	ad := fmt.Sprintf("onion-layer-%d", layerIndex)
	nonce0 := crypto.ConstructNonce(0)

	plaintext, err := crypto.ChaCha20Poly1305Open(sharedKey, nonce0, ciphertext, []byte(ad))
	if err != nil {
		return nil, fmt.Errorf("%w: layer %d", ErrPeelFailed, layerIndex)
	}

	if len(plaintext) < 1 {
		return nil, errors.New("empty peeled layer plaintext")
	}

	isExit := plaintext[0] == 0x01
	if isExit {
		if len(plaintext) < 5 {
			return nil, errors.New("invalid exit layer format")
		}
		targetLen := int(binary.BigEndian.Uint16(plaintext[1:3]))
		targetAddr := string(plaintext[3 : 3+targetLen])
		dataOffset := 3 + targetLen
		dataLen := int(binary.BigEndian.Uint16(plaintext[dataOffset : dataOffset+2]))
		data := plaintext[dataOffset+2 : dataOffset+2+dataLen]

		return &PeelResult{
			IsExit:       true,
			TargetAddr:   targetAddr,
			InnerPayload: data,
		}, nil
	}

	// Intermediate hop
	if len(plaintext) < 1+crypto.KeySize {
		return nil, errors.New("invalid intermediate layer format")
	}

	var nextHopPub [crypto.KeySize]byte
	copy(nextHopPub[:], plaintext[1:33])
	innerCiphertext := plaintext[33:]

	// Repack with client ephemeral pubkey for next hop
	nextPayload := make([]byte, crypto.KeySize+len(innerCiphertext))
	copy(nextPayload[0:32], clientEphPub[:])
	copy(nextPayload[32:], innerCiphertext)

	return &PeelResult{
		IsExit:       false,
		NextHopPub:   nextHopPub,
		InnerPayload: nextPayload,
	}, nil
}

// ComputeJitterDelay generates a pseudorandom delay between min and max ms to prevent timing correlation
func (c *OnionCircuit) ComputeJitterDelay() time.Duration {
	if c.MaxJitterMs <= c.MinJitterMs {
		return time.Duration(c.MinJitterMs) * time.Millisecond
	}

	var b [2]byte
	_, _ = rand.Read(b[:])
	val := int(binary.BigEndian.Uint16(b[:]))
	rangeMs := c.MaxJitterMs - c.MinJitterMs
	delayMs := c.MinJitterMs + (val % rangeMs)

	return time.Duration(delayMs) * time.Millisecond
}
