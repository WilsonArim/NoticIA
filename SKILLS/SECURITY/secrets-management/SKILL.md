---
name: Secrets Management
description: Environment variables, .env discipline, vault systems, secret rotation, and leak detection
phase: 0
always_active: true
---

# Secrets Management

## .ENV Discipline

### Nunca fazer commit de secrets

Configurar `.gitignore` para excluir arquivos de segredo:

```
.env
.env.local
.env.*.local
.env.production.local
.env.development.local
*.key
*.pem
*.p8
secrets/
config/secrets
```

Fazer commit apenas de templates:

```bash
cp .env .env.example
# Editar .env.example para remover valores reais
git add .env.example
git add .gitignore
```

Exemplo de `.env.example`:

```
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
API_KEY=your_api_key_here
JWT_SECRET=your_jwt_secret_here
STRIPE_SECRET_KEY=sk_test_xxx
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
OPENAI_API_KEY=sk-...
DEBUG=false
```

### Validar .gitignore e historico

Verificar se secrets estao no historico:

```bash
# Procurar patterns comuns de secrets
git log -p -S 'BEGIN PRIVATE KEY' -- '*.env'
git log -p -S 'password=' -- .env

# Verificar todos os arquivos commitados
git ls-files | grep -E '\.(env|key|pem)$'
```

## Hierarchy de Variaves de Ambiente

Estabelecer ordem de precedencia clara:

1. Variaves de ambiente do sistema (export VAR=value)
2. Arquivo `.env.local` (prioridade maxima, nunca commitar)
3. Arquivo `.env.{environment}` (env-specific: development, staging, production)
4. Arquivo `.env.example` (defaults, commitar como exemplo)
5. Valores padrao no codigo

Exemplo em Node.js:

```javascript
require('dotenv').config({ path: '.env.local' });
require('dotenv').config({ path: `.env.${process.env.NODE_ENV}` });
require('dotenv').config();

const config = {
    databaseUrl: process.env.DATABASE_URL || 'postgresql://localhost/dev',
    apiKey: process.env.API_KEY,
    jwtSecret: process.env.JWT_SECRET || 'dev-secret',
    debug: process.env.DEBUG === 'true'
};

if (!config.apiKey && process.env.NODE_ENV === 'production') {
    throw new Error('API_KEY is required in production');
}
```

## Secrets Rotation Strategy

### Frequencia de rotacao

- API keys: rotacao mensal ou trimestral
- Database credentials: trimestral ou quando funcionario sai
- JWT secrets: anual ou apos compromisso
- SSH keys: anual para usuario, imediatamente se comprometida

### Procedimento de rotacao zero-downtime

```bash
# 1. Gerar novo secret
NEW_SECRET=$(openssl rand -hex 32)

# 2. Configurar sistema para aceitar ambos antigos e novos
export OLD_SECRET=$CURRENT_SECRET
export NEW_SECRET=$NEW_SECRET

# 3. Fazer deploy com suporte dual
# Codigo verifica OLD_SECRET || NEW_SECRET

# 4. Apos periodo de estabilizacao (dias)
# Remover validacao de OLD_SECRET

# 5. Fazer deploy final
# Codigo so usa NEW_SECRET

# 6. Guardar OLD_SECRET em auditoria por compliance
```

### Automacao com scripts

```bash
#!/bin/bash
# rotate_secrets.sh

VAULT_ADDR="https://vault.company.internal"
SECRET_PATH="secret/prod/api_keys"

# Renovar API key
NEW_KEY=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/$SECRET_PATH/rotate | jq -r '.data.new_key')

# Atualizar aplicacao
curl -X POST https://api.example.com/config/secrets \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -d "{\"api_key\": \"$NEW_KEY\"}"

# Confirmar atualizacao
if curl -s https://api.example.com/health | jq '.api_key_valid'; then
    echo "Secret rotation successful"
    # Guardar registro em auditoria
    logger -t secrets-rotation "API key rotated successfully"
else
    echo "Secret rotation failed - rollback"
    exit 1
fi
```

## Vault Systems

### HashiCorp Vault

Instalacao basica:

```bash
wget https://releases.hashicorp.com/vault/1.15.0/vault_1.15.0_linux_amd64.zip
unzip vault_1.15.0_linux_amd64.zip
sudo mv vault /usr/local/bin/
vault --version
```

Iniciar servidor (desenvolvimento):

```bash
vault server -dev
```

Usar Vault em aplicacao:

