package crypto

import (
	"crypto/rand"
	"fmt"
	"io"

	"golang.org/x/crypto/curve25519"
)

const (
	KeySize = 32
)

// Keypair represents a Curve25519 static or ephemeral private/public keypair
type Keypair struct {
	PrivateKey [KeySize]byte
	PublicKey  [KeySize]byte
}

// GenerateKeypair creates a cryptographically secure random Curve25519 keypair
func GenerateKeypair() (*Keypair, error) {
	var priv [KeySize]byte
	if _, err := io.ReadFull(rand.Reader, priv[:]); err != nil {
		return nil, fmt.Errorf("failed to generate random private key: %w", err)
	}

	// Curve25519 clamping
	priv[0] &= 248
	priv[31] &= 127
	priv[31] |= 64

	pub, err := curve25519.X25519(priv[:], curve25519.Basepoint)
	if err != nil {
		return nil, fmt.Errorf("failed to derive public key: %w", err)
	}

	var pubArr [KeySize]byte
	copy(pubArr[:], pub)

	return &Keypair{
		PrivateKey: priv,
		PublicKey:  pubArr,
	}, nil
}

// DH performs Diffie-Hellman key agreement using private key and peer's public key
func DH(privateKey [KeySize]byte, peerPublicKey [KeySize]byte) ([KeySize]byte, error) {
	shared, err := curve25519.X25519(privateKey[:], peerPublicKey[:])
	if err != nil {
		return [KeySize]byte{}, fmt.Errorf("DH key exchange failed: %w", err)
	}

	var sharedArr [KeySize]byte
	copy(sharedArr[:], shared)
	return sharedArr, nil
}

// Wipe securely zeroizes a slice of sensitive bytes
func Wipe(b []byte) {
	for i := range b {
		b[i] = 0
	}
}

// WipeKeypair securely zeroizes the private key in a keypair
func (kp *Keypair) Wipe() {
	Wipe(kp.PrivateKey[:])
}
