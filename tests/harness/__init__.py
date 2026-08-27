"""
Sovereign Proxy v4.0 - Multi-Node Virtual Mesh Test Harness
"""

from .mock_mesh import (
    MockControlPlane,
    MockDERPRelay,
    MockClientExitNode,
    MockMeshNetwork,
    DirectFrame,
    DERPFrame,
    OnionCell,
    NodeCapability,
    NodeGeoIP,
    OnionCommand,
    DERPPacketType,
    DIRECT_MAGIC,
    ONION_CELL_SIZE,
    OVERLAY_CIDR,
)
from .net_sim import (
    NetworkSimulator,
    NATType,
    NATBehavior,
    SimulatedEndpoint,
    STUNSimulator,
    DiscoV4Simulator,
)
from .leak_detector import (
    LeakDetector,
    DNSLeakDetector,
    RFC1918LeakDetector,
    PlaintextProbe,
    LeakScanResult,
)

__all__ = [
    "MockControlPlane",
    "MockDERPRelay",
    "MockClientExitNode",
    "MockMeshNetwork",
    "DirectFrame",
    "DERPFrame",
    "OnionCell",
    "NodeCapability",
    "NodeGeoIP",
    "OnionCommand",
    "DERPPacketType",
    "DIRECT_MAGIC",
    "ONION_CELL_SIZE",
    "OVERLAY_CIDR",
    "NetworkSimulator",
    "NATType",
    "NATBehavior",
    "SimulatedEndpoint",
    "STUNSimulator",
    "DiscoV4Simulator",
    "LeakDetector",
    "DNSLeakDetector",
    "RFC1918LeakDetector",
    "PlaintextProbe",
    "LeakScanResult",
]
