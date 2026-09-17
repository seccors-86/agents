# Project Development Standard

Template leve para projetos desenvolvidos com coding agents, desenhado em torno de quatro princípios:

1. **Autonomia** — modelo, harness e editor devem ser substituíveis.
2. **Controle** — regras, contexto, permissões e gates devem ser explícitos.
3. **Gestão** — decisões, estado, custo e evolução devem ser observáveis sem depender de chats.
4. **Simplicidade** — adicionar processo e ferramentas apenas quando resolvem uma dor real.

## Ideia central

O **repositório é o cérebro durável do projeto**. Conversas são contexto transitório. O harness executa. O modelo raciocina. Nenhum fornecedor deve ser a única fonte de conhecimento do projeto.

```text
Editor (ex.: VS Code)
        ↓
Harness substituível
OpenCode / Codex / Claude Code / outro
        ↓
Modelo substituível
GLM / GPT / Claude / outro
        ↓
Repositório Git
├── AGENTS.md            mapa operacional
├── PROJECT.md           identidade e estado estável
├── .project/            configuração e estado corrente
├── docs/                conhecimento durável
├── .agents/skills/      método de trabalho portátil
└── scripts/             doctor, verify e usage
```

## Começar um projeto novo

1. Use este diretório como template do novo repositório.
2. Preencha `PROJECT.md` apenas com fatos conhecidos.
3. Ajuste `.project/config.json` aos comandos reais do projeto.
4. Inicie seu harness na raiz do repositório.
5. Peça: **"Inicialize este projeto seguindo a skill project-workflow."**

## Adotar um projeto existente

Peça ao agente:

> Adote este projeto no Project Development Standard. Reconstrua o estado a partir de código, Git, testes/CI e documentação existente. Não altere código funcional durante a adoção. Registre fatos verificáveis, marque inferências e apresente apenas lacunas que exigem confirmação humana.

A skill `project-workflow` contém o procedimento completo.

## Atualização incremental

Documentação não é diário de bordo. O Git já registra a história.

Atualize um artefato somente quando a mudança alterar conhecimento que um agente futuro precisará saber. Exemplos:

- mudança pequena de implementação: normalmente nenhuma documentação;
- novo comportamento público: atualizar documentação correspondente;
- decisão arquitetural importante: ADR;
- feature complexa: spec;
- foco/blocker atual: `.project/state.md`;
- mudança em comandos de validação: `.project/config.json` e, se necessário, `AGENTS.md`.

## Telemetria de IA

`.project/usage/` mantém o uso por projeto sem transformar o histórico de chat em banco de dados.

O relatório diferencia:

- **tokens observados**;
- **custo reportado pelo harness**;
- **custo real atribuído** quando houver cobrança metered/API identificável;
- **custo equivalente de API** quando o uso vier de assinatura;
- **estimativas** claramente marcadas como estimativas.

Execute:

```bash
python scripts/usage.py import-opencode --billing-mode subscription
python scripts/usage.py report
```

O OpenCode pode fornecer estatísticas cumulativas por projeto; outros harnesses alimentam o mesmo formato por adaptadores ou pelo comando `add`.

## Gates

`python scripts/verify.py` executa os comandos configurados em `.project/config.json`.

O princípio é simples:

> A IA pode decidir como implementar; software determinístico decide se os gates passaram.

`verify.py` não retorna PASS se nenhum gate real estiver configurado.

## O que NÃO é obrigatório

Beads, Spec Kit, MCPs, Serena, Ruler, multiagentes e outros componentes são opcionais. Eles só entram quando o projeto demonstrar uma necessidade concreta.

## Critério para adicionar complexidade

Antes de instalar uma ferramenta, responda:

> Qual problema recorrente deste projeto ela resolve e o que acontece se a removermos amanhã?

Se remover a ferramenta fizer o projeto perder conhecimento essencial, existe um novo lock-in que precisa ser justificado.
