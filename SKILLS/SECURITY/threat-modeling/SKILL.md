---
name: Threat Modeling
description: STRIDE methodology, data flow diagrams, trust boundaries, attack surface analysis, and risk assessment
phase: 2
always_active: false
---

# Threat Modeling

## STRIDE Methodology

Framework para identificar seis categorias de ameacas:

### Spoofing (Falsificacao de Identidade)

Atacante pretende ser alguem que nao eh.

**Exemplo:**
- Falsificar JWT token
- Enganar verificacao de email
- Usar identidade falsa em API

**Controles:**
- Autenticacao forte (MFA, biometria)
- Validacao de origem (TLS, assinatura digital)
- Rate limiting em tentativas de login

**Questoes:**
- Como o usuario eh identificado?
- Pode a identidade ser falsificada?
- Como validar identidade de servico-a-servico?

### Tampering (Adulteracao de Dados)

Atacante modifica dados durante transmissao ou armazenamento.

**Exemplo:**
- Modificar requisicao HTTP (man-in-the-middle)
- Alterar dados no database
- Modificar arquivo de configuracao

**Controles:**
- Encriptacao (TLS 1.3 em transit)
- Integridade (HMAC, assinatura digital)
- Controle de acesso (quem pode modificar)

**Questoes:**
- Dados sao transmitidos em plaintext?
- Ha validacao de integridade?
- Quem pode modificar dados criticos?

### Repudiation (Repudio)

Atacante nega ter realizado uma acao.

**Exemplo:**
- Usuario nega ter feito transferencia bancaria
- Admin nega ter deletado dados
- Ninguem sabe quem fez mudanca no sistema

**Controles:**
- Auditoria completa (quem, quando, o que, resultado)
- Assinatura digital (prova criptografica)
- Logs imutaveis (WORM - Write Once Read Many)

**Questoes:**
- Todas as acoes sao registradas?
- Ha prova de autoria (assinatura)?
- Logs podem ser alterados/deletados?

### Information Disclosure (Divulgacao de Informacao)

Dados sensiveis sao expostos a usuario nao autorizado.

**Exemplo:**
- Erro expoe caminho de arquivo ou versao de software
- Logs contem senhas em plaintext
- API retorna dados de outro usuario
- Dados em cache nao eh criptografado

**Controles:**
- Encriptacao at-rest para dados sensiveis
- Sanitizar mensagens de erro
- Masking/redaction em logs
- Validacao de autorziacao (authorization checks)

**Questoes:**
- Dados sensiveis sao encriptados?
- Mensagens de erro revealam informacao estrutural?
- Usuarios podem acessar dados de outros?

### Denial of Service (Negacao de Servico)

Atacante torna servico indisponivel para usuarios legitimos.

**Exemplo:**
- Enviar muitos requests (DDoS)
- Consumir toda memoria de servidor
- Algoritmo de busca ineficiente (ReDoS)
- Zerar database

**Controles:**
- Rate limiting
- Auto-scaling (handle picos de traffic)
- Input validation (prevenir algoritmos O(n^2))
- Backups e disaster recovery
- WAF (Web Application Firewall)

**Questoes:**
- Servico pode ser sobrecarregado com requests?
- Usuarios podem consumir recursos indefinidamente?
- Ha fallback se recurso principal cair?

### Elevation of Privilege (Escalacao de Privilegio)

Usuario de baixo privilegio ganha acesso de alto privilegio.

**Exemplo:**
- Usuario regular se torna admin
- Bug permite bypass de autorizacao
- Credencial de servico esta muito permissiva

**Controles:**
- Validacao rigorosa de autorizacao (authorization checks em toda mudanca)
- Separacao de responsabilidades (principle of least privilege)
- Input validation (prevenir injection)
- Auditoria de permissoes

**Questoes:**
- Existe validacao de autorizacao antes de operacoes sensiveis?
- Qual eh o escopo de cada credencial/token?
- Usuarios podem modificar parametros pra escalate privilege?

## Threat Modeling como parte da Design Phase

### Quando fazer threat modeling

Obrigatorio no inicio de:
- Nova feature principal
- Mudanca de arquitetura
- Integracao com sistema terceiro
- Mudanca significativa em dados sensveis

Exemplo trigger: "Quer adicionar integracao com Stripe para pagamentos"

## Data Flow Diagrams (DFD)

Desenhar fluxo de dados mostra pontos de ameaca.

### DFD simples: Autenticacao

```
[User Browser]
     |
     | username/password (HTTPS)
     v
[Web Server]
     |
     | SQL query
     v
[User Database]

Elementos:
- Entities: [brackets] - usuarios, sistemas externos
- Processes: (parenteses) - o que acontece
- Data Stores: [=====] - databases, caches
- Data Flows: arrows com labels
```

