# E2E Test Infra: Sovereign Proxy v4.0

## Test Philosophy
- Opaque-box, requirement-driven. Derives from user requirements in ORIGINAL_REQUEST.md.
- Multi-tier methodology:
  - **Tier 1**: Feature Coverage (>=5 test cases per feature across all 23 core features = 115+ tests)
  - **Tier 2**: Boundary, Edge & Corner Cases (>=5 test cases per feature = 115+ tests)
  - **Tier 3**: Cross-Feature Interactions & Pairwise Combinations (>=23 interaction tests)
  - **Tier 4**: Real-World Application & Workload Scenarios (>=15 comprehensive scenarios)
  - **Tier 5**: Adversarial Coverage Hardening & White-Box Integrity Audits (Fuzzing, Chaos, Anti-Cheat, Packet Capture Analysis)

## Feature Inventory & Test Coverage
| # | Feature | Category | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|----------|:------:|:------:|:------:|:------:|
| 1 | VLESS/REALITY Camouflage | Security/Proxy | 5 | 5 | ✓ | ✓ |
| 2 | Decoy Web Engine | Camouflage | 5 | 5 | ✓ | ✓ |
| 3 | Dynamic DNS & Discovery | Ops/Network | 5 | 5 | ✓ | ✓ |
| 4 | Parameterized Revocation | Security | 5 | 5 | ✓ | ✓ |
| 5 | DB Injector & Routing | Ops/Storage | 5 | 5 | ✓ | ✓ |
| 6 | Master Setup Console | Management | 5 | 5 | ✓ | ✓ |
| 7 | Active Defense Honeypot | Security | 5 | 5 | ✓ | ✓ |
| 8 | Multi-Factor Secrets | Security | 5 | 5 | ✓ | ✓ |
| 9 | Rootless Container Runtime | Security | 5 | 5 | ✓ | ✓ |
| 10 | Host Hardening & Cleanup | Ops/Security | 5 | 5 | ✓ | ✓ |
| 11 | Noise Cryptographic Plane | Mesh Core | 5 | 5 | ✓ | ✓ |
| 12 | DirectFrame SVRN Framing | Protocol | 5 | 5 | ✓ | ✓ |
| 13 | Camouflaged DERP-v4 Relay | Transport | 5 | 5 | ✓ | ✓ |
| 14 | Adaptive Disco-v4 NAT | Traversal | 5 | 5 | ✓ | ✓ |
| 15 | Sandboxed Client Bridge | Mesh Egress | 5 | 5 | ✓ | ✓ |
| 16 | Multi-Mode Routing Engine | Routing | 5 | 5 | ✓ | ✓ |
| 17 | Unified Multi-Cloud Schema | Infrastructure | 5 | 5 | ✓ | ✓ |
| 18 | Multi-Cloud IaC Modules | Infrastructure | 5 | 5 | ✓ | ✓ |
| 19 | Universal Node Bootstrap | Automation | 5 | 5 | ✓ | ✓ |
| 20 | Kubernetes Helm Chart | Orchestration | 5 | 5 | ✓ | ✓ |
| 21 | K8s Kustomize Overlays | Cloud Native | 5 | 5 | ✓ | ✓ |
| 22 | GitOps Branch Migration | DevOps | 5 | 5 | ✓ | ✓ |
| 23 | Production CI/CD Fleet | Quality/Release| 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Test Runner**: Python 3 `unittest` test discovery and custom bash test runners (`tests/legacy_compat/run_all_legacy_tests.sh`, `tests/e2e/runner.py`).
- **Legacy Compatibility Suite**: `tests/legacy_compat/` (20-point parity, SQLi fuzzing, secret leak scanner, rootless Docker verification).
- **E2E Test Suites**:
  - `tests/e2e/tier1_features/`: 23 feature test suites (115 tests).
  - `tests/e2e/tier2_boundaries/`: 23 boundary & corner case suites (115 tests).
  - `tests/e2e/tier3_combinations/`: Pairwise and multi-feature interaction suites (25 tests).
  - `tests/e2e/tier4_scenarios/`: Real-world end-to-end workload and failover simulations (26 tests).
  - `tests/e2e/tier5_adversarial/`: High-stress fuzzing, memory leak checks, replay attack simulations, and integrity forensics (30 tests).
- Total Suite Count: 311+ automated test cases.
