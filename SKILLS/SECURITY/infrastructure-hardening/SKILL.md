---
name: Infrastructure Hardening
description: Secure server configuration, SSH hardening, firewall rules, kernel tuning, and systemd isolation
phase: 6
always_active: false
---

# Infrastructure Hardening

## SSH Hardening

### Autenticacao apenas por chave

Desabilitar autenticacao por senha para força chaves SSH robustas. Editar `/etc/ssh/sshd_config`:

```
PasswordAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
```

Gerar chaves RSA 4096 ou ED25519:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
```

Manter permissoes corretas:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
chmod 600 ~/.ssh/authorized_keys
```

### Fail2Ban para mitigacao de forca bruta

Instalar e configurar:

```bash
sudo apt install fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
```

Editar `/etc/fail2ban/jail.local`:

```
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
findtime = 600
bantime = 3600
```

Reiniciar servico:

```bash
sudo systemctl restart fail2ban
```

### Mudanca de porta e restricoes

Editar `/etc/ssh/sshd_config`:

```
Port 2222
AllowUsers user1 user2
PermitRootLogin no
X11Forwarding no
AllowTcpForwarding no
PermitEmptyPasswords no
ClientAliveInterval 300
ClientAliveCountMax 2
```

Validar configuracao e recarregar:

```bash
sudo sshd -t
sudo systemctl reload ssh
```

## Firewall Configuration

### UFW (Uncomplicated Firewall)

```bash
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 2222/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status verbose
```

### Iptables Rules

Exemplo de regras completas:

```bash
# Permitir loopback
sudo iptables -A INPUT -i lo -j ACCEPT

# Permitir SSH em porta customizada
sudo iptables -A INPUT -p tcp --dport 2222 -j ACCEPT

# Permitir HTTP/HTTPS
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Rate limiting SSH
sudo iptables -A INPUT -p tcp --dport 2222 -m limit --limit 10/minute --limit-burst 20 -j ACCEPT

# Descartar padroes (DROP)
sudo iptables -A INPUT -j DROP

# Salvar configuracao
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

### NFTables (moderna alternativa)

```bash
sudo nft add table inet filter
sudo nft add chain inet filter input { type filter hook input priority 0 \; }
sudo nft add rule inet filter input iif lo accept
sudo nft add rule inet filter input tcp dport 2222 limit rate 10/minute accept
sudo nft add rule inet filter input tcp dport { 80, 443 } accept
sudo nft add rule inet filter input counter drop
```

## Swap Configuration

Desabilitar swap se nao necessario ou criptografar:

```bash
# Verificar swap atual
swapon --show

# Desabilitar permanentemente
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab

# Ou criptografar swap com dm-crypt
sudo cryptsetup close swap
sudo cryptsetup open --type plain /dev/sdX1 swap
```

## Kernel Hardening

Editar `/etc/sysctl.d/99-hardening.conf`:

```
# Protecao contra SYN flood
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048

# Desabilitar redirecao de pacotes
net.ipv4.ip_forward = 0
net.ipv6.conf.all.forwarding = 0

# Desabilitar ICMP redirects
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Ativar reverse path filtering
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Ativar execshield
kernel.exec-shield = 1

# Ativar ASLR
kernel.randomize_va_space = 2

# Limitar dmesg access
kernel.dmesg_restrict = 1

# Restringir acesso a /proc/sys/kernel/modules
kernel.modules_disabled = 1
```

Aplicar:

```bash
sudo sysctl -p /etc/sysctl.d/99-hardening.conf
```

## TLS/SSL e Certificados

### Let's Encrypt com Certbot

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d example.com -d www.example.com
sudo certbot renew --dry-run
```

Automacao de renovacao:

```bash
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### Configuracao Nginx para TLS 1.3

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

## Reverse Proxy Security

### Nginx com rate limiting

```nginx
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;

