"""
Sovereign Proxy v4.0 - Network Simulator & NAT Traversal Emulator (net_sim.py)
Simulates realistic WAN conditions (latency, jitter, loss, corruption) and comprehensive
NAT behaviors (Full Cone, Restricted Cone, Port Restricted, Symmetric Sequential, Symmetric Random).
Implements STUN classification and Disco-v4 port prediction & spraying.
"""

import random
import time
import struct
import socket
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Any, Set


class NATType(Enum):
    OPEN_INTERNET = "open_internet"
    FULL_CONE = "full_cone"
    RESTRICTED_CONE = "restricted_cone"
    PORT_RESTRICTED_CONE = "port_restricted_cone"
    SYMMETRIC_SEQUENTIAL = "symmetric_sequential"
    SYMMETRIC_RANDOM = "symmetric_random"


@dataclass
class NATBehavior:
    nat_type: NATType
    public_ip: str = "198.51.100.1"
    base_port: int = 40000
    port_step: int = 1  # For sequential symmetric NAT
    allowlist_ips: Set[str] = field(default_factory=set)
    allowlist_ports: Set[Tuple[str, int]] = field(default_factory=set)
    mapping_table: Dict[Tuple[str, int, str, int], int] = field(default_factory=dict)
    last_assigned_port: int = 40000

    def get_mapped_endpoint(self, private_ip: str, private_port: int, dest_ip: str, dest_port: int) -> Tuple[str, int]:
        """Translates private (ip, port) + destination (ip, port) to public (ip, port)."""
        if self.nat_type == NATType.OPEN_INTERNET:
            return private_ip, private_port

        mapping_key = (private_ip, private_port, dest_ip, dest_port)

        if self.nat_type in (NATType.FULL_CONE, NATType.RESTRICTED_CONE, NATType.PORT_RESTRICTED_CONE):
            # Endpoint Independent Mapping: same public port regardless of destination
            generic_key = (private_ip, private_port, "0.0.0.0", 0)
            if generic_key not in self.mapping_table:
                self.last_assigned_port += 1
                self.mapping_table[generic_key] = self.last_assigned_port
            public_port = self.mapping_table[generic_key]
        elif self.nat_type == NATType.SYMMETRIC_SEQUENTIAL:
            if mapping_key not in self.mapping_table:
                self.last_assigned_port += self.port_step
                self.mapping_table[mapping_key] = self.last_assigned_port
            public_port = self.mapping_table[mapping_key]
        elif self.nat_type == NATType.SYMMETRIC_RANDOM:
            if mapping_key not in self.mapping_table:
                self.mapping_table[mapping_key] = random.randint(30000, 65000)
            public_port = self.mapping_table[mapping_key]
        else:
            public_port = private_port

        # Update filtering allowlists
        self.allowlist_ips.add(dest_ip)
        self.allowlist_ports.add((dest_ip, dest_port))

        return self.public_ip, public_port

    def can_receive_from(self, sender_public_ip: str, sender_public_port: int) -> bool:
        """Determines if inbound packet is allowed by NAT filtering rules."""
        if self.nat_type in (NATType.OPEN_INTERNET, NATType.FULL_CONE):
            return True
        elif self.nat_type == NATType.RESTRICTED_CONE:
            return sender_public_ip in self.allowlist_ips
        elif self.nat_type in (NATType.PORT_RESTRICTED_CONE, NATType.SYMMETRIC_SEQUENTIAL, NATType.SYMMETRIC_RANDOM):
            return (sender_public_ip, sender_public_port) in self.allowlist_ports
        return False


@dataclass
class SimulatedEndpoint:
    node_id: str
    private_ip: str
    private_port: int
    nat: NATBehavior


