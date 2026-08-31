"""
Sovereign Proxy v4.0 - Multi-Node Virtual Mesh Harness (mock_mesh.py)
Implements simulated Control Plane, DERP-v4 Relay Swarm, Mock Client Exit Nodes,
and cryptographic wire-format frames (Direct Frame, DERP Frame, Onion Cell).
"""

import os
import struct
import hashlib
import hmac
import time
import socket
import ipaddress
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Any, Set


DIRECT_MAGIC = 0x534F5652  # 'SOVR' in ASCII
ONION_CELL_SIZE = 1420
OVERLAY_CIDR = "100.64.0.0/10"


class NodeCapability(Enum):
    CLIENT = "client"
    EGRESS = "egress"
    RELAY = "relay"
    CONTROL = "control"


class OnionCommand(Enum):
    CREATE = 0x01
    CREATED = 0x02
    RELAY = 0x03
    DESTROY = 0x04
    DATA = 0x05


class DERPPacketType(Enum):
    CLIENT_INFO = 0x01
    SERVER_KEY = 0x02
    PACKET = 0x03
    KEEP_ALIVE = 0x04
    HEALTH_PROBE = 0x05
    CLOSE = 0x06


@dataclass
class NodeGeoIP:
    country_code: str  # ISO-3166-1 alpha-2 e.g. 'US', 'DE', 'JP', 'SG', 'CH', 'NL'
    city: str
    latitude: float
    longitude: float
    asn: int = 13335
    as_org: str = "Cloudflare Inc"


@dataclass
class DirectFrame:
    magic: int = DIRECT_MAGIC
    nonce: bytes = field(default_factory=lambda: os.urandom(12))
    sender_pubkey: bytes = field(default_factory=lambda: os.urandom(32))
    payload: bytes = b""
    aead_tag: bytes = field(default_factory=lambda: os.urandom(16))

    def serialize(self, key: Optional[bytes] = None) -> bytes:
        """
        Direct Frame Wire Format:
        [Magic: 4B (0x534F5652)] [Nonce: 12B] [SenderPubKey: 32B] [PayloadLength: 2B] [AEAD Tag: 16B] [Ciphertext: N-B]
        """
        payload_len = len(self.payload)
        if payload_len > 65535:
            raise ValueError(f"Payload too large for Direct Frame: {payload_len} bytes")

        # AEAD tag calculation (HMAC-SHA256 truncated to 16 bytes over header + payload)
        calc_tag = self.aead_tag
        if key:
            header_prefix = struct.pack(">I", self.magic) + self.nonce + self.sender_pubkey + struct.pack(">H", payload_len)
            calc_tag = hmac.new(key, header_prefix + self.payload, hashlib.sha256).digest()[:16]

        header = struct.pack(">I", self.magic) + self.nonce + self.sender_pubkey + struct.pack(">H", payload_len) + calc_tag
        return header + self.payload

    @classmethod
    def parse(cls, data: bytes, key: Optional[bytes] = None) -> "DirectFrame":
        if len(data) < 66:
            raise ValueError(f"Direct frame too short ({len(data)} < 66 bytes)")
        magic, = struct.unpack(">I", data[0:4])
        if magic != DIRECT_MAGIC:
            raise ValueError(f"Invalid Direct Frame magic: {hex(magic)} != {hex(DIRECT_MAGIC)}")
        nonce = data[4:16]
        sender_pubkey = data[16:48]
        payload_len, = struct.unpack(">H", data[48:50])
        aead_tag = data[50:66]
        payload = data[66:66 + payload_len]

        if len(payload) != payload_len:
            raise ValueError(f"Direct frame payload truncated: expected {payload_len}, got {len(payload)}")

        if key:
            header_prefix = struct.pack(">I", magic) + nonce + sender_pubkey + struct.pack(">H", payload_len)
            expected_tag = hmac.new(key, header_prefix + payload, hashlib.sha256).digest()[:16]
            if not hmac.compare_digest(aead_tag, expected_tag):
                raise ValueError("Direct frame AEAD authentication verification failed")

        return cls(magic=magic, nonce=nonce, sender_pubkey=sender_pubkey, payload=payload, aead_tag=aead_tag)


