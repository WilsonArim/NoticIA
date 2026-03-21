---
name: Compliance & Privacy
description: GDPR, data classification, PII handling, cookie consent, privacy by design, and regulatory compliance
phase: 2
always_active: false
---

# Compliance & Privacy

## GDPR Essentials

### Sete Principios do GDPR

1. **Lawfulness, Fairness, Transparency**
   - Dados processados apenas com base legal (consentimento, contrato, obrigacao legal, etc)
   - Justo para o individuo (nao surpreendente)
   - Transparencia na coleta ("privacy notice" clara)

2. **Purpose Limitation**
   - Dados coletados apenas para proposito declarado
   - Nao pode reusar para proposito diferente sem novo consentimento

3. **Data Minimization**
   - Coletar apenas dados necessarios
   - Se nao precisa de CPF, nao coleta

4. **Accuracy**
   - Manter dados acurados
   - Permitir que usuario corrija dados incorretos

5. **Storage Limitation**
   - Guardar dados apenas pelo tempo necessario
   - Nao indefinidamente "just in case"
   - Politica de retencao documentada

6. **Confidentiality & Integrity (Security)**
   - Proteger dados contra acesso nao autorizado
   - Criptografia, controle de acesso, etc

7. **Accountability**
   - Demonstrar compliance
   - Manter registros de consentimento
   - Data Protection Impact Assessment (DPIA) para processamento novo

### Consentimento Valido

Consentimento deve ser:
- **Granular**: Consentir para marketing é diferente de consentir para analytics
- **Ativo**: Sem pre-checked boxes (opt-in, nao opt-out)
- **Documentado**: Guardar prova de consentimento com timestamp
- **Revogavel**: Usuario pode retirar consentimento facilmente

Exemplo de implementacao:

```javascript
// consentimento.js
function recordConsent(userId, consentType, value) {
    const record = {
        user_id: userId,
        consent_type: consentType,  // 'marketing', 'analytics', 'personalization'
        given: value,               // true or false
        timestamp: new Date().toISOString(),
        ip_address: getClientIP(),  // para prova
        user_agent: navigator.userAgent
    };

    // Guardar em database com protecao
    saveConsentRecord(record);

    // Garantir que dados so sao processados se consentimento = true
    if (consentType === 'marketing' && !value) {
        disableMarketingPixels();
    }
}

// Ao revogar consentimento
function revokeConsent(userId, consentType) {
    // 1. Parar novo processamento
    // 2. Nao precisa deletar dados historicos (processamento era legal na epoca)
    // 3. Mas parar enviando marketing email
}
```

### Right to Erasure (Direito ao Esquecimento)

Quando usuario solicita delecao:

```sql
-- Delete PII do usuario
DELETE FROM users WHERE id = $1;
DELETE FROM user_events WHERE user_id = $1;
DELETE FROM marketing_lists WHERE user_id = $1;

-- Anonimizar dados historicos necessarios por compliance
UPDATE transactions
SET user_id = NULL,
    user_name = 'ANONYMIZED',
    user_email = 'ANONYMIZED'
WHERE user_id = $1;

-- Guardar auditoria que delecao foi realizada
INSERT INTO audit_log (action, target, timestamp)
VALUES ('user_deletion_request', $1, NOW());
```

Excecoes (nao precisa deletar):
- Dados necessarios para cumprir obrigacao legal (contabil)
- Dados necessarios para defesa judicial
- Dados anonimizados (nao pode ser rastreado ate individuo)

### Data Protection Officer (DPO)

Obrigatorio se:
- Processamento em larga escala de dados sensveis
- Processamento sistematico de dados pessoais
- Autoridade publica (governo)

Responsabilidades do DPO:
- Monitorar compliance
- Recepcionar data subject requests
- Coordenar DPIA para novo processamento
- Liaison com reguladores

## Data Classification

Estabelecer niveis de protecao:

```
RESTRICTED (Critico)
├─ User passwords, API keys
├─ Financial account numbers
├─ SSN/CPF/Passport numbers
├─ Medical records
├─ Biometric data
├─ Authentication codes
└─ Encryption keys

CONFIDENTIAL (Alto)
├─ Customer email addresses
├─ User IP addresses
├─ Transaction history
├─ Browsing behavior
├─ Location data
└─ Usage analytics per user

INTERNAL (Medio)
├─ Product roadmap
├─ Financial projections
├─ Employee info
├─ Internal documentation
└─ Aggregate usage statistics

PUBLIC (Baixo)
├─ Marketing materials
├─ Public documentation
├─ General statistics
└─ Published articles
```