server {
    location / {
        limit_req zone=general burst=20 nodelay;
    }

    location /api/ {
        limit_req zone=api burst=5 nodelay;
    }
}
```

### Headers de seguranca

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline';" always;
```

### Caddy (alternativa simplificada)

```
example.com {
    reverse_proxy localhost:8080 {
        header_up X-Real-IP {http.request.remote.host}
    }

    encode gzip

    @ratelimit {
        rate-limit * 100r/m
    }
    handle @ratelimit {
        abort 429
    }
}
```

## File System Permissions

Configurar permissoes apropriadas:

```bash
# Diretorio de usuario
chmod 750 /home/user
chmod 700 /home/user/.ssh

# Arquivos de aplicacao
sudo chown app:app /opt/application
sudo chmod 755 /opt/application
sudo chmod 644 /opt/application/config.json

# Logs sensveis
sudo chmod 600 /var/log/auth.log
sudo chmod 600 /var/log/secure
```

Remover permissoes SUID desnecessarias:

```bash
sudo find / -xdev -perm -4000 -type f -print
sudo chmod u-s /path/to/binary
```

## Unattended Upgrades

Instalacao automatica de atualizacoes de seguranca:

```bash
sudo apt install unattended-upgrades apt-listchanges
sudo dpkg-reconfigure -plow unattended-upgrades
```

Configurar `/etc/apt/apt.conf.d/50unattended-upgrades`:

```
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};

Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Mail "root";
Unattended-Upgrade::AutoReboot "true";
Unattended-Upgrade::AutoRebootWithUsers "false";
Unattended-Upgrade::AutoRebootTime "02:00";
```

## Systemd Service Isolation

Exemplo de servico com isolamento:

```ini
[Unit]
Description=MyApplication
After=network.target

[Service]
Type=simple
User=appuser
ExecStart=/opt/myapp/bin/start

PrivateTmp=yes
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/myapp
ProtectClock=yes
ProtectHostname=yes
ProtectKernelLogs=yes
ProtectKernelModules=yes
ProtectKernelTunables=yes
RemoveIPC=yes
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
RestrictNamespaces=yes
RestrictRealtime=yes
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

MemoryLimit=512M
TasksMax=100

Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Verificar servico:

```bash
sudo systemd-analyze security myapp.service
```

## Log Rotation

Configurar `/etc/logrotate.d/myapp`:

```
/var/log/myapp/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 appuser appuser
    postrotate
        systemctl reload myapp > /dev/null 2>&1 || true
    endscript
}
```

Testar:

```bash
sudo logrotate -f /etc/logrotate.d/myapp
```

## Disk Encryption

### LUKS para volumes existentes

```bash
# Criar container criptografado
sudo cryptsetup luksFormat /dev/sdX1
sudo cryptsetup luksOpen /dev/sdX1 encrypted_volume
sudo mkfs.ext4 /dev/mapper/encrypted_volume
sudo mkdir /mnt/encrypted
sudo mount /dev/mapper/encrypted_volume /mnt/encrypted

# Adicionar ao fstab
echo "/dev/mapper/encrypted_volume /mnt/encrypted ext4 defaults 0 2" | sudo tee -a /etc/fstab
```

### Full Disk Encryption durante instalacao

Durante instalacao da distro, selecionar opcao de criptografia de disco completo (FDE). Isso protege `/boot` e `/` com LUKS.

## Auditoria de Configuracao

Executar verificacoes periodicas:

```bash
# Checar SSH config
sudo sshd -T | grep -E "permitemptypasswords|passwordauthentication|permitrootlogin"

# Listar usuarios com shell
awk -F: '$NF != "/usr/sbin/nologin" && $NF != "/bin/false" { print $1 }' /etc/passwd

# Encontrar arquivos SUID/SGID
sudo find / -xdev \( -perm -4000 -o -perm -2000 \) -type f
```

Implementar verificacoes em scripts de deploy para garantir hardening continuo.