@dataclass
class DERPFrame:
    packet_type: int
    dest_pubkey: bytes  # 32 bytes
    payload: bytes = b""

    def serialize(self) -> bytes:
        """
        DERP Frame Wire Format:
        [PacketType: 1B] [DestPubKey: 32B] [FrameLen: 4B] [EncryptedPayload: N-B]
        """
        if len(self.dest_pubkey) != 32:
            raise ValueError(f"DestPubKey must be 32 bytes, got {len(self.dest_pubkey)}")
        frame_len = len(self.payload)
        header = struct.pack(">B", self.packet_type) + self.dest_pubkey + struct.pack(">I", frame_len)
        return header + self.payload

    @classmethod
    def parse(cls, data: bytes) -> "DERPFrame":
        if len(data) < 37:
            raise ValueError(f"DERP frame too short ({len(data)} < 37 bytes)")
        packet_type, = struct.unpack(">B", data[0:1])
        dest_pubkey = data[1:33]
        frame_len, = struct.unpack(">I", data[33:37])
        payload = data[37:37 + frame_len]
        if len(payload) != frame_len:
            raise ValueError(f"DERP payload truncated: expected {frame_len}, got {len(payload)}")
        return cls(packet_type=packet_type, dest_pubkey=dest_pubkey, payload=payload)


@dataclass
class OnionCell:
    circuit_id: int
    command: int  # OnionCommand
    layer_crypto_header: bytes = field(default_factory=lambda: os.urandom(64))
    payload: bytes = b""  # Max 1335 bytes
    hmac_tag: bytes = field(default_factory=lambda: os.urandom(16))

    def serialize(self, key: Optional[bytes] = None) -> bytes:
        """
        Onion Cell Wire Format: Fixed 1420-byte cell
        [CircuitID: 4B] [Command: 1B] [LayerCryptoHeader: 64B] [Payload: 1335B] [HMAC: 16B]
        """
        if len(self.layer_crypto_header) != 64:
            raise ValueError(f"LayerCryptoHeader must be 64 bytes, got {len(self.layer_crypto_header)}")
        
        # Pad or truncate payload to exactly 1335 bytes
        padded_payload = self.payload.ljust(1335, b"\x00")[:1335]
        
        body_without_hmac = (
            struct.pack(">I", self.circuit_id)
            + struct.pack(">B", self.command)
            + self.layer_crypto_header
            + padded_payload
        )
        
        tag = self.hmac_tag
        if key:
            tag = hmac.new(key, body_without_hmac, hashlib.sha256).digest()[:16]
            
        full_cell = body_without_hmac + tag
        if len(full_cell) != ONION_CELL_SIZE:
            raise ValueError(f"Onion cell corrupted: size {len(full_cell)} != {ONION_CELL_SIZE}")
        return full_cell

    @classmethod
    def parse(cls, data: bytes, key: Optional[bytes] = None) -> "OnionCell":
        if len(data) != ONION_CELL_SIZE:
            raise ValueError(f"Invalid Onion cell size: {len(data)} != {ONION_CELL_SIZE}")
        circuit_id, = struct.unpack(">I", data[0:4])
        command, = struct.unpack(">B", data[4:5])
        layer_crypto_header = data[5:69]
        padded_payload = data[69:1404]
        hmac_tag = data[1404:1420]

        if key:
            body_without_hmac = data[0:1404]
            expected_tag = hmac.new(key, body_without_hmac, hashlib.sha256).digest()[:16]
            if not hmac.compare_digest(hmac_tag, expected_tag):
                raise ValueError("Onion cell HMAC authentication failed")

        return cls(
            circuit_id=circuit_id,
            command=command,
            layer_crypto_header=layer_crypto_header,
            payload=padded_payload.rstrip(b"\x00"),
            hmac_tag=hmac_tag,
        )