Aplicar politicas por classificacao:

```yaml
# data_classification.yaml

RESTRICTED:
  encryption: "AES-256 at rest, TLS 1.3 in transit"
  access_control: "Need-to-know basis, signed approval"
  retention: "Minimum necessary (usually days/weeks)"
  logging: "All access logged and monitored"
  deletion: "Secure wipe (7-pass overwrite or cryptographic erase)"
  backups: "Encrypted, tested recovery"

CONFIDENTIAL:
  encryption: "AES-256 at rest, TLS in transit"
  access_control: "Role-based, audit trail"
  retention: "As per privacy policy (usually months)"
  logging: "Sampled access logging"
  deletion: "Standard delete + eventual overwrite"

INTERNAL:
  encryption: "At rest if on shared systems"
  access_control: "Employee/contractor only"
  retention: "Project-based (years for compliance)"
  logging: "No individual logging required"
  deletion: "Standard delete"

PUBLIC:
  encryption: "Not required"
  access_control: "Open access"
  retention: "Indefinite"
  logging: "No logging required"
```

## PII Handling

### Criptografia de dados em repouso

```python
# pii_encryption.py
from cryptography.fernet import Fernet
import os

class PIIEncryptor:
    def __init__(self):
        # Guardar chave em vault ou Key Management Service
        self.key = os.environ['PII_ENCRYPTION_KEY'].encode()
        self.cipher = Fernet(self.key)

    def encrypt_email(self, email):
        """Criptografar antes de salvar no database"""
        return self.cipher.encrypt(email.encode()).decode()

    def decrypt_email(self, encrypted):
        """Desencriptar apenas quando necessario"""
        return self.cipher.decrypt(encrypted.encode()).decode()

# Database schema
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(255))  # Criptografado
    phone = Column(String(255))  # Criptografado

    # Indice searchable (hash)
    email_hash = Column(String(255), unique=True, index=True)
```

### Masking em logs

Nunca logar PII em plaintext:

```javascript
// logger.js
function sanitizeForLogging(data) {
    const sanitized = JSON.parse(JSON.stringify(data));

    // Mascarar patterns conhecidos
    if (sanitized.email) {
        sanitized.email = sanitized.email.replace(
            /([^@]{2})[^@]*(@.+)/,
            '$1***$2'  // user@***@example.com
        );
    }

    if (sanitized.phone) {
        sanitized.phone = sanitized.phone.replace(
            /(\d{2})\d{4}(\d{4})/,
            '$1****$2'  // 11****1234
        );
    }

    if (sanitized.cpf) {
        sanitized.cpf = '***.***.***-**';
    }

    if (sanitized.password) {
        delete sanitized.password;  // Nunca logar
    }

    return sanitized;
}

// Uso
logger.info('User login attempt', sanitizeForLogging({
    email: 'user@example.com',
    password: 'secret',  // Sera deletado
    timestamp: new Date()
}));
```

### Data Retention Policies

Estabelecer prazos claros:

```
User Account Data:
  - While active: Keep
  - On account deletion: Secure delete immediately
  - Anonymized logs: Keep 12 months for analytics

Customer Communications:
  - Email (support): Keep 3 years for dispute resolution
  - Chat (support): Keep 1 year
  - Complaint records: Keep 5 years

Marketing Data:
  - Email list: Keep while active + 30 days post-unsubscribe
  - Browsing cookies: 12 months
  - Marketing consent: Keep indefinitely for compliance proof

Financial Data:
  - Transaction records: Keep 7 years (tax/legal)
  - Invoice: Keep 7 years
  - Payment method: Delete after transaction + 2 months

System Logs:
  - Access logs: Keep 90 days
  - Error logs: Keep 30 days
  - Security logs: Keep 12 months
  - Audit logs: Keep 5+ years
```

Script de retencao automatica:

```sql
-- Delete expired data automatically
DELETE FROM marketing_emails
WHERE created_at < NOW() - INTERVAL '30 days'
  AND unsubscribed = true;

DELETE FROM session_logs
WHERE created_at < NOW() - INTERVAL '90 days';

-- Anonimizar dados vencidos
UPDATE user_analytics
SET user_id = NULL, user_email = 'REDACTED'
WHERE created_at < NOW() - INTERVAL '12 months';

-- Garantir consistencia
SELECT COUNT(*) FROM users WHERE id IN (
    SELECT user_id FROM deleted_users
);
```

## Cookie Consent

### Consentimento valido para cookies

