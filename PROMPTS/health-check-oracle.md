# Health Check — Oracle VM Pipeline

Liga-te ao servidor Oracle via SSH e faz uma verificação completa do pipeline NoticIA V3.

```
ssh -i ~/.ssh/oracle_noticia.key ubuntu@82.70.84.122
```

## Verifica TUDO isto, em ordem:

### 1. Containers Docker
```bash
cd ~/noticia && docker compose ps
```
Confirma que os 3 containers estão "Up" e "healthy":
- `noticia-pipeline`
- `noticia-diretor-elite`
- `noticia-telegram-collector`

Se algum estiver "restarting" ou "exited", mostra os logs:
```bash
docker compose logs --tail 50 <container>
```

### 2. Logs do pipeline (últimos erros)
```bash
docker compose logs --tail 100 pipeline 2>&1 | grep -i "error\|exception\|critical\|traceback"
```
Reporta TODOS os erros encontrados.

### 3. Scheduler — jobs activos
```bash
docker compose logs --tail 200 pipeline 2>&1 | grep -E "Scheduler|job|interval|Running"
```
Confirma que os 8 jobs estão a correr nos intervalos correctos:
- collectors: 15 min
- dispatcher: 30 min
- fact_checker_parallel: 15 min
- editorial_decisor: 10 min
- escritor: 15 min
- pipeline_health: 30 min
- coverage_analyzer: 6h
- cronistas: domingo 10:00 UTC

### 4. Telegram collector
```bash
docker compose logs --tail 50 telegram-collector 2>&1
```
Verifica se está activo ou se tem erros de flood-wait / sessão expirada.

### 5. Diário de Bordo (estenógrafo)
```bash
tail -80 ~/noticia/DIARIO-DE-BORDO.md
```
Verifica:
- Qual é a última entrada? (data)
- Está a ser actualizado diariamente às ~00:00 UTC?
- Se a última entrada é anterior a ontem, o estenógrafo está AVARIADO

Também verifica se o ficheiro está montado no container:
```bash
docker compose exec pipeline ls -la /app/DIARIO-DE-BORDO.md 2>/dev/null || echo "FICHEIRO NAO MONTADO NO CONTAINER"
```
Se não estiver montado, verifica o docker-compose.yml para ver os volumes.

### 6. Recursos do servidor
```bash
free -h && echo "---" && df -h / && echo "---" && uptime
```
Alerta se:
- RAM livre < 500MB
- Disco usado > 80%
- Load average > 4.0

### 7. Dispatcher interval
Confirma que o dispatcher está realmente a 30 min (não 5 min):
```bash
docker compose exec pipeline grep -n "dispatcher" /app/src/openclaw/scheduler_ollama.py | head -5
```

## Formato do relatório

Reporta assim:
```
🔍 HEALTH CHECK — Oracle VM NoticIA V3
Data: YYYY-MM-DD HH:MM UTC

CONTAINERS: ✅/❌ (detalhe)
ERROS RECENTES: ✅ nenhum / ❌ (lista)
SCHEDULER: ✅ 8 jobs activos / ❌ (detalhe)
TELEGRAM COLLECTOR: ✅ activo / ❌ (erro)
DIÁRIO DE BORDO: ✅ última entrada DD/MM / ❌ sem entradas recentes
RECURSOS: RAM XX% | Disco XX% | Load X.X
DISPATCHER INTERVAL: ✅ 30 min / ❌ ainda a 5 min
```
