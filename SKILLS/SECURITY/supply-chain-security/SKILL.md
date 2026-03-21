---
name: Supply Chain Security
description: Dependency pinning, vulnerability scanning, SBOMs, signed commits, and typosquatting detection
phase: 5
always_active: false
---

# Supply Chain Security

## Dependency Pinning

### Package Manager Lockfiles

Sempre commitar arquivos de lock para reproducibilidade exata:

**npm/yarn:**
```bash
# package-lock.json ou yarn.lock devem estar versionados
git add package-lock.json
git commit -m "Update dependencies"

# Para instalar, usar ci (clean install) em CI/CD
npm ci  # Usa exatamente as versoes de package-lock.json
yarn ci --frozen-lockfile
```

**Python:**
```bash
# requirements.txt com versoes fixas
pip freeze > requirements.txt
cat requirements.txt

# Melhor: usar pip-compile para gerar determiniticamente
pip install pip-tools
pip-compile requirements.in
git add requirements.txt
```

Exemplo `requirements.in`:
```
flask>=2.0.0,<3.0.0
sqlalchemy>=2.0.0,<3.0.0
requests>=2.28.0
```

```bash
pip-compile requirements.in  # Gera requirements.txt com todos hashes
```

**Cargo (Rust):**
```bash
# Cargo.lock obrigatorio para binarios
cargo build
git add Cargo.lock

# Verificar versoes exatas
cargo tree --locked
```

### Evitar versoes flutuantes

Ruim:
```json
{
  "dependencies": {
    "express": "^2.0.0",  // Qualquer 2.x.x
    "lodash": "*"         // Qualquer versao
  }
}
```

Bem:
```json
{
  "dependencies": {
    "express": "2.28.1",
    "lodash": "4.17.21"
  }
}
```

Usar `npm ci` em CI/CD, nunca `npm install`:

```yaml
# GitHub Actions
- name: Install dependencies
  run: npm ci
```

## NPM/Pip/Cargo Audit Automation

### Verificacao local antes de commit

```bash
# npm audit
npm audit --audit-level=moderate

# pip-audit
pip install pip-audit
pip-audit

# cargo audit
cargo install cargo-audit
cargo audit --deny warnings
```

### GitHub Dependabot automatico

Configurar `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "daily"
      time: "03:00"
    open-pull-requests-limit: 5
    reviewers:
      - "security-team"
    labels:
      - "dependencies"
      - "security"
    allow:
      - dependency-type: "direct"
      - dependency-type: "indirect"
    ignore:
      - dependency-name: "old-insecure-package"

  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    version-update-strategy: "increase-minor"

  - package-ecosystem: "cargo"
    directory: "/"
    schedule:
      interval: "weekly"
```

### CI/CD scan em pull requests

GitHub Actions para audit obrigatorio:

```yaml
name: Dependency Audit

on: [pull_request, push]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - run: npm ci

      - name: npm audit
        run: npm audit --audit-level=high

      - name: OWASP Dependency Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          project: 'MyApp'
          path: '.'
          format: 'JSON'

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: dependency-check-report
          path: reports/
```

## SBOM Generation

### CycloneDX para software bill of materials

Instalar ferramentas:

```bash
# Node.js
npm install -g @cyclonedx/cyclonedx-npm

# Python
pip install cyclonedx-python

# Geral (Java-based)
brew install cyclonedx-cli
```

Gerar SBOM:

```bash
# npm
cyclonedx-npm --output-file sbom.json

# Python
cyclonedx-py -o sbom.json requirements.txt

# CLI generico
cyclonedx-cli resource  --input-file package.json --output-file sbom.json
```

Exemplo de SBOM JSON:

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "version": 1,
  "components": [
    {
      "type": "library",
      "name": "express",
      "version": "4.18.2",
      "purl": "pkg:npm/express@4.18.2",
      "licenses": [
        {
          "license": {
            "id": "MIT"
          }
        }
      ]
    }
  ]
}
```

### SPDX para compliance

```bash
# Gerar SPDX Document
pip install spdx-tools

spdx-generator \
  --input-dir . \
  --output-file sbom.spdx \
  --license-list-file LICENSES.spdx
```

Exemplo SPDX:

```
SPDXVersion: SPDX-2.3
DataLicense: CC0-1.0
SPDXID: SPDXRef-DOCUMENT
DocumentName: MyApp
DocumentNamespace: https://example.com/sbom/myapp
Creator: Tool: cyclonedx-generator

