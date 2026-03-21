---
name: DevSecOps Pipeline
description: SAST, DAST, SCA scanning, container security, CI/CD gates, and automated security testing
phase: 6
always_active: false
---

# DevSecOps Pipeline

## SAST (Static Application Security Testing)

### Semgrep para analise generalista

Instalar:

```bash
brew install semgrep
# ou
pip install semgrep
```

Executar:

```bash
# Scan basico
semgrep --config=p/security-audit .

# Scan customizado
semgrep --config=rules/ --output=report.json --json .

# Language-specific
semgrep --config=p/javascript --lang=js src/
```

Exemplo de regra customizada:

```yaml
# rules/sql-injection.yaml
rules:
  - id: sql-injection-detect
    pattern: |
      db.query($QUERY)
    pattern-where: |
      metavariable-comparison:
        metavariable: $QUERY
        operator: "not-contains"
        pattern: "?"
    message: "Possible SQL injection - use parameterized queries"
    languages: [python]
    severity: ERROR
```

Integracao em CI/CD:

```yaml
# .github/workflows/sast.yml
name: SAST

on: [pull_request, push]

jobs:
  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Semgrep
        run: |
          pip install semgrep
          semgrep --config=p/security-audit \
                  --output=semgrep-report.json \
                  --json .

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: semgrep-results
          path: semgrep-report.json

      - name: Fail on HIGH/CRITICAL
        run: |
          CRITICAL=$(jq '[.results[] | select(.severity=="CRITICAL")] | length' semgrep-report.json)
          HIGH=$(jq '[.results[] | select(.severity=="HIGH")] | length' semgrep-report.json)
          if [ $((CRITICAL + HIGH)) -gt 0 ]; then
            echo "Found $CRITICAL critical and $HIGH high severity issues"
            exit 1
          fi
```

### CodeQL para seguranca em profundidade

Banco de dados de vulnerabilidades para multiplas linguagens:

```bash
# Instalar GitHub CLI
gh cli download

# Usar em GitHub Actions
name: CodeQL
on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: github/codeql-action/init@v2
        with:
          languages: ['javascript', 'python']
      - uses: github/codeql-action/autobuild@v2
      - uses: github/codeql-action/analyze@v2
```

Exemplo de query CodeQL (deteccao de insecure deserialization):

```
import javascript

from CallExpression call, Identifier func
where func.getName() = "JSON.parse"
  and call.getCallee() = func
  and not exists(
    Literal lit | call.getAnArgument() = lit
  )
select call, "Potential JSON parsing from untrusted source"
```

### Bandit para Python

```bash
pip install bandit

# Scan projeto
bandit -r . -f json -o bandit-report.json

# Ignorar paths
bandit -r . --skip B101,B601 --exclude "tests/,venv/"

# Severidade minima
bandit -r . -ll  # apenas MEDIUM e HIGH
```

Exemplo `.bandit`:

```yaml
exclude_dirs: ['tests', 'venv', 'docs']
skips: [B101]  # assert_used
tests: [B201, B301, B302, B303]
```

### ESLint com security plugins

```bash
npm install --save-dev eslint eslint-plugin-security

# .eslintrc.json
{
  "extends": ["eslint:recommended", "plugin:security/recommended"],
  "rules": {
    "security/detect-eval-with-expression": "error",
    "security/detect-non-literal-regexp": "warn",
    "security/detect-unsafe-regex": "error"
  }
}
```

## DAST (Dynamic Application Security Testing)

### OWASP ZAP para testes dinamicos

```bash
# Instalar
brew install zaproxy

# Scan automatico
zaproxy -cmd \
  -quickurl http://localhost:3000 \
  -quickout zap-report.html
```

Integracao em CI/CD apos deployment:

```yaml
name: DAST

on: [push]

jobs:
  dast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      # Deploy para staging
      - name: Deploy staging
        run: ./deploy-staging.sh

      - name: Wait for deployment
        run: sleep 30

      # ZAP scan
      - name: OWASP ZAP scan
        uses: zaproxy/action-baseline@v0.4.0
        with:
          target: 'http://staging.example.com'
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a'

      - name: Upload ZAP results
        uses: actions/upload-artifact@v3
        with:
          name: zap-report
          path: report_html.html
```

### Nuclei para testes especificos

```bash
# Instalar
go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest

# Scan com templates
nuclei -u http://localhost:3000 -t nuclei-templates/

# Custom template para sua aplicacao
nuclei -u http://localhost:3000 -t custom-checks/
```

Exemplo de template Nuclei:

```yaml
# custom-checks/api-auth.yaml
id: api-missing-auth
info:
  name: Missing Authentication on API Endpoints
  severity: high
  author: security-team

requests:
  - method: GET
    path:
      - "{{BaseURL}}/api/users"
      - "{{BaseURL}}/api/admin"
    matchers:
      - type: status
        status:
          - 200
          - 201
        negative: true  # Deve ser 401/403, nao 200
```

## SCA (Software Composition Analysis)

### Snyk para vulnerabilidades de dependencias

