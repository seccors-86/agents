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

Por padrão, a telemetria **não armazena prompts nem respostas**. Apenas métricas e identificadores operacionais. Os adaptadores podem ler arquivos locais do harness para extrair métricas, mas não copiam o conteúdo das conversas para o repositório.

## Estrutura gerada

```text
.project/usage/
├── README.md
├── USAGE.md                 relatório consolidado
├── snapshots/               estado cumulativo por harness
│   ├── opencode.json
│   └── codex.json
└── events/                  eventos idempotentes
    └── <event-id>.json
```

`events/` e `snapshots/` são criados automaticamente quando necessários.

## Atualizar tudo que for suportado

Use os adaptadores dos harnesses que estiver usando e depois gere o relatório:

```bash
python scripts/usage.py import-opencode --billing-mode subscription
python scripts/usage.py import-codex --billing-mode subscription
python scripts/usage.py report
```

Não há obrigação de instalar todos os harnesses. Um adaptador ausente não impede os demais.

## OpenCode

O OpenCode fornece estatísticas cumulativas por projeto:

```bash
python scripts/usage.py import-opencode --billing-mode subscription
```

O snapshot é substituído a cada importação para que executar o comando duas vezes não dobre os totais.

## Codex

O Codex mantém rollouts locais com o diretório de trabalho e eventos de contagem de tokens. O adaptador lê somente os metadados necessários e os eventos cumulativos de `token_count`, selecionando sessões cujo `cwd` pertence ao projeto atual:

```bash
python scripts/usage.py import-codex --billing-mode subscription
```

Por padrão procura em `$CODEX_HOME/sessions` ou `~/.codex/sessions`. Para outro local:

```bash
python scripts/usage.py import-codex --codex-home "P:/AI-State/Codex" --billing-mode subscription
```

Em uso por assinatura, o Codex não fornece uma cobrança real por projeto nos rollouts. Por isso o relatório deixa custo real/equivalente como **desconhecido**, em vez de inventar um rateio. Se houver uma equivalência calculada externamente e confiável, ela pode ser informada explicitamente:

```bash
python scripts/usage.py import-codex --billing-mode subscription --api-equivalent-cost 12.34
```

## Claude Code

Para uma execução programática salva em JSON:

```bash
claude -p "..." --output-format json > .project/usage/claude-result.json
python scripts/usage.py import-claude-json .project/usage/claude-result.json --billing-mode api
```

O import usa hash do arquivo como ID, portanto importar exatamente o mesmo resultado novamente não duplica a sessão. O arquivo bruto pode ser apagado depois; ele é ignorado pelo `.gitignore` quando segue o padrão `*-result.json`.

## Outros harnesses

Quando não houver adaptador, registre apenas as métricas disponíveis:

```bash
python scripts/usage.py add \
  --harness outro-harness \
  --provider <provider> \
  --model <modelo> \
  --billing-mode api \
  --input 100000 \
  --output 12000 \
  --reported-cost 1.23 \
  --actual-cost 1.23
```

Se o harness passar a expor telemetria estável (JSON, OpenTelemetry ou API local), crie um adaptador que alimente o mesmo schema, sem mudar a camada de relatório.

## Regras de interpretação

- `reported_cost_usd`: custo informado/calculado pelo harness;
- `actual_cost_usd`: cobrança realmente atribuível àquele uso;
- `api_equivalent_cost_usd`: equivalência econômica de API, útil para comparar assinatura vs API;
- `estimated: true`: valor estimado, nunca apresentado como medição exata;
- `—` no relatório significa **desconhecido**, nunca zero.

Os contadores são normalizados para reduzir dupla contagem conhecida de cache/reasoning. Ainda assim, providers podem ter semânticas diferentes; use custo reportado/real como referência financeira quando disponível.

Não force um rateio fictício de assinaturas mensais por projeto.
