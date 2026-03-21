# SECURITY — Guia Mestre de Seguranca

> Este documento define a postura de seguranca obrigatoria para qualquer projecto SOTA.
> Complementa as skills existentes (security-auditor, api-security, auth-patterns) com cobertura de infraestrutura, operacoes, DevSecOps, supply chain, monitorizacao e resposta a incidentes.

## Relacao com Skills Existentes

| Skill | Foco | Escopo | Fase |
|-------|------|--------|------|
| **security-auditor** | Auditoria de aplicacao | OWASP Top 10, vulns app-level | 5 |
| **api-security-best-practices** | Hardening de APIs | Autenticacao, rate-limiting, validacao | 3 |
| **auth-implementation-patterns** | Autenticacao e autorizacao | JWT, OAuth 2.0, MFA, sessoes | 3 |
| **SECURITY.md (este documento)** | Postura global de seguranca | Infraestrutura, ops, supply chain, compliance, incidentes | Transversal |

Este documento articula QUANDO e COMO cada skill se ativa. Trata-se de um maestro orquestral de seguranca.

---

## Principio Zero: Defense in Depth

Seguranca nao e conseguida com uma unica camada. Assumimos compromisso absoluto com defesa em profundidade:

```
Codigo (validacao, encoding)
    ↓
Dependencias (lockfiles, audit, SBOM)
    ↓
Segredos (vault, rotacao, .env)
    ↓
Infraestrutura (SSH, firewall, TLS, least privilege)
    ↓
Rede (mTLS, VPN, segmentacao)
    ↓
Monitorizacao (logs estruturados, anomalias, alertas)
    ↓
Resposta (playbooks, comunicacao, post-mortem)
```

Se uma camada falha, as outras impedem o dano.

---

## Camada 1 — Codigo Seguro

**Responsabilidade:** security-auditor e api-security-best-practices

**Minimos obrigatorios:**
- Validacao de inputs: whitelist, nao blacklist. Contrato entre camadas.
- Output encoding: HTML, URL, CSS, JavaScript contextos diferentes.
- Tratamento de erros: nunca expoem stack traces, paths, versoes ou dados sensveis em respostas publicas.
- SQL injection: parametrizacao obrigatoria (prepared statements, ORMs validados).
- CORS: configuracao explcita, nunca wildcards (*) em producao.
- Dependency scanning: `npm audit`, `pip-audit`, `cargo audit` em CI/CD.

**Ativacao:** Pre-desenvolvimento. Auditorias mensais em código ja produzido.

---

## Camada 2 — Dependencias & Supply Chain

**Responsabilidade:** supply-chain-security/SKILL.md (skills futuro); resumo aqui.

**Essencial:**
- **Lockfiles:** package-lock.json, poetry.lock, Cargo.lock OBRIGATORIOS em VCS.
- **Auditoria:** `npm audit --production` antes de cada deploy.
- **SBOM:** gerar Software Bill of Materials (cyclonedx ou spdx) para rastreabilidade.
- **Signed commits:** commits assinados com GPG, verificacao obrigatoria em main branch.
- **Dependency pinning:** nunca usar ranges fuzzy (^, ~) em producao; pinning exato.
- **Quarentena:** packages descontinuados ou com vulns criticas sao sinalizados antes de uso.

**Monitoramento:** Dependabot, Snyk, ou Trivy em CI/CD.

---

## Camada 3 — Segredos & Credenciais

**Responsabilidade:** secrets-management/SKILL.md (skills futuro); resumo aqui.

**Regra de Ouro:** Nunca, sob nenhuma circunstancia, commitar secrets em VCS.

**Implementacao:**
- **.env.example:** template sem valores, para demonstracao.
- **.env (local):** gitignored, carregado em runtime.
- **Vault/Secrets Manager:** HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, ou 1Password Business para producao.
- **Rotacao:** secrets de API/BD rotacionadas a cada 90 dias; credenciais de servico a cada 30 dias.
- **Auditoria:** logs de acesso a secrets, quem acedeu e quando.
- **Revogacao:** processo de revogacao imediata em caso de comprometimento.

