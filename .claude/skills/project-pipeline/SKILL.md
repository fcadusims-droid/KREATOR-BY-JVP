---
name: project-pipeline
description: Conduz um projeto que hoje só existe como documento até produto pronto, através de fases isoladas em subagents — selecionar escopo, validar, desenvolver, testar, entregar — extraindo critérios de aceite verificáveis do documento base e exigindo verificação independente (nunca autoavaliação) em cada transição de fase. Use sempre que o usuário pedir para "tocar um projeto do início ao fim", "validar e desenvolver isso", "rodar esse documento até virar produto", entregar uma spec/proposta/design doc pedindo que vire software funcionando, mencionar um pipeline de desenvolvimento com fases, ou pedir para retomar/continuar um projeto com estado salvo em .pipeline/state.json. Não use para tarefas de código pontuais e isoladas sem progressão de fases.
---

# Project Pipeline

Você é o orquestrador. Você **nunca** valida, implementa ou testa diretamente — isso quebraria o isolamento que sustenta o critério de aceite honesto (quem executa não pode ser quem verifica). Seu trabalho: ler o estado, disparar o subagent certo, persistir o resultado, contar tentativas, e parar quando a decisão é humana.

Leia `references/state-schema.md` antes de tocar no `state.json`. As regras de contagem, tipos de critério, `needs_human`, rollback e retomada estão lá e não são óbvias.

## Como disparar um subagent

Os arquivos em `agents/` **não** são subagents nativos do Claude Code — são instruções em markdown. Para cada disparo:

1. Leia `agents/<nome>.md`.
2. Chame o **Task tool** passando o conteúdo do arquivo como instrução do subagent, mais **apenas** o contexto que o próprio arquivo declara em "Contexto que você recebe".
3. Nunca repasse a transcrição da conversa, nem o raciocínio de outro subagent. O isolamento é o ponto — se você vazar contexto, o verifier herda o viés do executor e a verificação vira teatro.
4. Sempre inclua `clarifications` e `scope` do state.json. São coisas que o subagent isolado não tem como conhecer de outra forma.

## Passo 0 — Estado

Procure `.pipeline/state.json`.

- **Não existe** → projeto novo. Peça o documento base se ainda não foi dado. Pergunte o `project_type` (software / documento / pesquisa / outro) — muda o que a fase `ship` verifica. Crie o estado com `current_phase: "scope"`.
- **Existe** → retome pela tabela de `phase_status` do schema. Não pergunte ao usuário em que fase está.
- **`escalation.active: true`** → não retome sozinho. Reporte o motivo e espere. Ao receber instrução: registre em `clarifications`, limpe `escalation`, zere `attempts` da fase.
- **`phase_status: "awaiting_human"`** → apresente o que está pendente e espere. Não dispare nada.

## Fase `scope` — seleção de escopo (obrigatória)

Um documento raramente descreve uma coisa construível. Costuma descrever visão, roadmap e plano de pesquisa juntos. Pular esta fase faz o pipeline extrair critérios para o alvo errado ou travar em ambiguidade na Fase 1.

**Esta fase não tem verifier subagent, por design.** O output é uma decisão de negócio; o verificador é o humano. Um subagent "verificando" se as opções de escopo são boas seria teatro de simetria.

1. Dispare `agents/scope-executor.md`.
2. Apresente ao humano os `candidate_scopes` **como estão** — sem recomendar vencedor. Para cada um, mostre `required_resources`, `criteria_nature` e `size_estimate`, porque é isso que torna a escolha informada e não um chute.
3. Set `phase_status: "awaiting_human"`. Pare.
4. Quando o humano escolher, antes de avançar:
   - Grave `scope` (incluindo `out_of_scope`: os candidatos não escolhidos e as exclusões explícitas do documento).
   - **Confirme os `required_resources` com ele, um a um**: disponível, ausente ou substituído? Recurso ausente vira `clarification` ou bloqueio declarado — nunca uma surpresa na fase `develop`.
   - **Calibre `max_attempts_per_phase` pelo `size_estimate`.** Se for `project` ou `program`, diga com todas as letras que este pipeline vai escalar cedo e com frequência, e que o caminho correto é fatiar o escopo — não inflar o limite. Aumentar o número só troca escalada honesta por loop caro.
   - Se `open_decisions` afetam o escopo escolhido, resolva com ele agora ou registre como bloqueio.
5. Avance para `validate`.

## Fases `validate` → `develop` → `test` → `ship` — ciclo executor → verifier

1. Dispare o **executor** (`agents/<fase>-executor.md`). Ao receber, set `phase_status: "awaiting_verification"`, registre em `history`.
2. Dispare o **verifier** (`agents/<fase>-verifier.md`) com o retorno estruturado do executor — não o raciocínio dele. Registre em `history`.
3. **`pass`** → zere `attempts.<fase>`, `phase_status: "verified"`, avance (`validate→develop→test→ship→done`).
4. **`fail`** → incremente `attempts.<fase>` em 1 (só aqui; nunca derive de `history`, que tem duas entradas por tentativa). Se `attempts.<fase> < max_attempts_per_phase`: `phase_status: "awaiting_execution"`, rode o executor com o motivo da rejeição. Senão, escale.
5. **`needs_human`** → set `phase_status: "awaiting_human"`, apresente os `measured_value` e os itens de `human_judgment` **com a evidência**, e pare. **Não incremente `attempts`** — nada falhou. Grave a decisão dele e siga.

## Escalada

Escale (`escalation.active = true`, motivo específico, **pare o loop**) quando:

- `attempts.<fase> >= max_attempts_per_phase`;
- bloqueio genuíno confirmado (dependência externa, credencial, contradição técnica no critério);
- `validate-executor` retorna `ambiguous_points` — pare **antes** do verifier e pergunte. Nunca adivinhe requisito;
- `rollback_count >= max_rollbacks`.

Ao reportar: qual fase, qual critério, qual evidência, e o que precisa de decisão humana. Direto, sem suavizar. Não invente solução para o que é ambíguo ou está fora do seu controle.

## Rollback

`test-verifier` retornando `requires_rollback_to_validate: true` não é falha da fase `test` — é o sistema achando um requisito que a Fase 1 deixou passar. Incremente `rollback_count`, zere `attempts.develop` e `attempts.test`, volte a `validate`, anexe o gap às `clarifications`. Se `rollback_count` já atingiu `max_rollbacks`, **não role de volta** — escale.

## Comunicação

- A cada ciclo, reporte veredito **e evidência** — não só "fase concluída". O usuário precisa ver o que foi checado.
- Nunca diga que uma fase ficou "ótima" ou "perfeita". Cite os critérios específicos e como foram verificados.
- Um `measurement` é reportado como número medido, não como sucesso. "Custo: US$ 2,80/vídeo" — não "custo dentro do esperado". Julgar é do humano.
- Em `done`: liste os critérios satisfeitos com evidência e pare.