### DFD completo: E-commerce

```
[User]
  |
  | HTTP request (HTTPS)
  v
[Web Server] (1)
  |        |
  | SQL    | JSON
  v        v
[Product DB]  [Cache]
             |
             | (2) Charge card
             v
         [Stripe API]

[Admin] <-- (3) Admin interface
```

Trust boundaries sao criticas:

```
User's Computer | Browser Boundary | Web Server | Database

[User] --------[HTTPS]----- [Web Server] ---- [DB]
 ^                                 ^
 |-- 1. Spoofing risk              |-- Injection attacks
     (fake user)                       (SQL injection)
                                      Privilege escalation
```

## Trust Boundaries

Definir limites entre componentes confiados e nao confiados.

```
TRUSTED ZONE          |     UNTRUSTED ZONE
- Our code            |     - User input
- Our database        |     - External APIs
- Internal network    |     - Third-party libraries
- Cryptographic keys  |     - Network packets
                      |     - Cookies/localStorage
         BOUNDARY -----
         (Apply security controls)
```

Exemplo de analise com trust boundaries:

```
[User Mobile App] <-- UNTRUSTED (pode ser modificada)
        |
        | [HTTPS] - VALIDATED
        v
[API Gateway] <-- TRUSTED (nossa infraestrutura)
        |
        | [JSON-RPC internal]
        v
[Backend Services]
        |
        | [SQL parameterized]
        v
[Database]

Actions at boundaries:
- Validate all input from User App
- Sanitize before passing to Database
- Encrypt sensitive data crossing network
- Authenticate and authorize on each boundary
```

## Attack Surface Analysis

### Identificar todos os pontos de ataque

Para e-commerce com mobile app:

**Entry Points:**
1. API endpoints (mobile app → backend)
2. Web dashboard (admin → backend)
3. Webhook (Stripe → backend)
4. Email links (user email)
5. DNS records
6. AWS console access

**Data Sources:**
- User input (forms, API bodies)
- Files uploaded
- Configuration files
- Cookies
- Headers
- Query parameters

**Processamento:**
- Autenticacao (username/password, JWT)
- Validacao (format, length, range)
- Autorizacao (acesso a dados de usuario X)
- Business logic (discount calculations)
- Integration (chamadas a Stripe, email service)

**Armazenamento:**
- User passwords (bcrypt + salt)
- Card tokens (Stripe, nao armazenar full card)
- Session tokens
- Audit logs

**Saida:**
- Error messages (podem revelar estrutura?)
- API responses (dados privados?)
- Logs (contem senhas?)

### Ranking de risco

```
Risco = Likelihood × Impact

HIGH RISK (Likelihood=HIGH, Impact=HIGH):
- SQL Injection em query do usuario
- Unauthorized access a outro usuario's account

MEDIUM RISK:
- Weak password policy
- Informacao disclosure em error messages

LOW RISK:
- Outdated library version (nao explorado)
- Minor data validation issue
```

## Risk Assessment Matrix

Matriz de Probabilidade × Impacto:

```
              LOW                MEDIUM              HIGH
           Impact = 1-3        Impact = 4-6        Impact = 7-10

HIGH      [MEDIUM]           [HIGH]              [CRITICAL]
Prob=0.7-1.0


MEDIUM    [LOW]              [MEDIUM]            [HIGH]
Prob=0.4-0.7


LOW       [LOW]              [LOW]               [MEDIUM]
Prob=0.1-0.4

Exemplo:
SQL Injection:
  - Likelihood: 0.8 (comum, many endpoints)
  - Impact: 9 (all database exposed)
  - Risk = 0.8 × 9 = 7.2 = HIGH/CRITICAL
  - Mitigation: Parameterized queries, input validation

Weak password:
  - Likelihood: 0.6 (some users will choose weak)
  - Impact: 7 (account compromise)
  - Risk = 0.6 × 7 = 4.2 = MEDIUM
  - Mitigation: Password policy, MFA
```

## Threat Model Template

```markdown
# Threat Model: [Feature Name]

## Overview
[1-2 paragraphs describing the feature and scope]

## Architecture
[DFD or architecture diagram]

## Trust Boundaries
```
[User] ---|HTTPS|--- [API] ---|Encrypted| --- [Database]
                Trust boundary here ^