**Deteccao:** git-secrets, TruffleHog em pre-commit hook.

---

## Camada 4 — Infraestrutura

**Responsabilidade:** infrastructure-hardening/SKILL.md (skills futuro); resumo aqui.

**Hardening obrigatorio:**
- **SSH:** chaves ED25519, nao passwords; acesso por bastion/jump host em producao.
- **Firewall:** ufw/iptables com regras de least privilege; abertura de portos documentada.
- **Swap seguro:** encryption, permissoes restritivas (chmod 600).
- **Fail2ban:** proteccao contra brute-force em SSH e servicos criticos.
- **TLS/HTTPS:** obrigatorio em QUALQUER comunicacao em rede; certificados Let's Encrypt, rotacao automatica.
- **Reverse proxy:** Nginx/Caddy entre aplicacao e internet; filtro de requests malformados.
- **Permissoes:** aplicacao roda como usuario nao-root; umask 0077.
- **Updates:** patching automatico (unattended-upgrades em Linux).

**Verificacao:** security scanner (Trivy, Grype) em imagens de container.

---

## Camada 5 — Rede & Comunicacao

**Principios:**
- **TLS Everywhere:** HTTP apenas em localhost; HSTS obrigatorio (min-age 31536000).
- **mTLS:** servico-para-servico com certificados bidirecionais, validacao obrigatoria.
- **VPN/WireGuard:** acesso administrativo APENAS atraves VPN, nao acesso direto.
- **Segmentacao:** zero-trust network; firewalls entre zonas (DB isolada de frontend).
- **Rate-limiting:** DDoS mitigation, validacao em edge (Cloudflare, AWS Shield).
- **WAF:** Web Application Firewall para bloqueio de padroes OWASP.

**Monitoramento:** alertas em conexoes suspeitas, tentativas de lateral movement.

---

## Camada 6 — Monitorizacao & Alertas

**Logging obrigatorio:**
- **Estrutura:** JSON logs (ELK, Loki, Datadog) nao text logs.
- **Campos essenciais:** timestamp, nivel (ERROR, WARN, INFO), servico, usuario_id, request_id, acao, resultado.
- **Retencao:** minimo 90 dias em producao, 1 ano para eventos de seguranca.
- **Proteccao:** logs sao imutaveis (append-only); acesso auditado.

**Alertas (SLA de resposta):**
- **CRITICAL:** falhas de autenticacao em massa, acesso nao-autorizado → resposta em 5 minutos.
- **HIGH:** brute-force detectado, modificacao nao-esperada de ficheiros → 15 minutos.
- **MEDIUM:** padroes anomalos em trafego → 1 hora.
- **LOW:** updates disponveis, pequenas anomalias → 24 horas.

**SIEM basico:** correlacao de eventos, deteccao de padroes anormais.

---

## Camada 7 — Resposta a Incidentes

**Responsabilidade:** incident-response/SKILL.md (skills futuro); resumo aqui.

**Playbooks obrigatorios:**
1. **Data Breach:** isolamento de sistema, notificacao de stakeholders, analise forense.
2. **DDoS:** ativacao de mitigation, escalada para CDN/ISP.
3. **Compromise de credenciais:** revogacao imediata, password reset, 2FA refresh.
4. **Malware:** isolamento, scan completo, verificacao de backups.

**Processo:**
- **Deteccao:** alertas acionam runbook automatico.
- **Comunicacao:** escalada em cadeia; stakeholders informados em tempo real.
- **Mitigacao:** pasos definidos, nao improvisacao.
- **Postmortem:** dentro de 48h; raiz, timeline, accoes preventivas.

---

## Matriz de Responsabilidade (RACI)

