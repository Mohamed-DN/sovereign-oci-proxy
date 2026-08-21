# 🛡️ Sovereign OCI Proxy (Ultimate Edition)

![Sovereign Proxy](https://img.shields.io/badge/Status-Active-success.svg) ![Platform](https://img.shields.io/badge/Platform-Oracle_Cloud-red.svg) ![Protocol](https://img.shields.io/badge/Protocol-VLESS%2BReality-blue.svg) ![License](https://img.shields.io/badge/License-AGPL_3.0-green.svg)

**Sovereign OCI Proxy** è un'architettura completa e validata sul campo per costruire una fortezza anti-censura (VPN Proxy) utilizzando l'Always Free Tier di Oracle Cloud.

Il progetto è nato con un duplice scopo:
1. **Garantire libertà di comunicazione** e bypass della censura governativa (DPI) in reti ostili (es. Egitto, Cina, reti aziendali) camuffando il traffico come normali connessioni HTTPS verso server commerciali (es. AWS).
2. **Collegarsi in totale sicurezza al proprio Homelab** instradando il traffico decifrato verso una rete mesh sicura (Tailscale), agendo così da scudo esterno e da *Exit Node* senza dover mai esporre porte sul router di casa.

---

## 🏗️ Come Funziona l'Architettura
Il cuore del sistema ruota attorno a un'istanza Oracle ARM (A1.Flex) a costo zero. 
1. **L'ingresso (VLESS + REALITY):** Dal tuo telefono/PC invii traffico verso l'IP Oracle sulla porta 443. Ai firewall ostili sembrerà una normale navigazione TLS 1.3 crittografata verso `aws.amazon.com`.
2. **Lo smistamento (Xray):** Se sei tu (con UUID valido), Xray decifra la richiesta. Se è un bot o uno scanner governativo, la richiesta viene deviata silenziosamente a un sito civetta (Nginx Decoy).
3. **L'uscita (Internet o Homelab):** Le richieste dirette a Internet escono pulite dall'IP Oracle (o tramite Cloudflare WARP). Le richieste dirette al tuo Homelab (`*.internal` o IP di casa) vengono instradate dentro l'interfaccia `tailscale0` e recapitate al tuo server fisico.
4. **Le difese:** UFW blocca tutto tranne le porte strettamente necessarie. Fail2ban respinge i brute-force. Un Honeypot Python sulla porta 8080 cattura e banna gli scanner in tempo reale notificandoti via Ntfy. Uno script di *Anti-Idle* impedisce a Oracle di spegnere il server per inattività.

*Tutti i dettagli strutturali sono nella cartella `docs/` e nel manuale `SOAP_6.2_SOVEREIGN_ULTIMATE.md`.*

---

## 🛠️ Installazione Passo Passo (Quickstart)

> ⚠️ **ATTENZIONE SICUREZZA**: Questo repository è progettato per essere **Zero-Secrets**. Non includere mai chiavi SSH, password, UUID o token nei file. Qualsiasi dato sensibile deve essere caricato nel server al momento del deploy o conservato nel proprio gestore password (es. Vaultwarden).

1. **Pre-requisiti**: Crea un'istanza Ubuntu 24.04 ARM su OCI e apri le porte 2222, 443, 80 e 8080 nelle Security List (NON usare la porta 22 per SSH dopo il setup iniziale).
2. **Clona la repo**:
   ```bash
   git clone https://github.com/Mohamed-DN/sovereign-oci-proxy.git
   cd sovereign-oci-proxy
   ```
3. **Lancia il setup modulare**:
   All'interno della cartella `scripts/modules/` troverai i vari script per configurare il sistema a strati (Hardening, Decoy Nginx, Xray, ecc). Segui l'ordine cronologico descritto in `docs/FULL_GUIDE.md`.

---

## 🆘 Disaster Recovery: E se Oracle ci "frega"?
Oracle è nota per spegnere o cancellare istanze gratuite senza preavviso (reclamation). Questa architettura è progettata per **sopravvivere alla morte del server**. 

Il tempo di *Disaster Recovery* stimato è di **30 minuti**:
1. **Il Backup Asimmetrico:** Ogni notte alle 03:00, lo script di backup zippa il database degli utenti (`x-ui.db`), le configurazioni di routing e i siti civetta, li cripta con **GPG asimmetrico** (AES-256) usando solo la tua chiave pubblica, e carica il file blindato su Backblaze B2. 
2. **La Sicurezza:** Sul server Oracle NON è presente la chiave privata per decriptare i backup. Se un hacker compromette il server e ruba i file da Backblaze, troverà solo dati indecifrabili.
3. **Il Ripristino:** Se Oracle cancella il server:
   - Crei una nuova istanza (o usi Hetzner/AWS).
   - Scarichi l'ultimo backup cifrato `.gpg` da B2 sul tuo Mac/PC locale.
   - Lo decripti sul tuo computer usando la tua chiave privata.
   - Fai l'upload del file `x-ui.db` ripristinato sul nuovo server.
   - Tutti i tuoi utenti, profili, chiavi e rotte torneranno immediatamente funzionanti.

---

## 🚀 Roadmap e Release BETA (Automazione IaC)
Attualmente l'infrastruttura si basa su potenti shell script modulari (`bash`). 

**In arrivo nella v2.0 (BETA): Ansible & Terraform**
Stiamo lavorando per portare il progetto a un livello aziendale introducendo il supporto *Infrastructure as Code* (IaC):
- **Terraform:** Per fare il provisioning automatico dell'istanza su Oracle Cloud, configurare in automatico la VCN, le Security Lists (aprendo la porta 2222, 443 e 80) e associare l'IP pubblico, senza più fare click manuali sul portale Oracle.
- **Ansible:** Per eseguire in automatico tutto l'hardening dell'OS (Swap, BBR, SSH, Fail2ban, UFW, Honeypot) e deployare il proxy in modo completamente idempotente partendo dal server "vergine".

*Se vuoi contribuire all'automazione Terraform/Ansible, controlla i template in `.github/ISSUE_TEMPLATE/feature_request.md`.*

---
*Progetto nato per proteggere la privacy, i dati e il diritto alla connessione libera e neutrale.*
