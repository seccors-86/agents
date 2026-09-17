# PROJECT.md

> Mantenha este documento curto e atual. Ele descreve **o que o projeto é hoje**, não toda a sua história.

## Nome

`<nome-do-projeto>`

## Propósito

<Qual problema este projeto resolve e para quem?>

## Resultado esperado

<Como sabemos que o projeto está cumprindo seu objetivo?>

## Estado atual

- estágio: `discovery | development | production | maintenance`
- versão/release atual: `<se aplicável>`
- foco corrente: consulte `.project/state.md`

## Stack atual

- linguagem/runtime: `<preencher>`
- frontend: `<se houver>`
- backend: `<se houver>`
- banco/armazenamento: `<se houver>`
- infraestrutura/deploy: `<se houver>`

## Componentes principais

- `<componente>` — `<responsabilidade>`

## Interfaces/contratos importantes

- `<API/evento/arquivo/integração que agentes futuros precisam preservar>`

## Como executar

```bash
# comandos reais do projeto
```

## Como validar

A fonte executável é `.project/config.json`.

```bash
python scripts/doctor.py
python scripts/verify.py
```

## Restrições/invariantes

- `<regra que não pode ser quebrada sem decisão explícita>`

## Onde encontrar mais informação

- arquitetura: `docs/architecture/`
- decisões: `docs/adr/`
- specs de mudanças complexas: `docs/specs/`
- estado atual: `.project/state.md`
- telemetria de IA: `.project/usage/`
