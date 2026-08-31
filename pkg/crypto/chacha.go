package crypto

import (
	"encoding/binary"
	"errors"
	"fmt"

	"golang.org/x/crypto/chacha20poly1305"
)

const (
	NonceSize = 12
)

var (
	ErrDecryptionFailed = errors.New("chacha20poly1305 decryption verification failed")
)

// ConstructNonce creates a 12-byte standard Noise nonce from a 64-bit sequence counter.
// Format: 4 bytes zero padding + 8 bytes LittleEndian sequence counter.
func ConstructNonce(counter uint64) [NonceSize]byte {
	var nonce [NonceSize]byte
	binary.LittleEndian.PutUint64(nonce[4:], counter)
	return nonce
}

// ChaCha20Poly1305Seal encrypts and authenticates plaintext using ChaCha20-Poly1305 AEAD.
func ChaCha20Poly1305Seal(key [KeySize]byte, nonce [NonceSize]byte, plaintext, additionalData []byte) ([]byte, error) {
	aead, err := chacha20poly1305.New(key[:])
	if err != nil {
		return nil, fmt.Errorf("failed to initialize AEAD cipher: %w", err)
	}

	return aead.Seal(nil, nonce[:], plaintext, additionalData), nil
}

// ChaCha20Poly1305Open decrypts and verifies ciphertext using ChaCha20-Poly1305 AEAD.
func ChaCha20Poly1305Open(key [KeySize]byte, nonce [NonceSize]byte, ciphertext, additionalData []byte) ([]byte, error) {
	aead, err := chacha20poly1305.New(key[:])
	if err != nil {
		return nil, fmt.Errorf("failed to initialize AEAD cipher: %w", err)
	}

	plaintext, err := aead.Open(nil, nonce[:], ciphertext, additionalData)
	if err != nil {
		return nil, ErrDecryptionFailed
	}

	return plaintext, nil
}