```html
<!-- cookie_banner.html -->
<div id="cookie-banner" class="cookie-banner">
  <p>We use cookies for analytics and marketing.
     <a href="/privacy">Learn more</a></p>

  <!-- Granular choices (nao pre-checked) -->
  <label>
    <input type="checkbox" name="essential" disabled checked>
    Essential Cookies (required)
  </label>

  <label>
    <input type="checkbox" name="analytics">
    Analytics Cookies (to improve experience)
  </label>

  <label>
    <input type="checkbox" name="marketing">
    Marketing Cookies (personalized ads)
  </label>

  <button onclick="acceptAll()">Accept All</button>
  <button onclick="acceptSelected()">Accept Selected</button>
  <button onclick="rejectNonEssential()">Reject Non-Essential</button>
</div>

<script>
function acceptSelected() {
    const consent = {
        essential: true,
        analytics: document.querySelector('[name="analytics"]').checked,
        marketing: document.querySelector('[name="marketing"]').checked,
        timestamp: new Date().toISOString()
    };

    // Enviar para server para guardar
    fetch('/api/consent', {
        method: 'POST',
        body: JSON.stringify(consent)
    });

    // Carregar cookies apenas se consentimento foi dado
    if (consent.analytics) {
        loadGoogleAnalytics();
    }
    if (consent.marketing) {
        loadFacebookPixel();
    }
}
</script>
```

## Privacy by Design

Aplicar desde o inicio do projeto:

```
Etapa 1: Conceito
- Qual eh o proposito do processamento?
- Qual base legal? (consentimento, contrato, obrigacao legal)
- Que dados sao realmente necessarios?
- Por quanto tempo guardar?

Etapa 2: Design
- Minimizar dados (pseudonymization/anonymization)
- Encriptar desde o inicio
- Default para opcoes mais privadas
- Planejar direitos de usuario (acesso, correcao, delecao)

Etapa 3: Implementacao
- Encriptar tudo em transit e rest
- Audit logging de acessos
- Validacao de consentimento
- Testar controles

Etapa 4: Manutencao
- Revisar dados armazenados periodicamente
- Deletar dados expirados
- Testar direitos de usuario (DSAR)
- Manter compliance
```

Exemplo: Feature nova de personalizacao

```
Problema: Quer recomendar produtos baseado em historico de usuario

Privacidade by Design:
1. Dados: Precisa apenas de product_id + timestamp, nao nome de usuario
2. Retencao: Guardar apenas 12 meses (nao indefinidamente)
3. Consentimento: Novo consentimento granular para recomendacoes
4. Anonimizacao: Apos 12 meses, converter para dados anonimos para ML training
5. Direitos: Usuario pode visualizar e deletar historico

Implementacao:
- Criptografar user_id em analytics table (ja eh de RESTRICTED classification)
- Criar separada anonymized_events table para dados vencidos
- API endpoint /my-data/recommendations para usuario ver
- API endpoint DELETE /my-data para revogar historico
```

## Data Processing Agreements (DPA)

Quando usar servicos terceiros (AWS, Stripe, etc):

```
Acordo obrigatorio especificar:

1. Finalidade: O que dados serao usados
2. Duracao: Por quanto tempo
3. Natureza: Quais tipos de dados
4. Escopo: Quantos usuarios/registros
5. Processador: Quem pode acessar
6. Sub-processadores: Outras empresas que tenham acesso

Exemplo: Using Stripe for payments

Data Subject: Customer
Data Controller: Your company (decides para que dados usados)
Data Processor: Stripe (processa em nome seu)

DPA Components:
- Stripe processes payment data (PAN, expiry) - nao pode usar para outro proposito
- Stripe guardar dados por 3+ anos para compliance
- Stripe usa sub-processadores [AWS, etc] - deve estar documentado
- Data security: Stripe faz encriptografia, controle de acesso
- Your responsibility: Nao exceder escopo consentido
```

Template minimo de DPA:

```
DATA PROCESSING AGREEMENT

Between: [Your Company] (Controller)
And: [Vendor] (Processor)

Personal Data:
- Categories: [emails, payment info, etc]
- Scope: [All customers, beta users only, etc]
- Duration: [Project duration, contract term, etc]

Processing Instructions:
- Vendor SHALL: Only process as directed
- Vendor SHALL: Implement technical and organizational measures
- Vendor SHALL: Assist with DSAR, deletion requests
- Vendor SHALL: Sub-processor list: [attached]

Security:
- Vendor responsible for: [Encryption, access control, etc]
- Vendor shall notify of breach within 48 hours
- Vendor shall assist with incident response

Sub-processing:
- No new sub-processor without written approval
- Controller may object to new sub-processor

Signature: [Date]
```