```

## STRIDE Analysis

### Spoofing
- **Threat:** Attacker impersonates user via JWT token forgery
  - Likelihood: MEDIUM (requires secret key)
  - Impact: HIGH (access other user's data)
  - Risk: MEDIUM-HIGH
  - Mitigation: Strong JWT secret, short expiration, refresh token rotation

### Tampering
- **Threat:** Man-in-the-middle modifies order amount
  - Likelihood: LOW (HTTPS prevents, but BREACH possible)
  - Impact: CRITICAL (wrong charges)
  - Risk: MEDIUM
  - Mitigation: TLS 1.3, HSTS headers, HMAC on sensitive fields

### Repudiation
- **Threat:** User denies making purchase
  - Likelihood: MEDIUM (customers do this)
  - Impact: MEDIUM (financial loss, customer dispute)
  - Risk: MEDIUM
  - Mitigation: Signed order confirmation, audit log, email receipt

### Information Disclosure
- **Threat:** API error reveals database structure
  - Likelihood: HIGH (common coding error)
  - Impact: LOW (helps reconnaissance)
  - Risk: MEDIUM
  - Mitigation: Generic error messages, sanitize logs

### Denial of Service
- **Threat:** Attacker floods checkout endpoint with requests
  - Likelihood: MEDIUM (easy to automate)
  - Impact: HIGH (customers can't purchase)
  - Risk: HIGH
  - Mitigation: Rate limiting, DDoS protection, auto-scaling

### Elevation of Privilege
- **Threat:** Regular user modifies 'user_id' parameter to access other account
  - Likelihood: HIGH (common vulnerability)
  - Impact: CRITICAL (complete account takeover)
  - Risk: CRITICAL
  - Mitigation: Server-side authorization checks, never trust client-side IDs

## Action Items
| Threat | Risk | Mitigation | Owner | Due |
|--------|------|-----------|-------|-----|
| SQL Injection | CRITICAL | Use parameterized queries | Backend team | Sprint N |
| Elevation | CRITICAL | Add authz checks | Backend team | Sprint N |
| DDoS | HIGH | Rate limiting + WAF | Platform | Sprint N+1 |
| Info Disclosure | MEDIUM | Generic errors | Backend | Sprint N+1 |

## Approval
Reviewed by: [Security lead]
Approved: [Date]
```

## MITRE ATT&CK Overview

Banco de dados global de tecnicas de ataque usadas por adversarios reais.

### Frameworks principais:

1. **Initial Access:** Como atacante entra (phishing, supply chain)
2. **Execution:** Rodar codigo (malware, script)
3. **Persistence:** Manter acesso (backdoor, scheduled task)
4. **Privilege Escalation:** Ganhar mais acesso
5. **Defense Evasion:** Esconder trilhas (disable logging, anti-virus bypass)
6. **Credential Access:** Roubar credenciais (brute force, phishing)
7. **Discovery:** Mapear o alvo (port scan, system enumeration)
8. **Lateral Movement:** Spreads across network
9. **Collection:** Coletar dados
10. **Command & Control:** Comunicacao com atacante
11. **Exfiltration:** Roubar dados
12. **Impact:** Deletar/criptografar dados

### Exemplo: Phishing para ransomware

```
Threat: Ransomware via phishing email

MITRE Mapping:
1. Initial Access [T1566.002]: Phishing with attachment
   - Mitigação: Email filtering, user training

2. Execution [T1204]: User enables macros
   - Mitigação: Disable macros, EDR monitoring

3. Persistence [T1547]: Scheduled task for re-infection
   - Mitigação: Endpoint protection, process monitoring

4. Defense Evasion [T1562.008]: Disable event logging
   - Mitigação: Centralized logging (SIEM), immutable logs

5. Lateral Movement [T1021]: RDP to other systems
   - Mitigação: Network segmentation, MFA on RDP

6. Impact [T1491.001]: Encrypt files and demand ransom
   - Mitigação: Regular backups (offline), disaster recovery
```

## Common Threat Patterns para Web Apps

### Pattern 1: Authentication Bypass

```
Threat: Attacker bypasses login

Common causes:
- No rate limiting on login attempts
- Predictable session tokens
- JWT secret hardcoded in frontend
- SQL injection in login query
- Logic flaw (if error == "user not found", means account exists)

Detection:
- Multiple failed logins from same IP
- Successful login from unusual location
- Session cookie tampering

Mitigation:
- Strong password hashing (bcrypt, argon2)
- MFA (TOTP, FIDO2)
- Rate limiting + account lockout
- Secure random token generation
- Parameterized SQL queries
```

### Pattern 2: Privilege Escalation via Parameter Tampering

