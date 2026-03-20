# Oracle Cloud VM — Setup e Migração

> Guia para configurar a VM Oracle Cloud ARM e migrar o Paperclip + pipeline OpenClaw desde Fly.io.
> Criado: 2026-03-19

---

## 1. CRIAR A INSTÂNCIA VM

Na consola Oracle Cloud (cloud.oracle.com, region eu-madrid-3):

1. **Compute → Instances → Create Instance**
2. **Name:** `noticia-pipeline`
3. **Image:** Ubuntu 22.04 (Minimal)
4. **Shape:** `VM.Standard.A1.Flex`
   - OCPUs: **4** (máximo free tier)
   - Memory: **24 GB** (máximo free tier)
5. **Networking:** VCN público com subnet pública
6. **SSH keys:** Fazer upload da tua chave pública (`~/.ssh/id_rsa.pub`)
   - Se não tiveres: `ssh-keygen -t rsa -b 4096`
7. **Boot volume:** 200 GB (máximo free tier)
8. **Create**

Aguardar ~3 min até estado `RUNNING`. Anotar o **IP público**.

---

## 2. ACESSO INICIAL E CONFIGURAÇÃO BASE

```bash
# Ligar à VM (username padrão Oracle Ubuntu = ubuntu)
ssh ubuntu@<IP_PUBLICO>

# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar utilitários essenciais
sudo apt install -y curl wget git unzip build-essential software-properties-common \
  ca-certificates gnupg lsb-release htop ufw fail2ban
```

### Firewall (UFW)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 3000/tcp   # Paperclip UI
sudo ufw enable
```

> **IMPORTANTE:** A Oracle tem também Security Lists na consola web.
> Em Networking → VCN → Security Lists → Default, adicionar:
> - Ingress: TCP 3000 (0.0.0.0/0) — Paperclip UI
> - Ingress: TCP 80 e 443 (0.0.0.0/0) — opcional para proxy futuro

---

## 3. INSTALAR NODE.JS 20+ (para Paperclip)

```bash
# Via NodeSource (LTS 20.x)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verificar
node --version   # v20.x.x
npm --version

# Instalar pnpm 9.15+ (requisito do Paperclip)
npm install -g pnpm@latest
pnpm --version   # 9.x.x
```

---

## 4. INSTALAR PYTHON 3.11+ (para OpenClaw pipeline)

```bash
# Ubuntu 22.04 já vem com Python 3.10 — instalar 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Definir como padrão
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
python3 --version   # Python 3.11.x

# Instalar pip actualizado
curl -sS https://bootstrap.pypa.io/get-pip.py | python3
```

---

## 5. INSTALAR PLAYWRIGHT (para Crawl4AI)

```bash
# Dependências do browser headless em ARM
sudo apt install -y \
  libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
  libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
  libxrandr2 libgbm1 libasound2

# O Playwright será instalado via pip no ambiente virtual do pipeline
```

---

## 6. CLONAR O REPOSITÓRIO

```bash
# Na VM
cd ~
git clone https://github.com/<teu-user>/curador-de-noticias.git
cd curador-de-noticias

# Verificar estrutura
ls -la
```

---

## 7. CONFIGURAR O PIPELINE OPENCLAW (Python)

```bash
cd ~/curador-de-noticias/pipeline

# Criar ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Instalar Playwright browsers (ARM)
playwright install chromium
playwright install-deps chromium
```

### Variáveis de ambiente do pipeline

```bash
# Criar ficheiro .env no pipeline/
cat > ~/curador-de-noticias/pipeline/.env << 'EOF'
SUPABASE_URL=https://ljozolszasxppianyaac.supabase.co
SUPABASE_SERVICE_KEY=<service_role_key>
PUBLISH_API_KEY=<publish_api_key>
DEEPSEEK_API_KEY=<deepseek_api_key>
NVIDIA_API_KEY=<nvidia_api_key>
TELEGRAM_API_ID=<telegram_api_id>
TELEGRAM_API_HASH=<telegram_api_hash>
EOF

chmod 600 ~/curador-de-noticias/pipeline/.env
```

### Testar o scheduler

```bash
cd ~/curador-de-noticias/pipeline
source .venv/bin/activate
python scheduler_ollama.py
# Ctrl+C após confirmar que arranca sem erros
```

---

## 8. CONFIGURAR O PAPERCLIP

```bash
cd ~
git clone https://github.com/paperclipai/paperclip.git
cd paperclip

# Instalar dependências
pnpm install

# Setup interactivo (configura DB, auth, primeira company)
pnpm setup
```

Durante o setup, quando pedir a base de dados:
- **Database:** External PostgreSQL
- **Connection string:** `postgresql://postgres:<password>@db.ljozolszasxppianyaac.supabase.co:5432/postgres`

> O Paperclip vai criar as suas tabelas num schema próprio (`paperclip`) sem interferir com as tabelas do Curador.

### Iniciar Paperclip

```bash
cd ~/paperclip
pnpm dev   # desenvolvimento
# ou
pnpm build && pnpm start   # produção
```

Aceder em: `http://<IP_PUBLICO>:3000`

---

## 9. CONFIGURAR SERVIÇOS SYSTEMD (arranque automático)

### Pipeline OpenClaw

```bash
sudo nano /etc/systemd/system/noticia-pipeline.service
```

```ini
[Unit]
Description=Curador de Noticias — Pipeline OpenClaw
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/curador-de-noticias/pipeline
EnvironmentFile=/home/ubuntu/curador-de-noticias/pipeline/.env
ExecStart=/home/ubuntu/curador-de-noticias/pipeline/.venv/bin/python scheduler_ollama.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Paperclip

```bash
sudo nano /etc/systemd/system/paperclip.service
```

```ini
[Unit]
Description=Paperclip — Orquestrador de Agentes
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/paperclip
ExecStart=/usr/bin/pnpm start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Activar ambos

```bash
sudo systemctl daemon-reload
sudo systemctl enable noticia-pipeline paperclip
sudo systemctl start noticia-pipeline paperclip

# Verificar
sudo systemctl status noticia-pipeline
sudo systemctl status paperclip

# Logs em tempo real
journalctl -u noticia-pipeline -f
journalctl -u paperclip -f
```

---

## 10. MIGRAR SESSÃO TELEGRAM (desde Fly.io)

```bash
# No Fly.io (antes de desligar)
fly ssh console --app noticia-telegram
cat /app/sessions/curador_telegram.session | base64

# Na VM Oracle
mkdir -p ~/curador-de-noticias/telegram-collector/sessions
echo "<base64_output>" | base64 -d > ~/curador-de-noticias/telegram-collector/sessions/curador_telegram.session
```

---

## 11. CHECKLIST FINAL

- [ ] VM criada e acessível via SSH
- [ ] Node.js 20+ e pnpm 9.15+ instalados
- [ ] Python 3.11+ e venv configurados
- [ ] Repositório clonado
- [ ] `.env` com todas as API keys preenchido
- [ ] `scheduler_ollama.py` arranca sem erros
- [ ] Paperclip acessível em `http://<IP>:3000`
- [ ] Serviços systemd activos e a reiniciar automaticamente
- [ ] Sessão Telegram migrada
- [ ] Apps Fly.io (`noticia-scheduler`, `noticia-telegram`) desactivadas após confirmar Oracle estável

---

## 12. PRÓXIMO PASSO — AJUSTAR SKILLS DO PAPERCLIP

Após a VM estar funcional, ajustar os agentes do Paperclip para usar DeepSeek/Nemotron em vez de `claude_local`.
Ver: passo a passo no documento `docs/PAPERCLIP-SKILLS-CONFIG.md` (a criar).
