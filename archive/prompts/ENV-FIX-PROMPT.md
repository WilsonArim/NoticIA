# PROMPT — Mover search API keys para pipeline/.env

## PROBLEMA

As 3 keys de pesquisa foram colocadas no `.env.local` da raiz (ficheiro do Next.js frontend).
O pipeline Python (`scheduler_ollama.py`) faz `load_dotenv()` que lê apenas `pipeline/.env`.
As keys **não são lidas** pelo pipeline enquanto estiverem só no `.env.local`.

## TAREFA

1. Lê o ficheiro `.env.local` na raiz do projecto
2. Encontra as 3 linhas:
   - `TAVILY_API_KEY=...`
   - `EXA_API_KEY=...`
   - `SERPER_API_KEY=...`
3. Adiciona essas 3 linhas ao `pipeline/.env` (no final do ficheiro, junto às outras variáveis de configuração do pipeline)
4. **NÃO** remove as linhas do `.env.local` — o frontend Next.js pode precisar delas no futuro

## VERIFICAÇÃO

Depois de editar, confirma:
```bash
grep -E "TAVILY|EXA|SERPER" pipeline/.env
```
As 3 keys devem aparecer com os valores preenchidos (não vazias).

## COMMIT

```bash
git add pipeline/.env.example
git commit -m "fix: add search API keys to pipeline/.env

Tavily, Exa.ai and Serper.dev keys were only in root .env.local (Next.js).
Python pipeline uses load_dotenv() which reads pipeline/.env only.
Keys now in both files so both frontend and pipeline can use them."
git push
```

**Nota:** Não incluas os valores das keys no `.env.example` — só os nomes das variáveis vazias.
