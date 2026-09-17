# Arquitetura — visão atual

> Descreva a arquitetura **como ela existe hoje**. Evite histórico e detalhes que o código já torna óbvios.

## Visão de alto nível

```text
<diagrama textual simples dos componentes e fluxos principais>
```

## Componentes

| Componente | Responsabilidade | Dependências principais |
|---|---|---|
| `<nome>` | `<responsabilidade>` | `<dependências>` |

## Fluxos críticos

### <fluxo>

1. <passo>
2. <passo>

## Dados e persistência

<fontes de verdade, bancos, filas, caches e ownership de dados>

## Fronteiras e contratos

<APIs, eventos, interfaces internas importantes e invariantes>

## Segurança / isolamento

<somente o que é estrutural e necessário para futuras mudanças>

## Observabilidade

<logs, métricas, tracing, alertas relevantes>

## Decisões relacionadas

Consulte `docs/adr/` para decisões e trade-offs. Não replique justificativas completas aqui.