class NetworkSimulator:
    """
    Simulates WAN network conditions between endpoints:
    - Configurable latency (ms) and jitter (ms)
    - Packet loss rate (0.0 to 1.0)
    - Bit corruption simulation
    """

    def __init__(
        self,
        base_latency_ms: float = 20.0,
        jitter_ms: float = 5.0,
        packet_loss_rate: float = 0.0,
        corruption_rate: float = 0.0,
        seed: Optional[int] = 42,
    ):
        self.base_latency_ms = base_latency_ms
        self.jitter_ms = jitter_ms
        self.packet_loss_rate = packet_loss_rate
        self.corruption_rate = corruption_rate
        if seed is not None:
            random.seed(seed)

    def calculate_transit_delay(self) -> float:
        """Calculates simulated delivery delay in seconds."""
        jitter = random.uniform(-self.jitter_ms, self.jitter_ms)
        delay_ms = max(1.0, self.base_latency_ms + jitter)
        return delay_ms / 1000.0

    def transmit(
        self,
        sender: SimulatedEndpoint,
        receiver: SimulatedEndpoint,
        payload: bytes,
    ) -> Tuple[bool, Optional[bytes], str]:
        """
        Simulates packet transmission through NATs and loss/corruption models.
        Returns: (delivered, received_payload, diagnostic_status)
        """
        # 1. Packet loss check
        if self.packet_loss_rate > 0 and random.random() < self.packet_loss_rate:
            return False, None, "DROPPED_PACKET_LOSS"

        # 2. Source NAT mapping
        src_pub_ip, src_pub_port = sender.nat.get_mapped_endpoint(
            sender.private_ip, sender.private_port, receiver.nat.public_ip, receiver.nat.last_assigned_port
        )

        # 3. Destination NAT filtering check
        if not receiver.nat.can_receive_from(src_pub_ip, src_pub_port):
            return False, None, "BLOCKED_BY_DEST_NAT_FILTER"

        # 4. Corruption simulation
        data_to_deliver = bytearray(payload)
        if self.corruption_rate > 0 and random.random() < self.corruption_rate:
            if len(data_to_deliver) > 0:
                flip_idx = random.randint(0, len(data_to_deliver) - 1)
                data_to_deliver[flip_idx] ^= 0xFF
                return True, bytes(data_to_deliver), "CORRUPTED_IN_TRANSIT"

        return True, bytes(data_to_deliver), "DELIVERED_OK"


class STUNSimulator:
    """
    Simulates RFC 3489 / RFC 5389 STUN NAT Classification.
    """

    def __init__(self, primary_ip: str = "203.0.113.1", secondary_ip: str = "203.0.113.2", port: int = 3478):
        self.primary_ip = primary_ip
        self.secondary_ip = secondary_ip
        self.port = port

    def classify_nat(self, endpoint: SimulatedEndpoint) -> NATType:
        """Runs STUN classification tests against simulated endpoint NAT."""
        # Test I: Probe primary IP
        pub_ip1, pub_port1 = endpoint.nat.get_mapped_endpoint(
            endpoint.private_ip, endpoint.private_port, self.primary_ip, self.port
        )

        # Check if mapped address matches private address
        if pub_ip1 == endpoint.private_ip and pub_port1 == endpoint.private_port:
            return NATType.OPEN_INTERNET

        # Test I from secondary IP to see if mapping changes (Endpoint Independent vs Dependent)
        pub_ip2, pub_port2 = endpoint.nat.get_mapped_endpoint(
            endpoint.private_ip, endpoint.private_port, self.secondary_ip, self.port
        )

        if pub_port1 != pub_port2:
            # Symmetric NAT
            if endpoint.nat.nat_type == NATType.SYMMETRIC_SEQUENTIAL:
                return NATType.SYMMETRIC_SEQUENTIAL
            return NATType.SYMMETRIC_RANDOM

        # Mapping is Endpoint Independent (Cone NAT)
        if endpoint.nat.nat_type == NATType.FULL_CONE:
            return NATType.FULL_CONE
        elif endpoint.nat.nat_type == NATType.RESTRICTED_CONE:
            return NATType.RESTRICTED_CONE
        else:
            return NATType.PORT_RESTRICTED_CONE


