---
name: project-workflow
description: Protocolo mestre para iniciar, adotar, desenvolver, revisar e encerrar trabalho em projetos mantendo autonomia de modelo/harness, contexto seletivo, documentação incremental, validação determinística e telemetria de uso.
---

# Project Workflow — Master Skill

## Norte

Otimize simultaneamente para:

1. **Autonomia** — o conhecimento essencial pertence ao repositório, não ao harness ou modelo.
2. **Controle** — contexto, mudanças, permissões, validação e incertezas devem ser explícitos.
3. **Gestão** — estado, decisões e custo devem ser recuperáveis sem vasculhar chats.
4. **Simplicidade** — processo é proporcional ao risco/complexidade; não crie burocracia sem necessidade.

Esta estrutura orienta o trabalho, mas **não limita liberdade técnica**. Use a solução tecnicamente adequada; registre decisões duráveis quando necessário.

## Regra fundamental de memória

Classifique informação antes de persistir:

- **durável:** arquitetura, contratos, invariantes, decisão com trade-offs → `PROJECT.md`, `docs/architecture/` ou ADR;
- **operacional:** foco, blocker, próximo passo → `.project/state.md`;
- **mudança complexa:** intenção/critérios/escopo → `docs/specs/`;
- **transitória:** tentativa, log, exploração, raciocínio, conversa → não promover automaticamente à memória.

Nunca transforme conversa inteira em memória do projeto.

## Context budget / progressive disclosure

Comece pequeno:

1. `AGENTS.md`;
2. `PROJECT.md`;
3. `.project/state.md` somente se o estado corrente for relevante;
4. código e testes ligados à tarefa;
5. docs/ADRs/specs apenas quando houver razão concreta.

Não leia todos os ADRs, specs, documentos ou histórico por padrão. Descubra primeiro; recupere depois.

## Modo A — projeto novo

Quando o repositório ainda é um template:

1. entender objetivo e usuário do projeto;
2. preencher `PROJECT.md` somente com fatos conhecidos;
3. configurar `.project/config.json` com os comandos reais assim que existirem;
4. manter arquitetura mínima; não antecipar sistemas ainda inexistentes;
5. iniciar `.project/state.md` com foco e próximo passo;
6. criar ADR apenas se já existir uma decisão estrutural significativa;
7. criar spec apenas se a primeira mudança justificar.

## Modo B — adoção de projeto existente

Objetivo: reconstruir o **estado atual confiável** sem reescrever o produto nem inventar sua história.

### Ordem de evidência

1. código e configuração atuais;
2. testes e CI;
3. Git (commits/tags/releases);
4. documentação existente;
5. issues/PRs;
6. chats/históricos de IA apenas para preencher lacunas.

### Procedimento

1. inventariar stack, componentes, entrypoints, persistência, integrações e deploy;
2. identificar comandos reais de build/test/lint/typecheck;
3. reconstruir arquitetura atual a partir de evidência;
4. identificar marcos relevantes no Git sem criar cronologia excessiva;
5. separar fatos verificáveis de inferências;
6. preencher `PROJECT.md`, `.project/config.json`, `.project/state.md` e `docs/architecture/overview.md`;
7. criar ADR retroativo somente quando a decisão e seu motivo forem suficientemente evidentes; caso contrário, listar lacuna para confirmação;
8. não alterar código funcional durante a adoção, salvo pedido explícito;
9. apresentar ao usuário apenas lacunas relevantes que não puderam ser resolvidas por evidência.

### Confiança

Ao reconstruir informação histórica, marque mentalmente:

- **alta:** comprovada diretamente por código/testes/config/Git;
- **média:** fortemente sustentada por múltiplas evidências;
- **baixa:** hipótese — não persistir como fato sem confirmação.

## Modo C — executar tarefa

### Classifique a tarefa

**Pequena/localizada**
- implemente diretamente;
- execute validação relevante;
- normalmente não crie spec/ADR.

**Bug**
- reproduza ou encontre evidência antes de editar quando possível;
- identifique causa, não apenas sintoma;
- acrescente/ajuste teste quando isso aumenta proteção contra regressão;
- documente somente se o bug revelou conhecimento durável.

**Feature normal**
- explicite objetivo e critérios mínimos;
- use plano leve se necessário;
- spec é opcional.

**Feature complexa / longa / multiagente**
- crie/atualize spec;
- registre critérios de aceitação;
- decomponha trabalho apenas até o nível útil para execução/handoff.

**Mudança arquitetural**
- consulte arquitetura/ADRs relevantes;
- compare alternativas quando houver trade-offs reais;
- crie ADR quando a decisão for significativa e durável.

## Documentação incremental

Antes de alterar documentação, pergunte:

> A mudança alterou conhecimento que um agente futuro precisará para trabalhar corretamente?

Se **não**, não atualize documentos por ritual.

Se **sim**, atualize somente o dono canônico:

- visão/propósito/stack estável → `PROJECT.md`;
- arquitetura atual → `docs/architecture/`;
- decisão e justificativa → `docs/adr/`;
- intenção/aceitação de mudança complexa → `docs/specs/`;
- foco/blocker/próximo passo → `.project/state.md`.

Não mantenha changelog manual nesses arquivos. O Git registra a evolução.

## Validação

Antes de declarar conclusão de mudança substantiva:

1. revisar diff;
2. executar `python scripts/verify.py`;
3. interpretar FAIL como FAIL — não relativizar;
4. se um gate necessário não existe, registrar como lacuna, não como PASS;
5. confirmar que mudança não violou invariantes conhecidos.

A IA escolhe como resolver. Gates determinísticos avaliam o que for automatizável.

## Revisão independente

Para mudanças de risco médio/alto, prefira uma segunda perspectiva antes de encerrar:

- outro agente/subagente/harness quando disponível; ou
- uma segunda passada independente, reabrindo objetivo, diff, testes, edge cases e impacto arquitetural sem assumir que a primeira solução está correta.

A revisão deve procurar falhas, não apenas confirmar a implementação.

## Telemetria de tokens e custo

Telemetria é gestão, não conteúdo de prompt.

- não guardar prompts/respostas por padrão;
- importar métricas do harness quando disponíveis;
- registrar harness, provider, modelo, tokens e custo;
- distinguir `actual_cost_usd` de `api_equivalent_cost_usd`;
- uso via assinatura pode ter tokens observáveis sem custo real atribuível por chamada;
- nunca inventar custo ausente;
- marcar estimativas explicitamente.

Após sessões relevantes, use adaptador do harness quando disponível e gere:

```bash
python scripts/usage.py report
```

O relatório canônico é `.project/usage/USAGE.md`.

## Ferramentas opcionais

Beads, Spec Kit, Serena, Ruler, MCPs, worktrees e sistemas multiagente são opcionais.

Antes de adicionar qualquer um, responda:

1. qual problema recorrente resolve?
2. por que a solução atual não basta?
3. qual custo de contexto/operação adiciona?
4. se removermos amanhã, o conhecimento essencial continua no repositório?

## Encerramento da tarefa

Entregue uma síntese curta contendo:

- o que mudou;
- validações executadas e seus resultados;
- documentação atualizada (se houve motivo);
- incertezas/riscos remanescentes;
- próximo passo somente se houver um realmente necessário.

Atualize `.project/state.md` apenas quando o estado corrente realmente mudou.
