# Prompt para LMNotebook — Lógica de Statement vs Factual na Pipeline

Cola este prompt no LMNotebook para obter uma análise sobre como o certainty score deve tratar claims do tipo "statement" vs "factual".

---

## Prompt

```
Tenho um sistema de jornalismo automatizado por IA chamado "Curador de Notícias". O pipeline faz fact-checking com o Grok (modelo reasoning + web_search + x_search) e classifica cada claim de um artigo como:

- "statement": Alguém disse/declarou/prometeu algo. Verificação = a pessoa disse mesmo isto? (1 fonte primária basta: tweet oficial, conferência de imprensa, vídeo)
- "factual": Algo aconteceu ou é verdade. Verificação = é factualmente correto? (precisa de 2+ fontes independentes)

O problema atual:

O certainty score é calculado assim:
  certainty_score = (overall_confidence × 0.6) + (auditor_score/10 × 0.4)

O overall_confidence é a média de TODAS as claims, sem distinguir statement de factual.

Exemplo real que expõe o problema:

Artigo: "Hegseth promete impedir bloqueio iraniano no Estreito de Ormuz"

Claims:
1. [statement] "Hegseth declarou que vai impedir o bloqueio" → verified, 0.98
2. [factual] "Preços do petróleo acima de $100/barril" → verified, 0.95
3. [factual] "EUA vão conseguir reabrir o Estreito" → insufficient_data, 0.30

O overall_confidence cai para ~0.74 por causa da claim 3 (previsão sobre o futuro).
O artigo vai para revisão humana em vez de ser publicado automaticamente.
Mas o artigo é factualmente sólido — a declaração foi feita, o contexto é real, só a previsão é incerta.

O que preciso que me ajudes a decidir:

1. CÁLCULO DO CERTAINTY SCORE
   - Devo separar o cálculo em dois scores? (statement_confidence + factual_confidence)
   - Devo excluir claims com "insufficient_data" do cálculo do overall_confidence?
   - Ou devo dar pesos diferentes? (ex: statements pesam 40%, factuals pesam 60%)
   - E se um artigo só tem statements e nenhum factual confirmado — deve ser publicado?

2. LÓGICA DE PUBLICAÇÃO
   - Cenário A: Artigo com 3 statements verified + 0 factuals → publicar ou não?
   - Cenário B: Artigo com 1 statement verified + 2 factuals refuted → publicar ou não?
   - Cenário C: Artigo com 2 statements verified + 1 factual insufficient_data → publicar ou não?
   - Cenário D: Artigo com 0 statements + 3 factuals verified → publicar (caso normal)
   - Cenário E: Breaking news — só 1 statement de fonte oficial, zero factuals → publicar com que label?

3. COMO MOSTRAR AO LEITOR
   - O artigo deve ter badges diferentes para "Declaração Verificada" vs "Facto Verificado"?
   - Claims com insufficient_data devem aparecer como "Ainda por confirmar" no artigo?
   - Devo ter um certainty score composto visível (ex: "Declaração: 98% | Contexto: 95% | Previsão: 30%")?

4. EDGE CASES PERIGOSOS
   - Político mente em conferência de imprensa → statement verified (ele disse), factual refuted (é mentira). Como apresentar?
   - Leak/rumor de fonte anónima → nem statement nem factual clássico. Nova categoria?
   - Declaração contraditória (Hegseth diz X hoje, disse Y ontem) → como classificar?
   - Artigo de opinião/análise vs artigo de notícia — a mesma lógica aplica-se?

5. IMPLEMENTAÇÃO TÉCNICA
   - Onde na pipeline devo separar a lógica? (no fact-check, no auditor, no writer, ou no cálculo final do certainty?)
   - Devo alterar a fórmula do certainty_score ou criar scores adicionais?
   - Como guardar isto na base de dados? (campos novos na tabela articles?)

6. O MEU CONTEXTO
   - Limiar de publicação automática: 90% certainty
   - O público quer notícias rápidas mas fiáveis
   - Prefiro publicar com transparência ("declaração verificada, conteúdo por confirmar") do que atrasar
   - O sistema já funciona a 97-98% para artigos com claims factuais verificáveis
   - O writer escreve em PT-PT com tom jornalístico sóbrio (pirâmide invertida)

Dá-me:
A) Uma proposta de nova fórmula de certainty_score que trate statements e factuals de forma diferente
B) Uma tabela de decisão para os cenários A-E acima
C) Um mockup de como o leitor veria a verificação no artigo (texto, não design)
D) Red flags — situações onde esta lógica pode falhar perigosamente
```

---

## Notas de uso

- Este prompt complementa o PROMPT-BIAS-LMNOTEBOOK.md (viés) — são problemas diferentes
- A resposta deste prompt deve informar mudanças no grok-fact-check v8 e no writer-publisher
- Testa com vários LLMs para comparar abordagens (Claude, GPT-4, Grok, Gemini)
