# Architecture Decision Records (ADRs)

Use ADR somente para decisões **arquiteturais significativas** que um agente futuro pode precisar entender para evitar reabrir uma decisão sem contexto.

## Crie um ADR quando

- houver alternativas reais e trade-offs relevantes;
- a decisão alterar uma fronteira, contrato, persistência, segurança, infraestrutura ou dependência estrutural;
- reverter a decisão posteriormente tiver custo relevante;
- o motivo não puder ser deduzido com segurança apenas olhando o código.

## Não crie ADR para

- correções pequenas;
- refactors sem mudança de arquitetura;
- escolha trivial/reversível de implementação;
- registrar cada pacote instalado;
- manter changelog.

## Status

`proposed | accepted | superseded | deprecated`

Se uma decisão mudar, prefira um novo ADR que referencia o antigo em vez de apagar a história.

Use `0000-template.md` como modelo.
