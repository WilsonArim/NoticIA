# /debug — Debug Sistematico

> Workflow para resolver problemas de forma metodica e eficiente.

## Skills Encadeadas

1. **systematic-debugging** — Metodologia de debug
2. **lint-and-validate** — Verificar erros de sintaxe e tipo
3. **test-driven-development** — Escrever teste que reproduz o bug

## Sequencia

### Passo 1: Reproduzir (systematic-debugging)
- Obter descricao clara do problema
- Reproduzir o erro de forma consistente
- Isolar o contexto (quando acontece, quando nao acontece)

### Passo 2: Validar Basicos (lint-and-validate)
- Correr linter e type checker
- Verificar erros de compilacao
- Verificar dependencias e imports

### Passo 3: Hipotese (systematic-debugging)
- Formular hipotese sobre a causa
- Identificar o caminho do codigo afetado
- Usar binary search se necessario

### Passo 4: Testar (test-driven-development)
- Escrever teste que falha (reproduz o bug)
- Confirmar que o teste captura o problema
- Este teste servira de validacao do fix

### Passo 5: Corrigir (systematic-debugging)
- Implementar o fix minimo necessario
- Verificar que o teste agora passa
- Verificar que nenhum teste existente partiu

### Passo 6: Prevenir
- Considerar se o bug pode ocorrer noutros locais
- Adicionar validacao se necessario
- Documentar se for um pattern recorrente

## Output Esperado

```
1. Descricao do problema e como reproduzir
2. Causa raiz identificada
3. Teste que captura o bug
4. Fix implementado
5. Confirmacao de que tudo passa
```

## Quando Usar

- "Tenho um bug em..."
- "Isto nao esta a funcionar..."
- "Erro: [mensagem de erro]"
- "Porque e que X faz Y?"