class MockControlPlane:
    """
    Simulates the Sovereign Proxy Control Plane:
    - Node registration with Curve25519 public keys & overlay VIP assignment (100.64.0.0/10)
    - Topology sync & peer discovery
    - Cryptographic epoch distribution & rekeying
    - Peer health & quota monitoring
    """

    def __init__(self, cluster_name: str = "sovereign-mesh-prod"):
        self.cluster_name = cluster_name
        self.lock = threading.RLock()
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.overlay_network = ipaddress.ip_network(OVERLAY_CIDR)
        self.base_ip_int = int(self.overlay_network.network_address)
        self.next_ip_idx = 10  # Reserve first 10 for control/relays
        self.epoch = 1
        self.relay_endpoints: List[str] = [
            "derp-us-east.sovereign.mesh:443",
            "derp-eu-central.sovereign.mesh:443",
            "derp-ap-northeast.sovereign.mesh:443",
        ]
        self.revoked_tokens: Set[str] = set()

    def register_node(
        self,
        node_id: str,
        pubkey: bytes,
        capabilities: List[NodeCapability],
        geoip: NodeGeoIP,
        stun_endpoints: Optional[List[str]] = None,
        auth_token: str = "valid-mesh-secret-token",
    ) -> Dict[str, Any]:
        with self.lock:
            if auth_token in self.revoked_tokens or not auth_token:
                raise PermissionError("Registration rejected: Invalid or revoked authentication token")
            
            if len(pubkey) != 32:
                raise ValueError("Public key must be 32 bytes Curve25519")

            if node_id in self.nodes:
                assigned_ip = self.nodes[node_id]["overlay_ip"]
            else:
                if self.next_ip_idx >= self.overlay_network.num_addresses - 2:
                    raise OverflowError("Overlay VIP pool exhausted")
                assigned_ip = str(ipaddress.ip_address(self.base_ip_int + self.next_ip_idx))
                self.next_ip_idx += 1

            node_record = {
                "node_id": node_id,
                "pubkey": pubkey,
                "capabilities": [c.value if isinstance(c, NodeCapability) else c for c in capabilities],
                "geoip": geoip,
                "stun_endpoints": stun_endpoints or ["stun.sovereign.mesh:3478"],
                "overlay_ip": assigned_ip,
                "registered_at": time.time(),
                "last_seen": time.time(),
                "status": "HEALTHY",
                "battery_pct": 100.0,
                "bandwidth_used_mb": 0.0,
                "bandwidth_limit_mb": 10240.0,  # 10 GB
                "epoch": self.epoch,
            }
            self.nodes[node_id] = node_record

            mesh_token = hashlib.sha256(f"{node_id}:{assigned_ip}:{self.epoch}".encode()).hexdigest()
            return {
                "status": "SUCCESS",
                "node_id": node_id,
                "overlay_ip": assigned_ip,
                "mesh_token": mesh_token,
                "relay_swarms": self.relay_endpoints,
                "epoch": self.epoch,
            }

    def sync_topology(self, requester_node_id: str) -> Dict[str, Any]:
        with self.lock:
            if requester_node_id not in self.nodes:
                raise KeyError(f"Node {requester_node_id} not registered")
            
            peers = {}
            for nid, rec in self.nodes.items():
                if nid == requester_node_id:
                    continue
                peers[nid] = {
                    "pubkey": rec["pubkey"].hex(),
                    "overlay_ip": rec["overlay_ip"],
                    "capabilities": rec["capabilities"],
                    "country": rec["geoip"].country_code,
                    "status": rec["status"],
                    "stun_endpoints": rec["stun_endpoints"],
                }
            
            return {
                "epoch": self.epoch,
                "cluster_name": self.cluster_name,
                "relays": self.relay_endpoints,
                "peers": peers,
            }

    def report_health(
        self,
        node_id: str,
        battery_pct: Optional[float] = None,
        bandwidth_used_mb: Optional[float] = None,
        nat_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self.lock:
            if node_id not in self.nodes:
                raise KeyError(f"Node {node_id} not found")
            
            rec = self.nodes[node_id]
            rec["last_seen"] = time.time()
            if battery_pct is not None:
                rec["battery_pct"] = battery_pct
                if battery_pct < 15.0:
                    rec["status"] = "DEGRADED_BATTERY"
                elif rec["status"] == "DEGRADED_BATTERY":
                    rec["status"] = "HEALTHY"

            if bandwidth_used_mb is not None:
                rec["bandwidth_used_mb"] = bandwidth_used_mb
                if bandwidth_used_mb >= rec["bandwidth_limit_mb"]:
                    rec["status"] = "QUOTA_EXHAUSTED"

            return {
                "status": "ACK",
                "node_status": rec["status"],
                "epoch": self.epoch,
            }

    def rotate_epoch(self) -> int:
        with self.lock:
            self.epoch += 1
            for rec in self.nodes.values():
                rec["epoch"] = self.epoch
            return self.epoch

    def revoke_node(self, node_id: str):
        with self.lock:
            if node_id in self.nodes:
                del self.nodes[node_id]

    def revoke_token(self, token: str):
        with self.lock:
            self.revoked_tokens.add(token)


class MockDERPRelay:
    """
    Simulates a high-performance camouflaged DERP-v4 Relay Server:
    - Encapsulated packets in TLS 1.3 / WebSocket framing
    - Peer destination routing via 32-byte Curve25519 PubKey
    - Packet relaying and latency/loss metrics
    """

    def __init__(self, relay_id: str, region: str = "us-east"):
        self.relay_id = relay_id
        self.region = region
        self.lock = threading.RLock()
        self.connected_peers: Dict[bytes, Any] = {}  # pubkey -> peer connection state
        self.packet_log: List[Dict[str, Any]] = []
        self.is_running = True

    def register_client(self, client_pubkey: bytes, client_conn: Any = None):
        with self.lock:
            if len(client_pubkey) != 32:
                raise ValueError("Client pubkey must be 32 bytes")
            self.connected_peers[client_pubkey] = {
                "conn": client_conn,
                "registered_at": time.time(),
                "last_active": time.time(),
                "bytes_relayed": 0,
            }

    def relay_packet(self, sender_pubkey: bytes, dest_pubkey: bytes, encrypted_payload: bytes) -> bool:
        with self.lock:
            if not self.is_running:
                return False
            
            frame = DERPFrame(
                packet_type=DERPPacketType.PACKET.value,
                dest_pubkey=dest_pubkey,
                payload=encrypted_payload,
            )
            raw_bytes = frame.serialize()

            self.packet_log.append({
                "timestamp": time.time(),
                "sender": sender_pubkey.hex(),
                "dest": dest_pubkey.hex(),
                "size": len(raw_bytes),
                "relayed": dest_pubkey in self.connected_peers,
            })

            if dest_pubkey in self.connected_peers:
                self.connected_peers[dest_pubkey]["bytes_relayed"] += len(raw_bytes)
                self.connected_peers[dest_pubkey]["last_active"] = time.time()
                return True
            return False

    def close(self):
        with self.lock:
            self.is_running = False
            self.connected_peers.clear()


class MockClientExitNode:
    """
    Simulates a Client-Bridge Exit Node with userspace netstack isolation:
    - GeoIP tagging (US, DE, JP, SG, CH, NL)
    - Bogon / RFC 1918 destination dropping
    - Port filter (blocks 25, 445, 137, 138, 139)
    - SOCKS5 / HTTP CONNECT command handling
    - Battery and quota throttling
    """

    BOGON_NETWORKS = [
        ipaddress.ip_network("0.0.0.0/8"),
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("169.254.0.0/16"),
        ipaddress.ip_network("224.0.0.0/4"),
        ipaddress.ip_network("240.0.0.0/4"),
    ]
    RESTRICTED_PORTS = {25, 445, 137, 138, 139}

    def __init__(
        self,
        node_id: str,
        geoip: NodeGeoIP,
        overlay_ip: str = "100.64.0.25",
        battery_pct: float = 100.0,
        bandwidth_limit_mb: float = 10240.0,
    ):
        self.node_id = node_id
        self.geoip = geoip
        self.overlay_ip = overlay_ip
        self.pubkey = os.urandom(32)
        self.privkey = os.urandom(32)
        self.battery_pct = battery_pct
        self.bandwidth_used_mb = 0.0
        self.bandwidth_limit_mb = bandwidth_limit_mb
        self.active_sessions: Dict[str, Any] = {}
        self.packet_log: List[Dict[str, Any]] = []

    def handle_egress_request(
        self,
        client_node_id: str,
        dest_ip: str,
        dest_port: int,
        protocol: str = "TCP",
        payload: bytes = b"",
    ) -> Tuple[bool, str, bytes]:
        """
        Simulates egress request via sandboxed netstack.
        Returns: (success, message, response_data)
        """
        # 1. Quota / Battery check
        if self.battery_pct < 15.0:
            return False, "DROP_BATTERY_LOW", b""
        if self.bandwidth_used_mb >= self.bandwidth_limit_mb:
            return False, "DROP_QUOTA_EXHAUSTED", b""

        # 2. Port restrictions
        if dest_port in self.RESTRICTED_PORTS:
            return False, f"DROP_RESTRICTED_PORT_{dest_port}", b""

        # 3. RFC 1918 / Bogon Subnet Filter
        try:
            ip_obj = ipaddress.ip_address(dest_ip)
            for bogon in self.BOGON_NETWORKS:
                if ip_obj in bogon:
                    return False, f"DROP_RFC1918_BOGON_{bogon}", b""
        except ValueError:
            # If domain name, DoH resolution check applies
            if dest_ip.endswith(".local") or dest_ip.endswith(".internal"):
                return False, "DROP_SPLIT_HORIZON_LEAK", b""

        # Egress allowed: simulate upstream response
        data_len = len(payload)
        self.bandwidth_used_mb += (data_len + 128) / (1024 * 1024)
        resp_data = f"HTTP/1.1 200 OK\r\nServer: MockExit-{self.geoip.country_code}\r\nX-Egress-Node: {self.node_id}\r\n\r\nHello from {self.geoip.country_code}".encode()
        
        self.packet_log.append({
            "client": client_node_id,
            "dest": f"{dest_ip}:{dest_port}",
            "proto": protocol,
            "bytes_tx": len(payload),
            "bytes_rx": len(resp_data),
            "timestamp": time.time(),
        })

        return True, "FORWARDED", resp_data


class MockMeshNetwork:
    """
    Unified virtual mesh environment:
    - Combines MockControlPlane, multi-region MockDERPRelay, and GeoIP tagged MockClientExitNodes.
    - Provides routing via Country code, Specific Host ID, and 3-Hop Onion circuits.
    """

    SUPPORTED_COUNTRIES = ["US", "DE", "JP", "SG", "CH", "NL"]

    def __init__(self, cluster_name: str = "sovereign-mesh-prod"):
        self.control_plane = MockControlPlane(cluster_name=cluster_name)
        self.relays: Dict[str, MockDERPRelay] = {
            "us-east": MockDERPRelay("derp-us-east", "us-east"),
            "eu-central": MockDERPRelay("derp-eu-central", "eu-central"),
            "ap-northeast": MockDERPRelay("derp-ap-northeast", "ap-northeast"),
        }
        self.exit_nodes: Dict[str, MockClientExitNode] = {}
        self._init_default_exit_nodes()

    def _init_default_exit_nodes(self):
        countries_meta = [
            ("US", "Ashburn", 39.0438, -77.4874),
            ("DE", "Frankfurt", 50.1109, 8.6821),
            ("JP", "Tokyo", 35.6762, 139.6503),
            ("SG", "Singapore", 1.3521, 103.8198),
            ("CH", "Zurich", 47.3769, 8.5417),
            ("NL", "Amsterdam", 52.3676, 4.9041),
        ]
        for country, city, lat, lon in countries_meta:
            node_id = f"exit-{country.lower()}-01"
            geoip = NodeGeoIP(country_code=country, city=city, latitude=lat, longitude=lon)
            exit_node = MockClientExitNode(node_id=node_id, geoip=geoip)
            self.exit_nodes[node_id] = exit_node
            
            # Register in control plane
            self.control_plane.register_node(
                node_id=node_id,
                pubkey=exit_node.pubkey,
                capabilities=[NodeCapability.CLIENT, NodeCapability.EGRESS],
                geoip=geoip,
            )
            # Register with relays
            for relay in self.relays.values():
                relay.register_client(exit_node.pubkey)

    def route_by_country(self, country_code: str) -> Optional[MockClientExitNode]:
        """Finds an active healthy exit node for the requested country."""
        country_code = country_code.upper()
        for node in self.exit_nodes.values():
            if node.geoip.country_code == country_code:
                # Check health in control plane
                rec = self.control_plane.nodes.get(node.node_id)
                if rec and rec["status"] == "HEALTHY" and node.battery_pct >= 15.0:
                    return node
        return None

    def route_by_host_id(self, host_id: str) -> Optional[MockClientExitNode]:
        """Finds a specific exit node by Host ID."""
        node = self.exit_nodes.get(host_id)
        if node:
            rec = self.control_plane.nodes.get(node.node_id)
            if rec and rec["status"] == "HEALTHY":
                return node
        return None

    def build_onion_circuit(self, circuit_id: int, hops: List[MockClientExitNode]) -> List[bytes]:
        """
        Builds a 3-Hop Onion Circuit using fixed 1420-byte cells.
        Returns serialized cells layered from Entry -> Middle -> Exit.
        """
        if len(hops) != 3:
            raise ValueError("3-Hop Onion Circuit requires exactly 3 nodes (Entry, Middle, Exit)")
        
        # Layer encryption simulation: Exit (hop 3) -> Middle (hop 2) -> Entry (hop 1)
        raw_payload = b"GET /privacy HTTP/1.1\r\nHost: target.onion\r\n\r\n"
        
        # Layer 3 (Exit)
        cell3 = OnionCell(circuit_id=circuit_id, command=OnionCommand.DATA.value, payload=raw_payload)
        enc3 = cell3.serialize(key=hops[2].privkey)

        # Layer 2 (Middle)
        cell2 = OnionCell(circuit_id=circuit_id, command=OnionCommand.RELAY.value, payload=enc3[:1335])
        enc2 = cell2.serialize(key=hops[1].privkey)

        # Layer 1 (Entry)
        cell1 = OnionCell(circuit_id=circuit_id, command=OnionCommand.RELAY.value, payload=enc2[:1335])
        enc1 = cell1.serialize(key=hops[0].privkey)

        return [enc1, enc2, enc3]
