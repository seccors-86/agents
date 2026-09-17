# AGENTS.md

Este arquivo é o **mapa curto** para qualquer coding agent que entrar no repositório. Não é a documentação completa.

## Objetivo operacional

Trabalhe preservando quatro propriedades:

- **Autonomia:** não criar dependência desnecessária de um modelo, harness ou editor.
- **Controle:** tornar explícitos contexto, mudanças e validação.
- **Gestão:** manter estado e decisões recuperáveis sem depender do histórico de chats.
- **Simplicidade:** usar a menor quantidade de processo suficiente para a tarefa.

## Ao iniciar uma tarefa

1. Leia `PROJECT.md`.
2. Leia `.project/state.md` se a tarefa depender do estado corrente.
3. Carregue a skill `.agents/skills/project-workflow/SKILL.md` para trabalho substantivo.
4. Descubra primeiro; carregue documentação adicional somente quando relevante.
5. Nunca leia todos os ADRs/specs por padrão.

## Fonte de verdade por tipo de informação

- comportamento real: código + testes;
- identidade e visão estável: `PROJECT.md`;
- arquitetura atual: `docs/architecture/`;
- decisões com trade-offs: `docs/adr/`;
- especificações de mudanças complexas: `docs/specs/`;
- foco e blockers atuais: `.project/state.md`;
- uso/custo de IA: `.project/usage/`;
- histórico: Git.

Não duplique a mesma verdade em vários lugares.

## Liberdade técnica

As estruturas deste template são defaults, não limites. Banco de dados, serviços, MCPs, filas, novos frameworks e outras tecnologias podem ser usados quando forem a solução adequada. Quando uma decisão alterar a arquitetura de forma significativa, registre o motivo no local apropriado.

## Documentação incremental

Antes de concluir, pergunte:

> Esta mudança alterou conhecimento que um agente futuro precisará saber?

Se não, não crie documentação apenas por ritual.

Se sim, atualize somente o artefato dono daquela informação.

## Validação

Para mudanças substantivas, execute:

```bash
python scripts/verify.py
```

Se algum gate não for aplicável ou estiver ausente, informe isso; não transforme ausência de validação em PASS.

## Telemetria

Quando o harness fornecer métricas de uso, atualize o snapshot/ledger pelo adaptador disponível e gere o relatório:

```bash
python scripts/usage.py report
```

Nunca invente tokens ou custos. Diferencie cobrança real, custo equivalente de API e estimativas.

## Segurança e segredos

- nunca grave chaves, tokens ou credenciais no Git;
- use `.env.example` apenas para nomes e exemplos não secretos;
- não inclua prompts/conversas completos na telemetria por padrão;
- ações destrutivas ou de produção exigem intenção explícita do usuário.

## Encerramento

Antes de declarar uma tarefa concluída:

1. revise o diff;
2. execute os gates relevantes;
3. atualize documentos apenas se o conhecimento durável mudou;
4. atualize `.project/state.md` apenas se foco, blocker ou próximo passo mudou;
5. registre decisão arquitetural relevante, se houver;
6. apresente o que mudou, o que foi validado e qualquer incerteza remanescente.
