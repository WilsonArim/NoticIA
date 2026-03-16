# Método de Fact-Checking — Curador de Notícias

## Visão Geral

O Curador de Notícias utiliza um pipeline multi-agente de verificação de factos, composto por 6 módulos especializados que analisam cada artigo antes da publicação. Apenas artigos com **certainty score ≥ 90%** são publicados automaticamente; os restantes ficam numa fila de revisão humana.

---

## Arquitetura do Pipeline

```
Fontes (RSS, X, GDELT, Telegram, Crawl4AI)
    ↓
[collect-*] Coletores — recolha de notícias brutas
    ↓
[reporter-filter] Filtro — deduplicação e relevância
    ↓
[curator-central] Curador — triagem por área e prioridade
    ↓
[grok-reporter] Repórter — extração de claims e factos-chave
    ↓
[grok-fact-check] ◀── FACT-CHECKING (este documento)
    ↓
[writer-publisher] Redação + Publicação
    ↓
Artigo publicado (≥90%) ou fila de revisão (<90%)
```

---

## Modelo e Ferramentas

| Parâmetro | Valor |
|-----------|-------|
| **Modelo** | `grok-4-1-fast-reasoning` (modelo com raciocínio) |
| **Endpoint** | `https://api.x.ai/v1/responses` |
| **Ferramentas** | `web_search` + `x_search` (pesquisa web e X em tempo real) |
| **Temperature** | `0.0` (máxima precisão, zero criatividade) |
| **Max tokens** | `8192` |

### Porque `/v1/responses` e não `/v1/chat/completions`?

O endpoint `/v1/chat/completions` (antigo) apenas suporta `type: "function"` e `live_search`. As ferramentas nativas de pesquisa (`web_search`, `x_search`) só estão disponíveis no endpoint `/v1/responses`, que utiliza o formato `input` em vez de `messages`.

---

## Os 6 Módulos de Verificação

Cada artigo é analisado simultaneamente por 6 módulos especializados numa única chamada ao Grok:

### 1. Verificação de Fontes (`source_verification`)
- A fonte citada existe e é acessível?
- É credível (agência de notícias, instituição académica, governo)?
- A fonte diz realmente o que o artigo afirma?

### 2. Referência Cruzada de Claims (`claim_crossref`)
- Existem fontes independentes que confirmam ou negam cada claim?
- Múltiplas fontes credíveis reportam os mesmos factos?
- Existem contradições entre fontes?

### 3. Consistência Temporal (`temporal_consistency`)
- Datas e cronologias são internamente consistentes?
- A sequência de eventos faz sentido lógico?
- Existem afirmações temporais impossíveis ou anacrónicas?

### 4. Deteção de IA (`ai_detection`)
- O texto apresenta padrões típicos de conteúdo gerado por IA?
- Faltam detalhes específicos que um jornalista humano incluiria?
- O tom é uniformemente consistente de forma não-humana?

### 5. Análise de Enviesamento (`bias_analysis`)
- Existe enviesamento de enquadramento (framing)?
- Perspetivas importantes estão omitidas?
- Linguagem carregada ou manipulação emocional?
- Diversidade de fontes (unilateral vs equilibrado)?

### 6. Auditoria Lógica (`logic_audit`)
- Falácias lógicas (ad hominem, falsa dicotomia, etc.)?
- Non-sequiturs (conclusões que não seguem das premissas)?
- Afirmações causais têm evidência de suporte?
- Generalizações não fundamentadas?

---

## Prompt Anti-Alucinação

O sistema inclui um prompt rigoroso para evitar que o modelo rejeite notícias atuais como "futuras":

```
Current real date: [data atual].
Knowledge cutoff: November 2024.

REGRAS OBRIGATÓRIAS:
1. Para QUALQUER claim sobre eventos de 2025-2026, DEVE pesquisar com
   web_search E x_search antes de concluir.
2. Só concluir após encontrar pelo menos 2 fontes primárias independentes.
3. Qualquer fonte datada de 2025 ou 2026 é válida e real.
4. Contexto político: Trump é Presidente dos EUA desde 20 Jan 2025.
   Pete Hegseth é Secretário da Defesa.
5. Se as ferramentas não retornarem resultados, o veredito deve ser
   "insufficient_data" (nunca "refuted" sem evidência).
```

---

## Output do Fact-Check

Para cada artigo, o sistema produz:

```json
{
  "claims": [
    {
      "claim_text": "texto da afirmação",
      "verdict": "verified | partially_verified | unverified | refuted | insufficient_data",
      "confidence": 0.0-1.0,
      "sources_found": [
        { "url": "...", "title": "...", "reliability": "high | medium | low" }
      ],
      "reasoning": "explicação detalhada"
    }
  ],
  "overall_confidence": 0.0-1.0,
  "ai_probability": 0.0-1.0,
  "bias_score": 0.0-1.0,
  "logic_score": 0.0-1.0,
  "summary": "resumo da verificação"
}
```

---

## Cálculo do Certainty Score

O **certainty score** final de cada artigo é calculado pela fórmula:

```
certainty_score = (fact_check_confidence × 0.6) + (auditor_score/10 × 0.4)
```

| Componente | Peso | Fonte |
|-----------|------|-------|
| `fact_check_confidence` | 60% | Score overall do fact-check (0.0-1.0) |
| `auditor_score` | 40% | Score do auditor editorial (0-10, normalizado para 0-1) |

### Limiares de Publicação

| Certainty Score | Ação |
|----------------|------|
| ≥ 90% | **Publicação automática** |
| < 90% | Fila de revisão humana |

---

## Custos

| Modelo | Input | Output |
|--------|-------|--------|
| `grok-4-1-fast-reasoning` (fact-check) | $5.00/M tokens | $15.00/M tokens |
| `grok-4-1-fast-non-reasoning` (redação) | $0.20/M tokens | $0.50/M tokens |

O fact-checking com ferramentas de pesquisa custa significativamente mais que a redação, mas garante verificação factual em tempo real com fontes primárias.

---

## Fluxo de Dados

```
intake_queue (status: pending, fact_check_summary: null)
    ↓ grok-fact-check
intake_queue (status: pending, fact_check_summary: {...})
    ↓ auditor (score + aprovação)
intake_queue (status: auditor_approved)
    ↓ writer-publisher
articles (status: published | review)
```

---

## Histórico de Versões

| Versão | Data | Mudanças |
|--------|------|----------|
| v1-v4 | Mar 2026 | `grok-4-1-fast-non-reasoning`, sem tools, endpoint `/v1/chat/completions` |
| v5 | 13 Mar 2026 | Migração para reasoning model + tools (falhou: endpoint errado) |
| **v6** | **13 Mar 2026** | **Endpoint `/v1/responses` + `web_search` + `x_search` — funcional** |