PackageName: MyApp
SPDXID: SPDXRef-Package
PackageVersion: 1.0.0
PackageDownloadLocation: https://github.com/user/myapp
FilesAnalyzed: true
PackageVerificationCode: da39a3ee5e6b4b0d3255bfef95601890afd80709

ExternalRef: SECURITY cpe23Type cpe:2.3:a:myapp:myapp:1.0.0:*:*:*:*:*:*:*
```

## Signed Commits

### GPG Signing

Gerar chave GPG:

```bash
gpg --full-generate-key
# ou
gpg --default-new-key-algo rsa4096 --gen-key

# Listar chaves
gpg --list-secret-keys

# Copiar key ID (ultime 16 caracteres)
```

Configurar Git:

```bash
git config user.signingkey [KEY-ID]
git config commit.gpgsign true
git config gpgsign true
```

Fazer commits assinados:

```bash
git commit -S -m "Feature: add auth"

# Verificar assinatura
git log --show-signature
git verify-commit HEAD
```

Configurar em GitHub:

1. Copy public key: `gpg --armor --export [KEY-ID]`
2. Settings > SSH and GPG keys > New GPG key
3. Paste public key

### SSH Signing (alternativa)

Usar chave SSH para assinar commits:

```bash
git config user.signingkey ~/.ssh/id_ed25519.pub
git config gpg.format ssh
git config commit.gpgsign true

# Assinar manualmente
git commit -S -m "Feature: add auth"
```

### Enforce signed commits em main branch

GitHub branch protection rules:

```
Require signed commits: checked
```

Ou via API:

```bash
gh api repos/owner/repo/branches/main/protection \
  --input - <<EOF
{
  "required_commit_signing": true
}
EOF
```

## Sigstore e Cosign para Container Images

### Instalar Cosign

```bash
brew install sigstore/tap/cosign
cosign version
```

### Assinar container image

```bash
# Login no container registry
cosign login ghcr.io

# Gerar chave privada (uma vez)
cosign generate-key-pair

# Assinar imagem
cosign sign --key cosign.key ghcr.io/user/app:v1.0.0

# Verificar assinatura
cosign verify --key cosign.pub ghcr.io/user/app:v1.0.0
```

### Assinar com Keyless (GitHub Oidc)

```bash
# Assinar usando autenticacao GitHub (sem chave armazenada localmente)
cosign sign --keyless ghcr.io/user/app:v1.0.0

# Durante CI/CD (GitHub Actions)
# Usa automaticamente OIDC token

# Verificar
cosign verify --certificate-identity-regexp https://github.com/user/app/.github/workflows/release.yml@main ghcr.io/user/app:v1.0.0
```

### Policy enforcement com Kyverno

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signatures
spec:
  validationFailureAction: enforce
  rules:
  - name: verify-cosign
    match:
      resources:
        kinds:
        - Pod
    verifyImages:
    - imageReferences:
      - ghcr.io/user/app:*
      attestations:
      - name: signed-attestation
        predicateType: cosign.sigstore.dev/attestation/vuln/v1
        conditions:
        - all:
          - key: "{{ attestation.vulnerability }}"
            operator: equals
            value: "fixed"
      cosignPubKey: |-
        -----BEGIN PUBLIC KEY-----
        ...
        -----END PUBLIC KEY-----
```

## Dependabot e Renovate

### GitHub Dependabot Advanced Config

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "daily"
      time: "03:00"

    # Agrupar updates
    groups:
      development-dependencies:
        patterns:
          - "@typescript-eslint/*"
          - "eslint*"
        update-types:
          - "minor"
          - "patch"
      production:
        patterns:
          - "*"
        update-types:
          - "major"

    # Ignorar algumas atualizacoes
    ignore:
      - dependency-name: "old-package"
      - dependency-name: "unused-lib"
        versions:
          - "> 1.0"

    # Customizar mensagens de PR
    pull-request-branch-name:
      separator: "-"
    commit-message:
      prefix: "chore(deps):"
      include: "scope"
```

### Renovate para monorepos

```json
{
  "extends": [
    "config:base",
    ":dependencyDashboard",
    ":semanticCommits"
  ],
  "packageRules": [
    {
      "matchUpdateTypes": ["minor", "patch"],
      "automerge": true
    },
    {
      "matchDepTypes": ["devDependencies"],
      "automerge": true
    },
    {
      "matchPackagePatterns": ["typescript"],
      "automerge": false,
      "groupName": "Major TypeScript update"
    }
  ],
  "vulnerabilityAlerts": {
    "enabled": true
  }
}
```

## Typosquatting Detection

### Monitoring de registros

Verificar pacotes similares ao seu:

```bash
# npm - procurar por parecidos
npm search myapp-typo