class DiscoV4Simulator:
    """
    Simulates the Sovereign Proxy Disco-v4 Adaptive NAT Traversal Engine:
    - Direct UDP hole punch for Cone NATs
    - Sequential port delta prediction & multi-port spraying for Symmetric NATs
    - Seamless DERP fallback if hole punching fails
    """

    @classmethod
    def attempt_traversal(
        cls,
        node_a: SimulatedEndpoint,
        node_b: SimulatedEndpoint,
        net_sim: Optional[NetworkSimulator] = None,
        spray_count: int = 16,
    ) -> Dict[str, Any]:
        sim = net_sim or NetworkSimulator()
        
        # 1. Classify NATs
        stun = STUNSimulator()
        nat_a = stun.classify_nat(node_a)
        nat_b = stun.classify_nat(node_b)

        # If both are Symmetric Random, direct hole punching is impossible -> DERP Fallback
        if nat_a == NATType.SYMMETRIC_RANDOM and nat_b == NATType.SYMMETRIC_RANDOM:
            return {
                "success": True,
                "strategy": "DERP_RELAY_FALLBACK",
                "nat_a": nat_a.value,
                "nat_b": nat_b.value,
                "derp_fallback": True,
                "reason": "Symmetric-to-Symmetric random port collision requires camouflaged DERP-v4 relay",
            }

        # 2. Check if direct connection or cone-to-cone traversal works
        if nat_a not in (NATType.SYMMETRIC_SEQUENTIAL, NATType.SYMMETRIC_RANDOM) and \
           nat_b not in (NATType.SYMMETRIC_SEQUENTIAL, NATType.SYMMETRIC_RANDOM):
            pub_a_ip, pub_a_port = node_a.nat.get_mapped_endpoint(
                node_a.private_ip, node_a.private_port, node_b.nat.public_ip, node_b.nat.last_assigned_port
            )
            pub_b_ip, pub_b_port = node_b.nat.get_mapped_endpoint(
                node_b.private_ip, node_b.private_port, node_a.nat.public_ip, node_a.nat.last_assigned_port
            )

            node_a.nat.allowlist_ports.add((pub_b_ip, pub_b_port))
            node_b.nat.allowlist_ports.add((pub_a_ip, pub_a_port))

            delivered, _, _ = sim.transmit(node_a, node_b, b"DISCO_PING_A_TO_B")
            if delivered:
                return {
                    "success": True,
                    "strategy": "DIRECT_UDP_PUNCH",
                    "nat_a": nat_a.value,
                    "nat_b": nat_b.value,
                    "derp_fallback": False,
                    "endpoint_a": f"{pub_a_ip}:{pub_a_port}",
                    "endpoint_b": f"{pub_b_ip}:{pub_b_port}",
                }

        # 3. If either is Symmetric Sequential, simulate port prediction & spraying
        if nat_a == NATType.SYMMETRIC_SEQUENTIAL or nat_b == NATType.SYMMETRIC_SEQUENTIAL:
            pub_a_ip, pub_a_port = node_a.nat.get_mapped_endpoint(
                node_a.private_ip, node_a.private_port, node_b.nat.public_ip, node_b.nat.last_assigned_port
            )
            for offset in range(1, spray_count + 1):
                test_port = node_b.nat.last_assigned_port + (offset * node_b.nat.port_step)
                node_a.nat.allowlist_ports.add((node_b.nat.public_ip, test_port))
                node_b.nat.allowlist_ports.add((pub_a_ip, pub_a_port))

            delivered, _, _ = sim.transmit(node_a, node_b, b"DISCO_SPRAY_PACKET")
            if delivered:
                return {
                    "success": True,
                    "strategy": "SYMMETRIC_PORT_SPRAY",
                    "nat_a": nat_a.value,
                    "nat_b": nat_b.value,
                    "derp_fallback": False,
                    "sprayed_ports": spray_count,
                }

        # 4. Fallback to DERP
        return {
            "success": True,
            "strategy": "DERP_RELAY_FALLBACK",
            "nat_a": nat_a.value,
            "nat_b": nat_b.value,
            "derp_fallback": True,
            "reason": "Direct traversal failed; fallback to camouflaged DERP-v4 relay",
        }
