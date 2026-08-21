# Sovereign Proxy (OCI VPN)

Questo repository contiene l'infrastruttura as code e i manuali operativi (S.O.A.P.) per il proxy anti-censura su Oracle Cloud Infrastructure (OCI).

## Componenti Principali
- **Oracle Cloud ARM A1.Flex** (Ubuntu 24.04 Minimal)
- **VLESS + REALITY + XTLS-Vision** (tramite 3x-ui)
- **Tailscale** (Exit Node / Mesh network verso Homelab)
- **Nginx** (Decoy site per Honeypot e Subscription proxy)
- **Automazioni** (GeoIP update, Anti-idle, Healthchecks, DuckDNS)

## Manuale Operativo
Fai riferimento al file `SOAP_6.2_SOVEREIGN_ULTIMATE.md` per la procedura completa di disaster recovery, configurazione e hardening del server.

## Sicurezza
**ATTENZIONE**: Non caricare mai chiavi SSH (`.key`) o database in chiaro in questo repository.