# PyPI - search similar
python -m pip search "similarpackage" || \
  curl https://pypi.org/pypi/similarpackage/json

# Cargo - checar registry
cargo search myapp
```

### Automacao com script

```bash
#!/bin/bash
# detect_typosquatting.sh

PACKAGE_NAME="myapp"

# Verificar variantes comuns
VARIANTS=(
    "${PACKAGE_NAME}-js"
    "${PACKAGE_NAME}-py"
    "${PACKAGE_NAME}s"
    "my-app"
    "my_app"
    "myapps"
    "myapp-lib"
)

for variant in "${VARIANTS[@]}"; do
    echo "Checking for $variant in npm..."
    RESULT=$(npm view $variant 2>/dev/null)
    if [ $? -eq 0 ]; then
        OWNER=$(npm view $variant maintainers | head -1)
        echo "WARNING: Found similar package '$variant' owned by $OWNER"
        # Alertar se nao for seu repositorio
        if [[ ! "$OWNER" =~ "your-org" ]]; then
            echo "ALERT: Potential typosquatting candidate!"
        fi
    fi
done
```

### Verificacao em PR automatizada

```yaml
name: Typosquatting Check

on: [pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Check added dependencies
        run: |
          git diff HEAD~1 package.json | grep '"' | grep '+' | \
          grep -oP '(?<=")\K[^"]+(?=":)' | while read pkg; do
            echo "Checking: $pkg"
            npm view "$pkg" --json | jq '.name, .maintainers[0]'
          done
```

## Revisar Dependencias Antes de Adicionar

Checklist antes de adicionar uma dependencia:

```
[ ] Package existe em registrador oficial (npm, PyPI, etc)
[ ] Proprietario/maintainer identificado e confiavel
[ ] Package tem releases regulares (< 2 anos sem update)
[ ] Package tem testes e CI/CD pipeline
[ ] Download count / usage atual (nao muito novo ou abandonado)
[ ] Licenca compativel com projeto
[ ] Sem issues abertas de seguranca grave
[ ] Menos de 10 dependencias transitivias
[ ] Codebase revisado (se critico) em GitHub/GitLab
[ ] Nao tem features que podem ser feitas em-house simples
```

Script de verificacao:

```bash
#!/bin/bash
# check_dependency.sh PACKAGE_NAME

PKG=$1

echo "=== Checking $PKG ==="

echo "1. Latest version:"
npm view $PKG version

echo "2. Last publish date:"
npm view $PKG time | tail -1

echo "3. Maintainers:"
npm view $PKG maintainers

echo "4. Vulnerabilities:"
npm audit --json | jq ".vulnerabilities[] | select(.module == \"$PKG\")"

echo "5. License:"
npm view $PKG license

echo "6. Dependencies count:"
npm view $PKG dependencies | wc -l
```

## CVE Monitoring

### Setup automatico de alertas

```bash
# Usar GitHub's dependency scanning nativo
# Settings > Code security > Dependabot > Enable Dependabot alerts

# Ou integrar com serviço externo
pip install safety
safety check requirements.txt

# Ou Snyk
npm install -g snyk
snyk auth
snyk test
```

### RSS feeds CVE

```bash
# Monitorar NVD RSS
curl https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-2024.json | \
  jq '.CVE_Items[] | select(.cve.description.description_data[0].value | contains("expression-language")) | .cve.CVE_data_meta.ID'
```

## License Compliance

### Verificacao de licenca automatizada

```bash
# npm
npm install -g license-checker
license-checker --json > licenses.json

# Python
pip install pip-licenses
pip-licenses --format=json --output-file=licenses.json

# Cargo
cargo-license --json
```

Exemplo de conformidade:

```bash
#!/bin/bash
# verify_licenses.sh

# Licencas permitidas
ALLOWED=("MIT" "Apache-2.0" "BSD-2-Clause" "BSD-3-Clause" "ISC")

license-checker --json | jq -r 'to_entries[] | "\(.value.licenses)"' | \
while read license; do
    if [[ ! " ${ALLOWED[@]} " =~ " ${license} " ]]; then
        echo "ERROR: Disallowed license: $license"
        exit 1
    fi
done

echo "All licenses OK"
```

Integracao em CI/CD:

```yaml
- name: Check licenses
  run: |
    npm install -g license-checker
    license-checker \
      --onlyAllow "MIT,Apache-2.0,BSD-2-Clause,BSD-3-Clause,ISC" \
      --fail-on disallowed
```