```bash
# Login
export VAULT_ADDR='https://vault.example.com'
vault login -method=jwt role=app

# Ler secret
vault kv get secret/prod/database

# Escrever secret
vault kv put secret/prod/api_key value="sk-1234567890"
```

Exemplo em Python:

```python
import hvac
import os

client = hvac.Client(
    url=os.environ['VAULT_ADDR'],
    token=os.environ['VAULT_TOKEN']
)

# Ler secret
secret = client.secrets.kv.read_secret_version(path='prod/database')
db_password = secret['data']['data']['password']

# Dynamically gerar credenciais temporarias
db_creds = client.secrets.databases.generate_credentials(
    name='prod_role',
    mount_point='database'
)
```

### AWS Secrets Manager

Guardar secrets na AWS:

```bash
aws secretsmanager create-secret \
    --name prod/database/password \
    --secret-string '{"username":"admin","password":"secure-pw"}'

aws secretsmanager get-secret-value \
    --secret-id prod/database/password \
    --region us-east-1
```

Em Python:

```python
import boto3
import json

client = boto3.client('secretsmanager', region_name='us-east-1')

response = client.get_secret_value(SecretId='prod/database/password')
secret = json.loads(response['SecretString'])
print(secret['password'])
```

### Doppler para ambiente multiplataforma

```bash
# Instalar
curl -Ls https://cli.doppler.com/install.sh | sh

# Login e configurar projeto
doppler login
doppler projects
doppler configure

# Rodar aplicacao com secrets do Doppler
doppler run -- npm start

# Exportar para .env local (apenas desenvolvimento)
doppler secrets download --format env > .env.local
```

### 1Password CLI para times

```bash
# Instalar
brew install 1password-cli

# Authenticate
op account add

# Ler secret
op item get "API Keys" --field "Stripe Secret" --vault "Production"

# Em scripts CI/CD
export STRIPE_KEY=$(op item get "API Keys" --field "Stripe Secret" --vault "Production")
```

## Git Pre-Commit Hooks para Deteccao

### Gitleaks

```bash
# Instalar
brew install gitleaks

# Configurar pre-commit
cat > .pre-commit-config.yaml <<EOF
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
EOF

pre-commit install
```

### TruffleHog

```bash
# Instalar
pip install truffleHog

# Escanear repositorio
trufflehog git file:// . --debug

# Escanear historico
trufflehog git https://github.com/user/repo.git
```

### Custom git hook script

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Patterns para detectar
PATTERNS=(
    "BEGIN.*PRIVATE KEY"
    "aws_access_key_id"
    "api_key\s*=\s*['\"][^'\"]+['\"]"
    "password\s*=\s*['\"][^'\"]+['\"]"
    "token\s*=\s*['\"][^'\"]+['\"]"
)

# Verificar arquivos staged
git diff --cached --name-only | while read file; do
    for pattern in "${PATTERNS[@]}"; do
        if git diff --cached "$file" | grep -iP "$pattern" > /dev/null; then
            echo "ERROR: Potential secret found in $file"
            exit 1
        fi
    done
done
```

## Incident Response - Secret Leaks

### Protocolo imediato

1. Confirmar leak (repositorio publico, log, screenshot)
2. Gerar novo secret imediatamente
3. Fazer revoke do antigo em todos os sistemas
4. Buscar por uso/acesso malicioso (logs, anomalias)
5. Fazer commit com novo secret e força push se necessario
6. Notificar equipe e stakeholders
7. Rever como ocorreu (post-mortem)

```bash
#!/bin/bash
# respond_to_leak.sh

SECRET_NAME=$1
NEW_SECRET=$(openssl rand -hex 32)

echo "[1] Revogar secret antigo"
vault write -f secret/admin/revoke/$SECRET_NAME old_value="$OLD_SECRET"

echo "[2] Atualizar em todos os servicos"
for service in api web worker; do
    curl -X POST https://$service.example.com/admin/secrets/rotate \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -d "{\"secret_name\": \"$SECRET_NAME\", \"new_value\": \"$NEW_SECRET\"}"
done

echo "[3] Procurar uso malicioso"
# Revisar logs de 24h antes da descoberta
elk-query "api_calls" "since:now-24h" "auth_token:*" | grep -c "failed"

echo "[4] Criar issue de post-mortem"
gh issue create --title "Security: $SECRET_NAME leak response" \
    --body "Leakage discovered. Secret rotated. Review and post-mortem required."
```

### Limpeza do Git

Se secret foi commitado:

```bash
# Usar BFG Repo-Cleaner (mais simples que filter-branch)
brew install bfg

