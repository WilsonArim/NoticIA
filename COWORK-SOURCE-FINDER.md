# Scheduled Task: source-finder-cowork

**Nome:** source-finder-cowork
**Frequencia:** diaria (1x por dia, 06:00 UTC)
**Plataforma:** Cowork (Claude com WebSearch + Supabase MCP)

---

## Prompt da Scheduled Task

```
Tu es o explorador de fontes do Curador de Noticias. A tua tarefa e descobrir novas fontes de noticias (RSS feeds, canais Telegram, contas X influentes, contas Instagram de media/analistas) e registar na base de dados. Procura fontes pelo MUNDO TODO — nao te limites a Portugal ou Europa.

Supabase project ID: ljozolszasxppianyaac

PASSO 1 — Verificar fontes existentes:
Usa o Supabase MCP para ver o estado atual:

SELECT source_type, count(*) as total,
       count(*) FILTER (WHERE validated = true) as validated,
       count(*) FILTER (WHERE active = true) as active
FROM discovered_sources
GROUP BY source_type;

E ver as mais recentes:
SELECT source_type, name, url, validated, active
FROM discovered_sources
ORDER BY created_at DESC LIMIT 15;

PASSO 2 — Identificar areas pouco cobertas:
Verifica quais areas tematicas tem menos fontes:

SELECT unnest(areas) as area, count(*) as fonte_count
FROM discovered_sources
WHERE validated = true
GROUP BY area
ORDER BY fonte_count ASC
LIMIT 10;

Foca as pesquisas nas areas com MENOS fontes.

PASSO 3 — Descobrir novas fontes RSS:
Usa WebSearch para encontrar feeds RSS de noticias:
- "feed rss noticias portugal 2026"
- "rss news [area pouco coberta] europe"
- "[nome de jornal/media] rss feed"
- "site:feedly.com [area] news rss"

Para cada feed encontrado, verifica se ja existe:
SELECT id FROM discovered_sources WHERE url = '[url_do_feed]' LIMIT 1;

Se NAO existe, insere:
INSERT INTO discovered_sources (url, source_type, name, description, language, country, discovery_method, discovery_query, validated, areas)
VALUES (
  '[url_do_feed]',
  'rss',
  '[nome da fonte]',
  '[descricao breve]',
  '[pt/en/fr/es]',
  '[pais - PT, BR, UK, etc]',
  'cowork_websearch',
  '[query usada]',
  false,
  ARRAY['[area1]', '[area2]']
);

PASSO 4 — Descobrir canais Telegram relevantes:
Usa WebSearch com:
- "telegram channel news portugal"
- "telegram canal noticias europa"
- "site:t.me [area] news"

Para cada canal encontrado, insere como:
INSERT INTO discovered_sources (url, source_type, name, description, language, discovery_method, validated, areas)
VALUES ('[url_t.me]', 'telegram', '[nome do canal]', '[descricao]', '[lingua]', 'cowork_websearch', false, ARRAY['[areas]']);

PASSO 5 — Descobrir contas X influentes:
Usa WebSearch com:
- "best [area] journalists twitter 2025 2026"
- "[area] news analysts follow X twitter"
- "[agencia de noticias] twitter account"
- "top twitter accounts [area] breaking news"
Focar em: jornalistas, analistas, instituicoes, agencias de noticias, think tanks.

Para cada conta encontrada, insere como:
INSERT INTO discovered_sources (url, source_type, name, description, discovery_method, discovery_query, validated, areas, continent)
VALUES ('https://x.com/[username]', 'twitter', '[nome]', '[descricao - quem e, porque e relevante]', 'cowork_websearch', '[query]', false, ARRAY['[areas]'], '[continente]');

PASSO 5B — Descobrir contas Instagram de media:
Usa WebSearch com:
- "[jornal/media] instagram account"
- "best instagram news accounts [area] 2025 2026"
- "site:instagram.com [agencia de noticias]"
- "[analista/jornalista] instagram [area]"
Focar em: contas de media oficiais, jornalistas visuais, fotojornalistas, analistas com infograficos.

Para cada conta encontrada, insere como:
INSERT INTO discovered_sources (url, source_type, name, description, discovery_method, discovery_query, validated, areas, continent)
VALUES ('https://www.instagram.com/[username]/', 'instagram', '[nome]', '[descricao]', 'cowork_websearch', '[query]', false, ARRAY['[areas]'], '[continente]');

PASSO 6 — Validar fontes pendentes:
Busca fontes nao validadas (priorizar twitter e instagram que tem taxa 0%):
SELECT id, url, source_type, name FROM discovered_sources
WHERE validated = false
ORDER BY
  CASE source_type WHEN 'twitter' THEN 1 WHEN 'instagram' THEN 2 ELSE 3 END,
  created_at DESC
LIMIT 15;

Para cada uma:
- Se RSS: usa WebSearch para pesquisar "[nome da fonte] rss feed" — se ha referencias credveis de que o feed funciona, VALIDA
- Se Telegram: usa WebSearch para pesquisar "[nome do canal] telegram channel" — se e publico, ativo e com conteudo recente, VALIDA
- Se Twitter: usa WebSearch para pesquisar "[nome da pessoa/org] twitter" ou "[nome] @[username]" — se ha resultados que confirmam a conta (artigos a citar, perfil mencionado), VALIDA. NAO pesquisar "site:x.com" pois esta bloqueado.
- Se Instagram: usa WebSearch para pesquisar "[nome da fonte] instagram" — se e conta oficial de media/jornalista com actividade recente, VALIDA

Para VALIDAR E ACTIVAR (IMPORTANTE: fazer os DOIS — validated E active E added_to_collector):
UPDATE discovered_sources
SET validated = true, active = true, added_to_collector = true, last_checked_at = now(),
    validation_result = jsonb_build_object('method', 'cowork_websearch', 'validated_at', now()::text, 'notes', '[notas da validacao]')
WHERE id = '[id]';

Para rejeitar (fonte morta/invalida/spam):
DELETE FROM discovered_sources WHERE id = '[id]';

PASSO 6B — Corrigir fontes validadas mas nao activadas:
UPDATE discovered_sources SET active = true, added_to_collector = true
WHERE validated = true AND (active = false OR added_to_collector = false);

PASSO 7 — Log:
Conta as operacoes e regista:

INSERT INTO pipeline_runs (stage, status, started_at, completed_at, events_in, events_out, metadata)
VALUES (
  'source_finder_cowork',
  'completed',
  '[hora_inicio]'::timestamptz,
  now(),
  0,
  [fontes_descobertas],
  jsonb_build_object(
    'function', 'source-finder-cowork',
    'source', 'cowork',
    'new_sources', [total_novas],
    'validated', [total_validadas],
    'rejected', [total_rejeitadas],
    'by_type', jsonb_build_object('rss', [N], 'telegram', [N], 'twitter', [N], 'instagram', [N]),
    'focus_areas', '[areas menos cobertas]'::jsonb
  )
);

Objetivo: 5-15 novas fontes por execucao diaria. Minimo 1 de cada tipo (RSS, Telegram, X, Instagram).

IMPORTANTE:
- O campo 'name' e obrigatorio (NOT NULL) — sempre incluir um nome descritivo
- O campo 'url' e UNIQUE — nao tentar inserir URLs duplicados
- Usar areas validas: geopolitica, defesa, economia, tecnologia, energia, saude, clima, crypto, regulacao, portugal, ciencia, financas, sociedade, desporto, politica_intl, diplomacia, defesa_estrategica, desinformacao, direitos_humanos, crime_organizado
- Focar em fontes de qualidade: jornais, agencias, analistas reconhecidos, instituicoes
- NAO inserir: blogs pessoais, contas de humor/entretenimento, bots, contas inativas
- Preencher SEMPRE o campo 'continent' (Europe, Africa, Asia, North America, South America, Oceania)
- source_type validos: rss, telegram, twitter, instagram, web
```

---

## Como criar no Cowork

1. Abrir Cowork
2. Criar nova scheduled task
3. Nome: `source-finder-cowork`
4. Frequencia: `daily at 06:00 UTC`
5. Colar o prompt acima
6. Confirmar que o Supabase MCP esta ligado ao Cowork
7. Testar manualmente uma vez antes de ativar o schedule