```bash
# Instalar
npm install -g snyk

# Testar projeto
snyk test

# Monitor continuamente
snyk monitor

# Fix automaticamente
snyk fix
```

Configuracao `.snyk`:

```yaml
version: v1.25.0
cli: 2.128.0

ignore:
  SNYK-JS-AXIOS-XXXX:
    - node_modules/axios:
        reason: "Mitigated by WAF"
        expires: "2024-03-01T00:00:00Z"

patch: {}
```

Integracao GitHub:

```bash
# Conectar repositorio
snyk auth --docker

# Enable automatic PR fixes
snyk monitor --project-name=myapp
```

### Trivy para multiplos formatos

```bash
# Instalar
brew install trivy

# Scan dependencias
trivy fs .

# Scan container image
trivy image myapp:latest

# Saida JSON
trivy fs . --format json --output results.json
```

Exemplo de CI/CD:

```yaml
name: Trivy Scan

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

## Container Scanning

### Trivy para imagens Docker

```bash
# Scan imagem local
trivy image myapp:latest

# Scan imagem remota
trivy image ghcr.io/user/app:latest

# Saida JSON com detalhes
trivy image --format json --output image-scan.json myapp:latest
```

Policy de scanning:

```yaml
# trivy-policy.rego (Open Policy Agent)
package trivy

deny[msg] {
    severity := input.Results[_].Severity
    severity == "CRITICAL"
    msg := sprintf("CRITICAL vulnerability found: %v", [input.Results[_].VulnerabilityID])
}

deny[msg] {
    count(input.Results[_]) > 10
    msg := "More than 10 vulnerabilities found"
}
```

### Grype para completa visibilidade

```bash
# Instalar
brew install anchore/grype/grype

# Scan imagem
grype ghcr.io/user/app:latest

# Gerar SBOM
grype ghcr.io/user/app:latest -o cyclonedx > sbom.json
```

Integracao pre-push:

```bash
#!/bin/bash
# .git/hooks/pre-push

IMAGE=$1
CRITICAL_VULNS=$(trivy image --format json "$IMAGE" | \
    jq '[.Results[] | select(.Severity == "CRITICAL")] | length')

if [ "$CRITICAL_VULNS" -gt 0 ]; then
    echo "ERROR: Found $CRITICAL_VULNS CRITICAL vulnerabilities in $IMAGE"
    exit 1
fi
```

## CI/CD Security Gates

### GitHub branch protection rules

```
Settings > Branches > Add rule (main branch)

REQUIRE:
✓ Pull request reviews before merging (2 reviewers)
✓ Dismiss stale pull request approvals
✓ Require status checks to pass:
  - SAST (Semgrep)
  - DAST (ZAP)
  - SCA (Snyk)
  - Container scan (Trivy)
  - Build succeeds
  - All tests pass
✓ Require signed commits
✓ Require branches be up to date before merging
✓ Restrict who can push to matching branches
```

### GitHub Actions security workflow

```yaml
name: Security Gates

on: [pull_request, push]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      # SAST
      - name: Semgrep SAST
        continue-on-error: true
        run: |
          pip install semgrep
          semgrep --config=p/security-audit --json --output=sast.json .

      # SCA
      - name: Trivy SCA
        continue-on-error: true
        run: |
          brew install trivy
          trivy fs . --format json --output sca.json

      # Compilar
      - name: Build
        run: npm run build

      # DAST (apenas main branch)
      - name: Deploy staging
        if: github.ref == 'refs/heads/main'
        run: ./deploy-staging.sh

      - name: DAST Scan
        if: github.ref == 'refs/heads/main'
        continue-on-error: true
        run: |
          pip install nuclei
          nuclei -u http://staging.example.com -t nuclei-templates/ -json

      # Verificacao de vulnerabilidades
      - name: Check for HIGH/CRITICAL
        run: |
          CRITICAL=$(jq '[.[] | select(.severity == "CRITICAL")] | length' sast.json)
          if [ "$CRITICAL" -gt 0 ]; then
            echo "CRITICAL vulnerabilities found"
            exit 1
          fi
```

### Signed commits requirement

```bash
# Configure branch to require signed commits
gh api repos/owner/repo/branches/main/protection \
  --input - <<EOF
{
  "required_commit_signing": true,
  "enforce_admins": true
}
EOF
```

## Pre-commit Hooks

### Instalar pre-commit framework

```bash
pip install pre-commit

# Criar .pre-commit-config.yaml
cat > .pre-commit-config.yaml <<EOF
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks

  - repo: https://github.com/semgrep/semgrep
    rev: v1.45.0
    hooks:
      - id: semgrep

  - repo: https://github.com/hadialqattan/pycln
    rev: v2.2.2
    hooks:
      - id: pycln

  - repo: local
    hooks:
      - id: npm-audit
        name: npm audit
        entry: npm audit --audit-level=high
        language: system
        files: package-lock.json
        pass_filenames: false
EOF

# Instalar hooks
pre-commit install
```

### Custom hook para security checks

```bash
#!/bin/bash
# .git/hooks/pre-commit