# Criar lista de patterns a remover
cat > .bfg-secrets.txt <<EOF
(?i)(password|api_key|secret|token)\s*[=:]\s*.{20,}
EOF

# Remover do historico
bfg --replace-text .bfg-secrets.txt

# Force push (com cuidado!)
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force-with-lease
```

## API Key Scoping

### Principio de minimo privilegio

Criar diferentes chaves para diferentes propositos:

```bash
# Chave apenas leitura para metricas
stripe_key_readonly=rk_live_xxx (read analytics, no charges)

# Chave de leitura/escrita limitada para produto especifico
stripe_key_product_a=sk_live_yyy (only product A charges)

# Chave admin - altamente restrita, usar apenas em migracao
stripe_key_admin=sk_live_admin_zzz

# Para API externa
github_token_readonly=ghp_xxxx (public repo only)
github_token_actions=ghp_yyyy (workflows, no admin)
```

Exemplo de rotacao de chaves por escopo:

```bash
# Daily rotation de chaves read-only (menos risco)
if [[ $(date +%u) == "1" ]]; then
    # Rotar chaves de apenas leitura todas segundas
    vault write -f secret/rotation/read_only
fi

# Monthly rotation de chaves read-write
if [[ $(date +%d) == "01" ]]; then
    vault write -f secret/rotation/read_write
fi

# Quarterly rotation de chaves admin
if [[ $(date +%j) == "001" || $(date +%j) == "092" || ... ]]; then
    vault write -f secret/rotation/admin
fi
```

## Database Credential Management

### Credenciais dinamicas com Vault

```hcl
# Configurar banco de dados em Vault
path "database/config/postgres" {
  capabilities = ["read"]
}

path "database/static-creds/app_user" {
  capabilities = ["read"]
}
```

```bash
# Gerar credenciais temporarias
vault read database/static-creds/app_user

# Role com rotacao automatica
vault write database/roles/app_role \
    db_name=postgres \
    creation_statements="CREATE ROLE \"{{name}}\" WITH PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';" \
    default_ttl="1h" \
    max_ttl="24h"
```

Em aplicacao:

```python
import hvac

vault = hvac.Client()
creds = vault.secrets.databases.generate_credentials(name='app_role')
db_user = creds['data']['username']
db_pass = creds['data']['password']

# Conectar com credenciais temporarias (TTL 1h)
db = psycopg2.connect(
    host="postgres.internal",
    user=db_user,
    password=db_pass
)
```

## CI/CD Secrets

### GitHub Secrets

Adicionar secrets em Settings > Secrets and variables > Actions:

```
DATABASE_PASSWORD: xxxxx
API_KEY: xxxxx
DOCKER_TOKEN: xxxxx
```

Usar em workflow:

```yaml
name: Deploy

on: [push]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v3

      - name: Deploy
        env:
          DATABASE_PASSWORD: ${{ secrets.DATABASE_PASSWORD }}
          API_KEY: ${{ secrets.API_KEY }}
        run: |
          ./deploy.sh
```

### Environment Protection Rules

Proteger secrets em producao:

```
Environment: production
  Required reviewers: 2
  Deployment branches: main
  Prevent reviewers from deploying: checked
```

### GitLab CI/CD

```yaml
deploy:
  stage: deploy
  variables:
    API_KEY: $SECRET_API_KEY  # Definido em Settings > CI/CD > Variables
  protected: true  # So roda em branches protegidas
  environment:
    name: production
    url: https://example.com
  script:
    - ./deploy.sh
  only:
    - main
```

Mascarar secrets em logs:

```yaml
variables:
  SENSITIVE_VAR:
    value: "very_secret_value"
    protected: true
```

## Auditoria de Secrets

Manter registro de acesso:

```bash
# Vault audit log
vault audit enable file file_path=/var/log/vault-audit.log

# CloudTrail para AWS Secrets Manager
aws cloudtrail describe-trails --region us-east-1

# Revisar quem acessou secrets
vault audit list
vault read sys/audit
```

Periodicamente verificar secrets em uso:

```bash
#!/bin/bash
# audit_secrets.sh - rodar mensalmente

echo "=== Secrets nao rotacionados por 90 dias ==="
vault list secret/metadata | while read secret; do
    last_update=$(vault kv metadata get secret/$secret | grep -i "created_time" | head -1)
    echo "secret/$secret: $last_update"
done

echo "=== Verificar chaves desnecessarias ==="
vault list auth/approle/role
vault list secret/admin
```