## International Data Transfers

Se transferir dados entre paises:

### EU -> US (after Schrems II)
- Standard Contractual Clauses (SCC) com US vendor
- Plus: Supplementary measures (encriptografia, etc) se dados em cloud publica

### EU -> Non-adequacy country
- Standard Contractual Clauses (SCC)
- Or Binding Corporate Rules (BCR) se multi-empresa
- Additional safeguards na contrato

Exemplo: AWS Data Processing Addendum (DPA)
```
AWS oferece modelo de SCC
Your Company deve assinar no AWS Contract Management Console
Garante que dados em EU sao processados em conformidade
```

## Data Subject Access Requests (DSAR)

Usuario pode solicitar: "Quais dados voce tem sobre mim?"

Processamento obrigatorio:

```python
# dsar_handler.py
from datetime import datetime, timedelta

class DSARHandler:
    def __init__(self, user_id, request_date):
        self.user_id = user_id
        self.request_date = request_date
        self.response_deadline = request_date + timedelta(days=30)

    def gather_data(self):
        """Coleta TODOS dados associados ao usuario"""
        return {
            'profile': self.get_user_profile(),
            'emails': self.get_user_emails(),
            'activity': self.get_user_activity(),
            'preferences': self.get_user_preferences(),
            'payments': self.get_user_payments(),
            'communications': self.get_user_communications(),
        }

    def get_user_profile(self):
        """Incluir TODOS campos, mesmo que nao sao normalmente vistos"""
        return db.query(User).filter(User.id == self.user_id).first()

    def get_user_activity(self):
        """Incluir events, logs, etc"""
        return db.query(UserEvent).filter(
            UserEvent.user_id == self.user_id
        ).all()

    def format_response(self, data):
        """Formato acessivel (CSV, JSON, XML)"""
        # GDPR requer formato estruturado e legivel
        # Nao pode ser raw database dump
        return {
            'format': 'JSON',
            'data': data,
            'export_date': datetime.now().isoformat(),
            'note': 'Contains all personal data we process about you'
        }

    def send_response(self):
        """Enviar ao usuario por meio seguro"""
        # Encryptar arquivo
        # Enviar por email com password temporaria
        # Manter registro de envio
        pass
```

Procedimento:
1. Receber solicitacao (email, formulario, etc)
2. Verificar identidade (nao pode ser pedido publico)
3. Coletar dados de todos sistemas (3 horas a 30 dias dependendo de escopo)
4. Formatar de modo legivel
5. Enviar ao usuario (por meio seguro) dentro de 30 dias
6. Documentar no registro de DSAR

## Auditoria de Compliance

Checklist periodico:

```
MONTHLY:
[ ] Review deletion requests - foram deletados?
[ ] Check data minimization - coleta ainda necessaria?
[ ] Audit access logs - alguem acessou dados desnecessariamente?
[ ] Verify encryption - tudo ainda encriptado?

QUARTERLY:
[ ] DPIA review - novo processamento planejado?
[ ] Vendor DPA review - todos processadores tem acordo?
[ ] Retention policy audit - deletar dados vencidos
[ ] Consentimento validation - records validos?

ANNUALLY:
[ ] Privacy impact assessment completa
[ ] Testar DSAR process (completar em 30 dias)
[ ] Revisar Data Processing Register
[ ] Compliance training para staff
[ ] Audit externa se possivel
[ ] Atualizar Privacy Policy se necessario
```

Manter registro centralizado:

```yaml
# ROPA (Records of Processing Activities)
processings:
  - name: "Customer Email Marketing"
    purpose: "Send promotional emails"
    legal_basis: "Consent (opt-in)"
    data_categories:
      - Email address
      - Signup date
      - Preferences
    recipients: ["Email service provider (Mailchimp)"]
    retention: "12 months after unsubscribe"
    safeguards:
      - "AES-256 encryption at rest"
      - "TLS 1.3 in transit"
      - "Access logged"
    dpia_required: false

  - name: "Payment Processing"
    purpose: "Process customer payments"
    legal_basis: "Contract (payment is necessary)"
    data_categories:
      - Card last 4 digits
      - Transaction amount
      - Billing address
    recipients: ["Payment processor (Stripe)"]
    retention: "7 years (compliance requirement)"
    safeguards:
      - "Stripe handles encryption (PCI-DSS)"
      - "We dont store full card numbers"
    dpia_required: false
```
