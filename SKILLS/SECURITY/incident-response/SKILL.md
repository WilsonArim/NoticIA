---
name: Incident Response
description: Incident classification, response playbooks, communication templates, evidence preservation, and post-mortem processes
phase: 6
always_active: false
---

# Incident Response

## Incident Classification

### Severidade por impacto

**P1 - Critical (0-4 horas)**
- Breach confirmado de dados de usuario
- Indisponibilidade total do servico
- Unauthorized access ativo em sistemas criticos
- Ransomware/malware detectado em producao
- Comprometimento de credenciais admin

**P2 - High (4-24 horas)**
- Unauthorized access em sistema nao-critico
- Vazamento de dados confidenciais (interno)
- Degradacao significativa de performance
- Compromisso de conta privilegiada (sem acesso direto ainda)
- Vulnerability ativa sendo explorada

**P3 - Medium (1-7 dias)**
- Vulnerability descoberta (nao explorada)
- Anomalia suspeita em logs (inconclusive)
- Tentativas multiplas de forca bruta frustradas
- Possivel phishing targetado

**P4 - Low (1-30 dias)**
- Atualizacao de seguranca desnecessaria
- Anomalia menor em processamento
- Alertas de configuracao

## Response Playbooks

### Template generico de resposta

```markdown
# Incident Response Playbook: [Type]

## Trigger Indicators
- [Indicator 1]
- [Indicator 2]

## Immediate Actions (first 30 min)
1. [ ] Declare incident e notificar escalation chain
2. [ ] Gather initial evidence (screenshots, logs, timestamps)
3. [ ] Preserve evidence (snapshot, memory dump)
4. [ ] Isolate affected systems se necessario
5. [ ] Notify communication lead para template de resposta
6. [ ] Abrir incident ticket com rastreamento

## Investigation Phase (1-2 horas)
1. [ ] Timeline: Quando foi descoberto vs quando ocorreu
2. [ ] Scope: Quantos usuarios/sistemas afetados
3. [ ] Root cause: Como ocorreu (executar analise forense)
4. [ ] Data exposed: Quais dados foram acessados
5. [ ] Culprit: Quem/o que causou (interno vs externo)

## Containment Phase (parallel)
1. [ ] Revoke acesso se compromisso
2. [ ] Ativar protecoes adicionais (WAF, rate limits)
3. [ ] Desativar funcionalidades vulneraveis se necessario
4. [ ] Comunicar afetados de acordo com timeline regulatoria

## Recovery Phase
1. [ ] Patch vulnerability ou fixar root cause
2. [ ] Fazer deploy de fix
3. [ ] Monitorar para recorrencia
4. [ ] Schedule post-mortem em 2-5 dias

## Communication (paralelo)
- Usuarios afetados: [template interno]
- Media/publico: [template externo]
- Regulatory: [template GDPR/compliance]
```

### Data Breach Playbook

```
## Trigger
- Confirmacao de exfiltracacao de dados

## Immediate (0-2h)
1. Confirmar escopo e tipos de dados
   - PII (nomes, emails, CPF)?
   - Passwords (hashes ou plaintext)?
   - Payment info?
   - IP addresses?

2. Notificar:
   - CEO/Founder
   - Legal/Compliance Officer
   - PR lead
   - Engineering lead

3. Preservar evidencia:
   - Snapshot de databases afetados
   - Copy de logs (authentication, access, exfiltration)
   - Network captures (PCAP) de fluxos suspeitos
   - Screenshots de dashboards/queries suspeitas

4. Containment:
   - Revoke credenciais suspeitas
   - Bloquear access patterns detectados
   - Disable affected accounts temporariamente se necessario

## Investigation (2-24h)
1. Determinar:
   - Quantidade exata de registros
   - Quais campos afetados
   - Data de inicio de comprometimento
   - Como invasor ganhou access
   - Se dados ja foram vendidos/publicados

2. Consultar:
   - Cyber insurance provider
   - External forensics firm (se sofisticado)
   - Legal counsel (GDPR compliance)

## Notification Timeline
- GDPR: 72 horas para notificar autoridades regulatorias
- USA (varies by state): 30-60 dias
- Email notice: [vide template abaixo]

## Post-incident
- Breach register entry
- Insurance claim (se necessario)
- Credit monitoring offer (se sensvel)
- Post-mortem em 1 semana
```

### Credential Leak Playbook