set -e

echo "[*] Running security checks..."

# 1. Secret detection
echo "[1] Checking for secrets..."
if command -v gitleaks &> /dev/null; then
    gitleaks protect --verbose
fi

# 2. SAST
echo "[2] Running SAST..."
npm run lint:security

# 3. Dependency audit
echo "[3] Auditing dependencies..."
npm audit --audit-level=moderate || exit 1

# 4. Format check
echo "[4] Checking code format..."
npm run format:check

echo "[✓] All security checks passed"
```

## Artifact Signing

### Sign container images com Cosign

```bash
# Gerar chave
cosign generate-key-pair

# Assinar imagem
cosign sign --key cosign.key ghcr.io/user/app:v1.0.0

# Verificar
cosign verify --key cosign.pub ghcr.io/user/app:v1.0.0
```

Verificacao em deployment:

```yaml
# Deploy verifica assinatura antes de usar
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  template:
    spec:
      containers:
      - name: app
        image: ghcr.io/user/app:v1.0.0@sha256:abcd1234...  # Use digest
      # Kubernetes pode validar assinatura com Binary Authorization
```

### Notarize commits e releases

```bash
# Criar release assinada
gh release create v1.0.0 \
  --notes "Security release" \
  --draft \
  artifacts/*

# Assinar release
cosign sign-blob \
  --key cosign.key \
  v1.0.0.tar.gz > v1.0.0.tar.gz.sig

# Publicar
gh release upload v1.0.0 v1.0.0.tar.gz.sig
```

## Deployment Verification

### Verificar integridade pre-deployment

```bash
#!/bin/bash
# verify-deployment.sh

set -e

VERSION=$1

echo "[1] Verify image signature"
cosign verify --key cosign.pub "ghcr.io/myapp:$VERSION"

echo "[2] Verify SBOM"
trivy image "ghcr.io/myapp:$VERSION" \
  --format cyclonedx --output sbom.json
if [ ! -f sbom.json ]; then
  echo "ERROR: SBOM not found"
  exit 1
fi

echo "[3] Verify no CRITICAL vulnerabilities"
CRITICAL=$(trivy image "ghcr.io/myapp:$VERSION" \
  --format json | \
  jq '[.Results[] | select(.Severity == "CRITICAL")] | length')
if [ "$CRITICAL" -gt 0 ]; then
  echo "ERROR: $CRITICAL CRITICAL vulnerabilities found"
  exit 1
fi

echo "[4] Verify commit is signed"
git verify-commit "v$VERSION" || exit 1

echo "[✓] All verifications passed"
```

### Audit log de deploys

```yaml
# Manter historico completo
deployments:
  v1.0.0:
    timestamp: "2024-03-20T10:00:00Z"
    deployed_by: "github-actions"
    image_digest: "sha256:abcd1234..."
    image_signed: true
    image_signer: "cosign"
    sbom_generated: true
    vulnerabilities_scan_passed: true
    code_review_approved: true
    reviewed_by: ["alice", "bob"]
    commit_hash: "abc123def"
    commit_signed: true
    branch: "main"
    environment: "production"
    rollback_available: "v0.9.9"
```

## Security Dashboard

Consolidar metricas de seguranca:

```python
# security_metrics.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SecurityMetrics:
    timestamp: datetime
    sast_issues_critical: int
    sast_issues_high: int
    sca_vulnerabilities_critical: int
    sca_vulnerabilities_high: int
    container_scan_issues: int
    coverage_percent: float
    last_deployment: str
    days_since_last_update: int
    compliance_score: float

    def to_json(self):
        """Para dashboard ou monitoramento"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'sast': {
                'critical': self.sast_issues_critical,
                'high': self.sast_issues_high
            },
            'sca': {
                'critical': self.sca_vulnerabilities_critical,
                'high': self.sca_vulnerabilities_high
            },
            'containers': self.container_scan_issues,
            'coverage': self.coverage_percent,
            'compliance_score': self.compliance_score
        }

# Publicar em Prometheus
def export_metrics(metrics):
    print(f"# HELP security_sast_critical SAST critical issues")
    print(f"# TYPE security_sast_critical gauge")
    print(f"security_sast_critical {metrics.sast_issues_critical}")
    # Continuar para outras metricas...
```

Alertas baseado em metricas:

```yaml
# alertas.yaml
rules:
  - alert: CriticalVulnerabilityFound
    expr: security_sast_critical > 0 or security_sca_critical > 0
    for: 5m
    annotations:
      summary: "Critical vulnerability in {{ $labels.service }}"
      action: "Trigger incident response"

  - alert: OutdatedDependencies
    expr: security_days_since_dependency_update > 90
    for: 1h
    annotations:
      summary: "Dependencies not updated in {{ $value }} days"
      action: "Schedule dependency review"

  - alert: LowCoverageScanning
    expr: security_coverage_percent < 80
    for: 24h
    annotations:
      summary: "Security scanning coverage below 80%"
      action: "Extend scanning configuration"
```
