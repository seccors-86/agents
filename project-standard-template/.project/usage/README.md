# AI Usage / Cost

Este diretório é o ponto único para gestão de consumo de IA **deste projeto**.

## Objetivo

Responder sem vasculhar chats:

- quantos tokens o projeto consumiu;
- quais harnesses/modelos consumiram;
- qual custo foi reportado;
- qual custo foi realmente cobrado quando isso é atribuível;
- qual seria o equivalente de API quando o uso veio de assinatura.

## Privacidade

Por padrão, a telemetria **não armazena prompts nem respostas**. Apenas métricas e identificadores operacionais.

## Estrutura gerada

```text
.project/usage/
├── README.md
├── USAGE.md                 relatório consolidado
├── snapshots/               estado cumulativo por harness
│   └── opencode.json
└── events/                  eventos de harnesses sem snapshot cumulativo
    └── <event-id>.json
```

`events/` e `snapshots/` são criados automaticamente quando necessários.

## OpenCode

O OpenCode fornece estatísticas por projeto. Na raiz do projeto:

```bash
python scripts/usage.py import-opencode --billing-mode subscription
python scripts/usage.py report
```

Use:

- `--billing-mode api` quando aquele consumo foi realmente metered/cobrado como API;
- `--billing-mode subscription` quando veio de plano/assinatura;
- `--billing-mode unknown` se não houver certeza.

No modo assinatura, o custo reportado pelo harness pode ser usado como **equivalente econômico**, mas não é registrado como cobrança real do projeto.

## Claude Code

Para uma execução programática salva em JSON:

```bash
claude -p "..." --output-format json > .project/usage/claude-result.json
python scripts/usage.py import-claude-json .project/usage/claude-result.json --billing-mode api
python scripts/usage.py report
```

O import usa hash do arquivo como ID, portanto importar o mesmo resultado novamente não duplica a sessão.

## Codex e outros harnesses

Enquanto não houver adaptador específico no template, normalize um evento:

```bash
python scripts/usage.py add \
  --harness codex \
  --provider openai \
  --model <modelo> \
  --billing-mode subscription \
  --input 100000 \
  --output 12000 \
  --cache-read 80000 \
  --api-equivalent-cost 1.23
```

Quando um harness expuser telemetria estável (JSON, OpenTelemetry ou API local), prefira criar um adaptador que alimente o mesmo schema em vez de mudar o relatório.

## Regras de interpretação

- `reported_cost_usd`: custo informado/calculado pelo harness;
- `actual_cost_usd`: cobrança realmente atribuível àquele uso;
- `api_equivalent_cost_usd`: equivalência econômica de API, útil para comparar assinatura vs API;
- `estimated: true`: valor estimado, nunca apresentado como medição exata.

Não force um rateio fictício de assinaturas mensais por projeto. Se o fornecedor não atribui custo real por chamada, mantenha `actual_cost_usd` vazio e use equivalente de API quando houver base confiável.
