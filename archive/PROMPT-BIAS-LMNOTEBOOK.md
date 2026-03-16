# Prompt para LMNotebook — Estratégia de Viés no Curador de Notícias

Cola este prompt no LMNotebook para obter uma análise aprofundada sobre como tratar viés no projeto.

---

## Prompt

```
Sou o criador do "Curador de Notícias", um sistema de jornalismo automatizado por IA que recolhe notícias de múltiplas fontes, faz fact-checking com o Grok (modelo reasoning + web_search + x_search), e publica artigos em português de Portugal.

O meu pipeline de fontes é:
- 22 RSS feeds (BBC, NYT, Al Jazeera, Reuters, Guardian, Público, Observador, etc.)
- GDELT v2 (eventos globais, API pública)
- ACLED (conflitos armados, dados académicos)
- Telegram (8 canais: @rybar pro-Russia, @ukraine_now pro-Ucrânia, @bbcnews, @bloombergfeeds, etc.)
- X/Twitter (verificação de claims)
- Crawl4AI (enriquecimento de URLs)

O meu fact-check tem um módulo de bias_analysis que atualmente é apenas um prompt genérico que pede ao Grok para "avaliar viés de 0 a 1". Reconheço que isto é insuficiente.

Preciso da tua ajuda para desenhar uma estratégia completa de tratamento de viés. Considera:

1. FONTES DE ENTRADA
   - Como classificar e pontuar o viés de cada fonte? (ex: AllSides rating, Media Bias/Fact Check)
   - Devo criar uma base de dados interna com score de viés por fonte?
   - Como lidar com fontes que são assumidamente enviesadas mas valiosas (ex: @rybar para perspectiva russa, Al Jazeera para perspectiva árabe)?
   - Devo manter fontes enviesadas para ter diversidade de perspectivas, ou removê-las?

2. DETECÇÃO DE VIÉS NO ARTIGO
   - Que técnicas de NLP posso usar para detetar viés automaticamente? (sentiment analysis, loaded language detection, framing analysis)
   - Como distinguir entre viés legítimo (opinião editorial) e viés manipulativo (propaganda, desinformação)?
   - O Grok (ou outro LLM) consegue detetar viés de forma fiável, ou tem os seus próprios vieses que contaminam a análise?

3. TRANSPARÊNCIA PARA O LEITOR
   - Como mostrar o viés ao leitor de forma honesta sem ser paternalista?
   - Devo ter um "espectro de viés" visível em cada artigo?
   - Como apresentar múltiplas perspectivas no mesmo artigo sem false balance (dar peso igual a factos e negacionismo)?

4. PROBLEMAS ÉTICOS
   - Como evitar que o sistema amplifique propaganda de estados (Rússia, China, EUA, Israel)?
   - Como tratar temas onde "ambos os lados" não são equivalentes (ex: alterações climáticas, genocídio)?
   - O sistema deve ter uma posição editorial (ex: "baseado em evidência científica") ou ser puramente neutro?
   - Como lidar com o viés inerente do próprio LLM que faz o fact-checking?

5. IMPLEMENTAÇÃO TÉCNICA
   - Que base de dados de viés de media posso usar? (AllSides, MBFC, Ad Fontes)
   - Como implementar um score de viés composto que considere: fonte, linguagem, enquadramento, omissões?
   - Como fazer A/B testing para medir se a detecção de viés está a funcionar?

6. O MEU CONTEXTO ESPECÍFICO
   - O público-alvo são portugueses interessados em geopolítica, defesa, economia e energia
   - As áreas mais sensíveis ao viés são: conflito Israel-Palestina, guerra Rússia-Ucrânia, política EUA, China-Taiwan
   - Quero ser rigoroso mas não censurar — o leitor deve ver todas as perspectivas com contexto
   - O sistema já classifica claims como "statement" (alguém disse X) vs "factual" (X é verdade) — isto ajuda a separar declarações de factos

Dá-me:
A) Uma estratégia completa em 3 fases (MVP, v2, v3)
B) Uma proposta de "media bias database" com as fontes que já uso
C) Um exemplo concreto de como o artigo do Hegseth/Ormuz seria tratado com esta estratégia
D) Red flags — coisas que devo NUNCA fazer no tratamento de viés
```

---

## Notas de uso

- Este prompt é longo de propósito — dá ao LLM todo o contexto necessário para uma resposta útil
- Funciona bem com Claude, GPT-4, Grok ou Gemini
- Guarda a resposta e usa-a como base para implementação futura
- Atualiza o prompt se mudares fontes ou a arquitetura do pipeline