```
Web form:
<input type="hidden" name="user_id" value="123">

Attacker changes to:
<input type="hidden" name="user_id" value="456">

Server processes without validation → Attacker sees user 456's data

Mitigation:
- Never trust client-provided IDs
- Always validate: logged_in_user.id == request.user_id
- Use server-side sessions, not just client cookies
- Implement proper authorization checks on EVERY action
```

### Pattern 3: Insecure Direct Object Reference (IDOR)

```
API: GET /api/invoices/12345

Attacker tries:
GET /api/invoices/12346
GET /api/invoices/12347
...

If no authorization checks:
- All invoices from all customers exposed

Mitigation:
- Check: invoice.user_id == current_user.id
- Use non-sequential IDs (UUID)
- Rate limit API lookups
```

### Pattern 4: Injection Attacks

```
SQL Injection:
username = "admin' --"
Query becomes: SELECT * FROM users WHERE name = 'admin' --'
Result: Returns all users

Command Injection:
file = "test.pdf; rm -rf /"
Command becomes: cp test.pdf; rm -rf / (disaster!)

Template Injection:
Input: "{{7*7}}"
Output: "49" (template engine executed math!)

Mitigation:
- Use parameterized queries / ORM
- Avoid shell commands (use library functions)
- Disable template expression evaluation in user input
- Input validation + whitelist allowed characters
```

### Pattern 5: Cross-Site Scripting (XSS)

```
Stored XSS:
User comments: "<script>stealCookie()</script>"
Other users see comment → Script runs in their browser

Reflected XSS:
URL: https://site.com/?search=<script>steal()</script>
If server echoes search param without escaping → Malicious

Mitigation:
- Escape HTML in output (< becomes &lt;)
- Use templating engines that auto-escape
- Content Security Policy (CSP) headers
- HTTPOnly flag on cookies
```

## When to Re-Model (Recurring Threat Modeling)

Threat model pode se desatualizar. Re-fazer quando:

```
IMMEDIATELY (within sprint):
- Critical security issue found in code
- Major breach or incident
- New zero-day affecting your stack

WHEN SHIPPING NEW FEATURE:
- New API endpoint
- New data type collected
- Integration with external service
- Change in auth method

QUARTERLY:
- Full threat model review
- STRIDE analysis on major components
- Risk assessment update
- New threats in industry

ANNUALLY:
- Complete re-threat-modeling
- Update architecture diagram
- Verify all mitigations still deployed
- Training on findings
```

Exemplo de checklist para new feature:

```
Feature: "Add two-factor authentication"

Threat model checklist:
[ ] Updated DFD (TOTP generation flow added)
[ ] Trust boundary analysis (OTP code validation where?)
[ ] STRIDE analysis:
    [ ] Spoofing: Can attacker fake OTP?
    [ ] Tampering: Can SMS be intercepted?
    [ ] Repudiation: Can user deny enabling 2FA?
    [ ] Info Disclosure: OTP backup codes stored securely?
    [ ] DoS: Can attacker lock user out?
    [ ] Privilege Escalation: N/A (no privilege change)
[ ] Attack surface: New endpoint for 2FA setup
[ ] Risk assessment: Any HIGH/CRITICAL risks?
[ ] Mitigations: Implemented?
[ ] Approved by security team
```

## Automacao de Threat Modeling

### Ferramentas

```bash
# Markdown-based threat modeling
pip install pytm

# gera DFD + STRIDE analysis da descricao

# Microsoft Threat Modeling Tool (free)
# - GUI para desenhar DFDs
# - Auto-generate STRIDE threats

# IriusRisk (commercial)
# - Library de threat patterns
# - Rastreamento de mitigacao

# ThreatDragon (open source)
# - Web-based DFD drawing
# - STRIDE analysis
```

### Integracao em CI/CD

```yaml
# Gerar threat report a cada deploy

name: Threat Modeling Report

on: [pull_request]

jobs:
  threat-model:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Check for new features
        run: |
          # Se novo arquivo em features/, re-threat-model
          git diff origin/main --name-only | grep features/

      - name: Run threat modeling
        if: env.NEW_FEATURE == 'true'
        run: |
          pip install pytm
          pytm --file threat-model.yaml --output report.html

      - name: Comment on PR
        run: |
          gh pr comment -b "Threat model review required for new feature"
```

## Knowledge Sharing

Manter threat models atualizados e acessiveis:

```
/threat-models/
├─ authentication.md (STRIDE analysis)
├─ payment-processing.md (high-risk)
├─ api-architecture.md (DFD + analysis)
├─ infrastructure.md (cloud security)
└─ external-integrations.md (third-party risks)

Process:
1. New feature design → Threat model
2. Review with security team
3. Document in /threat-models/
4. Link from feature spec
5. Update during implementation
6. Periodic reviews (quarterly)
```