```
## Immediate Actions
1. Identificar secreto:
   - API key, password hash, JWT token, SSH key?
   - Escopo de acesso (read-only ou read-write)?
   - Services afetados

2. Monitorar uso:
   - Logs de 24h antes e 24h depois da descoberta
   - Qualquer request malicioso usando a chave?

3. Revoke imediatamente:
   - Invalidar secret em todos os sistemas
   - Gerar novo secret
   - Fazer deploy com novo secret (zero-downtime)

4. Buscar em repositorios publicos:
   - GitHub, GitLab, Bitbucket public repos
   - Pastebin, GitHub Gists
   - Dark web (opcional, via servicos de monitoramento)

## Evidence
- First noticed date/time
- Committed date (se em git)
- Who had access (git log)
- If password, force-reset related accounts
- Check for secondary access (backdoor accounts criados)

## Prevention
- Pre-commit hook (gitleaks)
- Rotate secret mensalmente mesmo sem leak
- Monitor for unauthorized access patterns
```

### DDoS/Availability Playbook

```
## Detection
- Alertas de traffic anormalmente alto
- Error rates elevadas (5xx)
- Timeouts no services
- Infra (CPU/bandwidth) maxed out

## Immediate Response (< 5 min)
1. [ ] Ativar rate limiting agressivo
2. [ ] Ativar CDN DDoS protection (Cloudflare, AWS Shield)
3. [ ] Block known botnet IPs
4. [ ] Failover para backup infrastructure se disponvel

## Analysis
1. Identificar origem:
   - Distributed botnet (tipos de IPs, geografias)
   - Volumetric (UDP flood, DNS amplification)
   - Protocol attack (SYN flood, HTTP slowloris)
   - Application layer (valid requests mas abusivas)

2. Tamanho do attack:
   - Bandwidth em Gbps
   - RPS (requests per second)
   - Geographic distribution

## Mitigation
- Rate limiting por IP
- CAPTCHA para usuarios suspeitos (se application level)
- Geo-blocking se apropriado
- Escalar para CDN provider para upstream filtering

## Communication
- Status page updates (5-10 min intervals)
- Notify customers via email
- Post-mortem no final
```

## Communication Templates

### Internal Communication

```
Subject: SECURITY INCIDENT - [TYPE] [SEVERITY]

Team,

We have identified a security incident affecting [scope].

SEVERITY: [P1/P2/P3/P4]
DISCOVERED: [Date/Time UTC]
AFFECTED SYSTEMS: [List]
STATUS: [Investigating/Contained/Resolved]

TIMELINE:
- [Time]: Incident occurred
- [Time]: Detected
- [Time]: Escalated
- [Time]: Contained

IMPACT:
- Users affected: ~[number] or [%]
- Data types: [PII/passwords/payment/internal docs]
- Services down: [service 1], [service 2]

CURRENT ACTIONS:
1. [Action 1]
2. [Action 2]
3. [Action 3]

NEXT STEPS:
- Team X investigating [component]
- Team Y implementing [fix]
- All: Do not share details externally until clearance

Questions? Ask in #security-incident channel.

[Incident Commander]
```

### External Communication (Breach Notification)

```
Subject: Important Security Notice - Action Required

Dear Valued Customer,

We are writing to inform you of a security incident that may have affected your account.

WHAT HAPPENED:
On [Date], we discovered unauthorized access to our systems. Our investigation determined that
the following information may have been accessed:
- Name
- Email address
- Password hash (bcrypt-encrypted)
- [Additional data]

WHAT WE'RE DOING:
- Immediately revoked unauthorized access
- Enhanced monitoring on affected accounts
- Notified law enforcement
- Engaging external cybersecurity firm

WHAT YOU SHOULD DO:
1. Change your password immediately
2. Enable two-factor authentication
3. Monitor account for unauthorized activity
4. Consider credit monitoring if payment info exposed

COMPENSATION:
We're offering [months] of free [service] and $[amount] for credit monitoring
as a token of our commitment to your security.

SUPPORT:
Email us at security@example.com or call [number]. We're available 24/7.

We deeply regret this incident and are committed to earning back your trust.

[CEO Name]
```

### Regulatory Notification (GDPR)

```
To: [Supervisory Authority]
From: [Data Controller DPO]
Date: [Within 72 hours of discovery]

INCIDENT NOTIFICATION

Supervisory Authority: [GDPR Authority, e.g., CNPD Portugal]

INCIDENT DETAILS:
- Date of discovery: [DD/MM/YYYY]
- Estimated date of incident: [DD/MM/YYYY]
- Number of data subjects affected: [Number]
- Categories of personal data: [List]
- Categories of recipients of data: [List]

RISK ASSESSMENT:
Risk of high severity breach: [Yes/No]
Reason: [Explain likelihood and severity]

MEASURES TAKEN/PLANNED:
- Technical measures: [List]
- Organizational measures: [List]
- Notification to data subjects: [Date planned]

CONTACT POINT:
[DPO name, email, phone]
```