| Atividade | security-auditor | api-security | auth-patterns | SECURITY.md | Skill Futuro |
|-----------|-----------------|--------------|---------------|-------------|---|
| Auditoria OWASP | **R/A** | C | I | I | - |
| Design de API segura | C | **R/A** | C | I | - |
| Implementacao JWT/OAuth | C | I | **R/A** | I | - |
| Hardening de infraestrutura | I | I | I | **C** | **R/A** |
| Gestao de secrets | I | I | I | **C** | **R/A** |
| Supply chain | I | I | I | **C** | **R/A** |
| Monitorizacao global | I | I | I | **R/A** | C |
| Resposta a incidentes | I | I | I | **C** | **R/A** |

**Legenda:** R=Responsible, A=Accountable, C=Consulted, I=Informed

---

## Checklist Security-by-Default

**Obrigatorio ANTES de qualquer deploy em producao:**

- [ ] Todas as inputs validadas com whitelist
- [ ] Outputs encoded segundo contexto (HTML/URL/JS)
- [ ] Nao ha secrets em VCS; .gitignore valido
- [ ] Lockfiles presentes e auditados (zero vulns CRITICAL)
- [ ] SSH keys ED25519, nao passwords
- [ ] HTTPS/TLS obrigatorio; HSTS configurado
- [ ] Firewall configurado; ports minimos abertos
- [ ] Aplicacao roda como user nao-root
- [ ] Logging estruturado (JSON) com campos obrigatorios
- [ ] Alertas configurados (CRITICAL, HIGH)
- [ ] Backup testado; plano de restauro documentado
- [ ] Secrets Manager em uso (vault, Secrets Manager, etc.)
- [ ] 2FA habilitado para acesso administrativo
- [ ] WAF ou rate-limiting ativo
- [ ] Postmortem de seguranca realizado no ultimo mes (zero findings pendentes)

**Falha neste checklist = bloqueio de deploy.**

---

## Classificacao de Severidade

| Nivel | Impacto | SLA de Resposta | Exemplos |
|-------|---------|-----------------|----------|
| **CRITICAL** | Roubo de dados, downtime completo | 5 minutos | Breach confirmado, RCE em uso, falha de autenticacao |
| **HIGH** | Compromisso de contas, funcionalidade afetada | 15 minutos | Brute-force ativo, privesc, unauthorized access |
| **MEDIUM** | Risco potencial, usuario afetado | 1 hora | Padroes anomalos, tentativas explorados, weak crypto |
| **LOW** | Observacao, qualidade | 24 horas | Updates disponiveis, config suboptima, lint warnings |

---

## Workflows de Seguranca (Skills Futuros)

Estes workflows serao invocados como comandos em ambiente SOTA:

```
/security-audit          → Ativa security-auditor + api-security
                           Output: OWASP Top 10 audit report, recomendacoes

/hardening              → Ativa infrastructure-hardening + secrets-management
                           Output: playbook de hardening, checklist pré-deploy

/incident TIPO          → Ativa incident-response + monitorizacao
                           Output: runbook especifico, playbook, comunicacao template

/supply-chain-scan      → Ativa supply-chain-security
                           Output: SBOM, dependency graph, vulns por severidade

/secrets-rotate         → Ativa secrets-management
                           Output: script de rotacao, verificacao pós-rotacao

/monitor-anomalies      → Ativa monitorizacao 24/7
                           Output: alertas, correlacoes, SLA met report
```

---

## Governance & Compliance

**Revisao:** Este documento e revisto trimestralmente. Mudancas regulatorias (GDPR, NIS2, SOC 2) sao integradas imediatamente.

**Auditoria:** Todas as camadas auditadas anualmente por terceiro independente.

**Evidencia:** Cada security decision deixa trail auditavel (logs, commits assinados, postmortems).

---

## Referencia Cruzada

- **ARCHITECTURE.md:** como security integra-se na arquitetura SOTA
- **claude.md:** como Claude agents aplicam security patterns
- **skills/** folder: implementacoes concretas de cada camada

**Ultima atualizacao:** 2026-03-20
