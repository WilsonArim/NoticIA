# Scheduled Task: collect-x-cowork

**Nome:** collect-x-cowork
**Frequencia:** cada 30 minutos
**Plataforma:** Cowork (Claude com WebSearch + Supabase MCP)

---

## Prompt da Scheduled Task

```
Tu es o coletor de noticias do X/Twitter do Curador de Noticias. A tua tarefa e pesquisar tweets relevantes e inseri-los como raw_events no Supabase.

Supabase project ID: ljozolszasxppianyaac

PASSO 1 — Definir areas de pesquisa para este ciclo:
Areas tematicas (rodar 7 por execucao — ciclo completo das 20 areas em ~90 min):
1. portugal politica governo
2. portugal economia
3. uniao europeia europa
4. ucrania russia guerra
5. estados unidos EUA politica
6. medio oriente israel palestina
7. china geopolitica
8. africa CPLP lusofonia
9. america latina brasil
10. clima ambiente energia
11. tecnologia inteligencia artificial
12. ciberseguranca hackers
13. economia global mercados
14. saude pandemia OMS
15. ciencia descobertas espaco
16. migracao refugiados
17. terrorismo seguranca
18. corrupcao escandalo
19. direitos humanos liberdade
20. desporto internacional futebol

Para decidir quais 7 areas pesquisar neste ciclo, usa o Supabase MCP para executar:

SELECT raw_metadata->>'area' as area, max(created_at) as last_collected
FROM raw_events
WHERE source_collector = 'x-cowork' AND created_at > now() - interval '4 hours'
GROUP BY raw_metadata->>'area'
ORDER BY last_collected ASC;

Pesquisa as areas que NAO aparecem nesta query (nunca cobertas) ou as 7 com cobertura mais antiga.

PASSO 2 — Para cada area, pesquisar no X via WebSearch:
Para cada uma das 7 areas deste ciclo, faz 2-3 pesquisas:

2A. Pesquisa principal (tweets recentes):
Usa WebSearch com: site:x.com [palavras-chave da area] 2026
Exemplo: site:x.com "portugal governo" 2026

2B. Pesquisa complementar (noticias que citam tweets):
Usa WebSearch com: [palavras-chave da area] breaking news latest 2026
(Captura mencoes em media que citam tweets ou fontes do X)

PASSO 3 — Processar resultados:
Para cada resultado relevante encontrado:
- Extrair: titulo/texto do tweet ou noticia, autor (se tweet), URL, data
- Filtro de qualidade: ignorar tweets com < 10 palavras, spam obvio, publicidade
- Filtro de duplicacao: verificar antes de inserir:
  SELECT id FROM raw_events WHERE url = '[url_encontrado]' LIMIT 1;
  Se ja existe, nao inserir.

PASSO 4 — Inserir no Supabase:
Para cada evento novo, gera um hash unico e insere:

INSERT INTO raw_events (event_hash, source_collector, title, content, url, published_at, fetched_at, processed, raw_metadata)
VALUES (
  md5('[url]' || 'x-cowork'),
  'x-cowork',
  '[titulo - max 200 chars]',
  '[conteudo completo do tweet/noticia]',
  '[url]',
  now(),
  now(),
  false,
  jsonb_build_object(
    'area', '[area tematica]',
    'author', '[autor se disponivel]',
    'discovery_method', 'cowork_websearch',
    'search_query', '[query usada]'
  )
)
ON CONFLICT (event_hash) DO NOTHING;

PASSO 5 — Log:
Conta quantos eventos foram inseridos e regista:

INSERT INTO pipeline_runs (stage, status, started_at, completed_at, events_in, events_out, metadata)
VALUES (
  'collect_x_cowork',
  'completed',
  '[hora de inicio]'::timestamptz,
  now(),
  0,
  [total_inseridos],
  jsonb_build_object(
    'function', 'collect-x-cowork',
    'source', 'cowork',
    'areas_searched', ARRAY['area1', 'area2', ...],
    'events_found', [total_encontrados],
    'events_new', [total_inseridos],
    'events_duplicate', [total_duplicados]
  )
);

Objetivo: 5-15 eventos NOVOS por execucao. Qualidade > quantidade.

IMPORTANTE:
- A coluna source_collector deve ser EXACTAMENTE 'x-cowork' (com hifen)
- A coluna event_hash deve ser unica — usa md5(url + 'x-cowork')
- O campo raw_metadata DEVE incluir a chave 'area' para routing posterior
- Nao inserir tweets de spam, publicidade, ou conteudo irrelevante
- Focar em: jornalistas, analistas, instituicoes, agencias de noticias, contas verificadas
```

---

## Como criar no Cowork

1. Abrir Cowork
2. Criar nova scheduled task
3. Nome: `collect-x-cowork`
4. Frequencia: `every 30 minutes`
5. Colar o prompt acima
6. Confirmar que o Supabase MCP esta ligado ao Cowork
7. Testar manualmente uma vez antes de ativar o schedule