## Evidence Preservation

### Immediate snapshot protocol

```bash
#!/bin/bash
# preserve_evidence.sh

INCIDENT_ID=$1
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
EVIDENCE_DIR="/secure/evidence/$INCIDENT_ID/$TIMESTAMP"

mkdir -p "$EVIDENCE_DIR"
chmod 700 "$EVIDENCE_DIR"

echo "[1] System state"
uname -a > "$EVIDENCE_DIR/system.txt"
date -u >> "$EVIDENCE_DIR/system.txt"
ps aux >> "$EVIDENCE_DIR/system.txt"
netstat -pantul >> "$EVIDENCE_DIR/network.txt"

echo "[2] Memory dump"
sudo bash -c "cat /proc/kcore" > "$EVIDENCE_DIR/memory.dump" 2>/dev/null || \
    echo "Memory dump unavailable" > "$EVIDENCE_DIR/memory.dump"

echo "[3] Disk snapshot (LVM)"
sudo lvcreate -L 100G -s -n evidence /dev/vg0/root || \
    echo "Could not snapshot filesystem"

echo "[4] Recent logs"
sudo tar czf "$EVIDENCE_DIR/logs.tar.gz" /var/log/ 2>/dev/null

echo "[5] Database backup"
sudo mysqldump --all-databases --events > "$EVIDENCE_DIR/databases.sql"

echo "[6] Network traffic (PCAP)"
tcpdump -i any -w "$EVIDENCE_DIR/traffic.pcap" "host $(hostname -I)" \
    -G 60 -W 10 &

echo "[7] Command history"
history > "$EVIDENCE_DIR/bash_history.txt"
sudo cat ~/.bash_history >> "$EVIDENCE_DIR/bash_history.txt"

echo "[8] Chain of custody"
cat > "$EVIDENCE_DIR/CHAIN_OF_CUSTODY" <<EOF
Incident ID: $INCIDENT_ID
Collection time: $TIMESTAMP
Collected by: $(whoami)
Purpose: Security incident investigation
File list:
EOF

find "$EVIDENCE_DIR" -type f -exec sha256sum {} \; >> "$EVIDENCE_DIR/CHAIN_OF_CUSTODY"

echo "Evidence collected to: $EVIDENCE_DIR"
```

### Logs forensicos

```bash
# Extrair logs relevantes
grep "FAILED\|ERROR\|suspicious\|unauthorized" /var/log/auth.log \
    > /secure/evidence/auth_anomalies.log

# Timeline de eventos
sudo journalctl --since "2024-01-15 10:00:00" --until "2024-01-15 14:00:00" \
    > /secure/evidence/timeline.log

# Conexoes de rede suspeitas
sudo tcpdump -r /secure/evidence/traffic.pcap \
    'src net 10.0.0.0/8 and dst net !10.0.0.0/8' \
    > /secure/evidence/exfiltration_attempts.txt
```

## Blameless Post-Mortem Template

```markdown
# Post-Mortem: [Incident Type]

Date: [YYYY-MM-DD]
Duration: [X hours from detection to resolution]
Severity: [P1/P2/P3/P4]
Participants: [Names, roles]

## Executive Summary
[1-2 paragraphs of what happened, impact, resolution]

## Timeline
- **[Time1] UTC**: Incident occurred (e.g., unauthorized access)
- **[Time2] UTC**: Detected by [alert/manual review]
- **[Time3] UTC**: Escalated to [team]
- **[Time4] UTC**: Root cause identified
- **[Time5] UTC**: Mitigation started
- **[Time6] UTC**: Fully resolved

## Contributing Factors (Blameless)
NOT: "Engineer X forgot to enable 2FA"
BUT: "Process gap: 2FA not enforced in our deployment pipeline"

NOT: "Contractor left SSH key in code"
BUT: "Preventative control gap: no pre-commit hook scanning"

Examples of root factors:
- Incomplete runbook for deployment
- Alert threshold was too high (missed early signs)
- No monitoring for specific attack vector
- Configuration drift from standard hardening
- Missing validation in API endpoint
- Lack of rate limiting on endpoint

## Learnings
### What went well
- [Positive aspect 1]
- [Positive aspect 2]

### What could be improved
- [Area 1] - affected response time
- [Area 2] - made detection harder
- [Area 3] - complicated mitigation

## Action Items
| Item | Owner | Due Date | Priority |
|------|-------|----------|----------|
| [1] Implement [control] to prevent | Team X | [Date] | P1 |
| [2] Add [alert] to detect | Team Y | [Date] | P1 |
| [3] Update [runbook] | Team Z | [Date] | P2 |
| [4] Conduct [training] | HR | [Date] | P2 |

## Appendix
- [Link to incident ticket]
- [Link to war room recording]
- [Link to logs analysis]
```

