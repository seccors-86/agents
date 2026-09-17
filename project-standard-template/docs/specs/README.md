# Specs

Specs são usadas **sob demanda**, não como ritual obrigatório.

## Quando criar uma spec

Crie uma spec quando a mudança tiver complexidade suficiente para que intenção, escopo e critérios de aceitação possam se perder durante a implementação. Exemplos:

- feature com múltiplos componentes;
- mudança com vários contratos envolvidos;
- trabalho que provavelmente atravessará várias sessões/agentes;
- requisito com comportamento ambíguo;
- mudança que precisa de critérios de aceitação claros antes de codificar.

## Quando NÃO criar

- typo/CSS pequeno;
- bug localizado com causa clara;
- refactor simples;
- manutenção rotineira.

## Estrutura sugerida

Cada spec pode viver em uma pasta própria:

```text
docs/specs/<id>-<slug>/
├── spec.md
├── plan.md      # somente se necessário
└── tasks.md     # somente se necessário
```

### `spec.md`

- problema/intenção;
- comportamento desejado;
- fora de escopo;
- critérios de aceitação;
- restrições conhecidas.

### `plan.md`

Use apenas quando houver valor em registrar abordagem, componentes afetados ou sequência de migração.

### `tasks.md`

Use apenas quando o trabalho precisar ser decomposto para execução/handoff.

A spec descreve a mudança. A arquitetura atual continua em `docs/architecture/`, e decisões permanentes com trade-offs ficam em ADRs.