## Recovery Procedures

### Disaster Recovery (RTO/RPO)

```yaml
# disaster_recovery.yaml

services:
  api:
    rto: "15 minutes"  # Recovery Time Objective
    rpo: "5 minutes"   # Recovery Point Objective
    backup_frequency: "every 5 minutes (incremental)"
    restore_procedure:
      1. "Restore database from latest backup"
      2. "Redeploy application from git tag"
      3. "Run health checks"
      4. "Gradual traffic shift to new instance"

  database:
    rto: "30 minutes"
    rpo: "1 minute"
    backup_type: "Continuous replication to standby"
    restore_procedure:
      1. "Promote read replica to primary"
      2. "Update connection strings"
      3. "Verify data consistency"

  cache:
    rto: "5 minutes"
    rpo: "0 minutes (non-critical, cache miss acceptable)"
    restore_procedure:
      1. "New cache cluster can be provisioned from scratch"
      2. "Application will refill cache"
```

Script de failover:

```bash
#!/bin/bash
# failover.sh - Execute durante incident P1

set -e

echo "[1] Promoting read replica..."
aws rds promote-read-replica \
    --db-instance-identifier prod-db-replica

echo "[2] Waiting for promotion..."
sleep 120

echo "[3] Updating connection strings..."
kubectl patch secret database-creds \
    --patch='{"stringData":{"DATABASE_URL":"new-url"}}'

echo "[4] Rolling restart of app pods..."
kubectl rollout restart deployment/app -n production

echo "[5] Health check..."
kubectl rollout status deployment/app -n production
```

## Escalation Matrix

```
Detectado por: Alert -> On-call Engineer (5 min response)

Severidade:
P1:
  - Notificar CEO, CTO, Compliance Officer (imediatamente)
  - Page on-call from 2+ teams
  - War room setup
  - Public status page update (5 min)

P2:
  - Notificar Team Lead + Manager
  - Page on-call engineer
  - Slack notification ao time
  - Status page update (30 min)

P3:
  - Notificar Team Lead
  - Create ticket
  - Update via email (1 day)

P4:
  - Create backlog item
  - Track em planning meeting
```

## Regulatory Timelines

### GDPR (EU)
- **72 hours** from discovery → Notify supervisory authority
- **Without undue delay** → Notify affected individuals IF high risk
- **30 days** → Response to data subject access request
- **Permanent record** of all incidents for 3 years

### LGPD (Brazil)
- **72 hours** from discovery → Notify ANPD if sensitive data
- **Without undue delay** → Notify affected individuals
- **Cooperation** with authorities for investigation

### CCPA (California)
- **Without undue delay** → Notify affected consumers
- **Reasonable security** required (business judgment)
- Right to opt-out of sale of personal information

### HIPAA (Healthcare - USA)
- **60 days** from discovery → Notify affected individuals
- **60 days** → Notify media (if >500 individuals)
- **Breach notification to HHS** if >500 individuals

## Tabletop Exercises

Executar trimestralmente:

```markdown
## Tabletop Exercise: Data Breach Scenario

### Scenario
Friday 3 PM: Customer reports unusual activity. You discover 100k user records
were exfiltrated 2 days ago.

### Teams
- Incident Commander
- Engineering Lead
- Security Engineer
- Legal/Compliance Officer
- PR/Communications
- Customer Success Lead

### Discussion Points
1. Timeline: When would we have detected this?
2. Initial actions: Who does what in first 30 min?
3. Scope determination: How do we figure out what was taken?
4. Evidence: What would we preserve?
5. Communication: What's the first message to customers?
6. Compliance: GDPR vs LGPD vs CCPA - different timelines?
7. Business impact: Can we operate during investigation?
8. Post-mortem: What failed in detection?

### Scoring
- Time to declare incident: Target < 5 min
- Time to escalation: Target < 15 min
- Notification draft: Target < 60 min
- Root cause hypothesis: Target < 2 hours
```
