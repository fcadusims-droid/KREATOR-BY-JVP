# Formato do arquivo de estado

Local: `<raiz-do-projeto>/.pipeline/state.json`

**Raiz do projeto** = o diretório de trabalho atual da sessão do Claude Code, salvo indicação contrária. Se `.pipeline/` já existir em um diretório ancestral, use esse.

Este arquivo é a ÚNICA fonte da verdade sobre em que fase o projeto está. Nunca infira a fase da conversa.

```json
{
  "project_name": "string",
  "project_type": "software | document | research | other",
  "base_document": "caminho relativo para o documento original",
  "scope": {
    "id": "S1",
    "name": "escopo escolhido pelo humano na Fase 0",
    "source_sections": ["§18"],
    "chosen_at": "ISO8601",
    "required_resources": ["recurso: disponível | ausente | substituído por X"],
    "out_of_scope": ["o que foi explicitamente deixado de fora — usado para rejeitar scope creep"]
  },
  "current_phase": "scope | validate | develop | test | ship | done",
  "phase_status": "not_started | awaiting_execution | awaiting_verification | awaiting_human | rejected | verified",
  "max_attempts_per_phase": 3,
  "max_rollbacks": 2,
  "rollback_count": 0,
  "attempts": { "validate": 0, "develop": 0, "test": 0, "ship": 0 },
  "clarifications": [
    {
      "question": "pergunta levantada por um subagent como ambígua",
      "answer": "resposta do humano — PERSISTIR AQUI, senão o próximo subagent isolado não a verá",
      "asked_in_phase": "validate"
    }
  ],
  "acceptance_criteria": [
    {
      "id": "AC-001",
      "type": "assertion | measurement | human_judgment",
      "description": "string",
      "source": "trecho/seção do base_document (ou clarification) que originou este critério",
      "phase_required": "develop | test | ship",
      "status": "pending | met | failed | measured | approved | rejected | blocked",
      "measured_value": "só para type: measurement — o número/resultado observado",
      "human_verdict": "só para type: human_judgment — decisão do humano + justificativa"
    }
  ],
  "history": [
    {
      "phase": "validate",
      "attempt": 1,
      "role": "executor | verifier",
      "summary": "resumo curto",
      "verdict": "pass | fail | needs_human | n/a",
      "evidence": "comando rodado, output real, arquivo checado — nunca aceitar afirmação sem evidência",
      "timestamp": "ISO8601"
    }
  ],
  "escalation": { "active": false, "phase": null, "reason": null }
}
```

## Tipos de critério — e por que existem

Nem todo critério é uma barra que a máquina pula. Forçar tudo em `pass/fail` faz o sistema mentir: ou inventa uma barra que o documento não deu, ou marca `met` sem base. Três tipos:

| type | O que é | Quem decide | `status` possíveis |
|---|---|---|---|
| `assertion` | Verificável por máquina: rodar comando, checar output contra valor esperado | verifier subagent | `pending`, `met`, `failed`, `blocked` |
| `measurement` | A resposta é um número **a ser descoberto**, não uma barra conhecida ("medir custo real por vídeo") | executor mede, **humano julga** se o número serve | `pending`, `measured`, `blocked` |
| `human_judgment` | Juízo irredutivelmente humano ("um Short que o criador realmente postaria") | **só o humano** | `pending`, `approved`, `rejected`, `blocked` |

Regras:

- Um `measurement` com barra explícita **no documento** não é `measurement` — é `assertion`. "Custo abaixo de US$2" é assertion. "Custo confortavelmente abaixo do preço" é measurement (a barra é vaga; o humano decide).
- Um verifier **nunca** marca `human_judgment` como `approved`. Se tentar, é bug. Ele retorna `needs_human`.
- Um `measurement` sem `measured_value` preenchido não pode sair de `pending`. "Não deu pra medir" é `blocked`, com motivo — não é `measured`.

## Veredito `needs_human`

Verifier retorna `needs_human` quando a parte automatizável passou mas restam critérios `measurement` ou `human_judgment` pendentes na fase.

Ao receber: set `phase_status: "awaiting_human"`, apresente ao humano os valores medidos e os itens de julgamento **com a evidência**, e pare. Não avance. Não presuma a resposta. **`needs_human` não conta como tentativa** — não incremente `attempts`; nada falhou.

Ao receber a resposta do humano: grave em `human_verdict`/`measured_value`, registre em `clarifications` se for decisão reutilizável, e então avance ou volte a `awaiting_execution` conforme o veredito dele.

## Contagem de tentativas (não derive de `history`)

`history` tem entrada de executor E de verifier — contar linhas dá o dobro. Use só `attempts.<fase>`:

- Incremente em +1 **apenas quando o verifier retorna `fail`**.
- `pass` → zere `attempts.<fase>` e avance.
- `needs_human` → não mexa em `attempts`.
- Escale quando `attempts.<fase> >= max_attempts_per_phase`.

`max_attempts_per_phase` é calibrado na Fase 0 pelo `size_estimate` do escopo escolhido. O default 3 serve para `task`/`feature`. Para `project`/`program`, 3 tentativas garantem escalada imediata — o que significa que o escopo está grande demais para este pipeline e deveria ter sido fatiado na Fase 0, não compensado com um limite maior.

## Rollback (proteção contra ping-pong)

`test-verifier` pode exigir volta para `validate`. Legítimo, mas sem limite vira ciclo infinito:

- Cada rollback incrementa `rollback_count`.
- `rollback_count >= max_rollbacks` → **não role de volta**, escale. Dois rollbacks significam que a Fase 1 está estruturalmente errada ou o documento base é insuficiente; mais tentativas automáticas não resolvem.
- Rollback zera `attempts.develop` e `attempts.test` (recomeço legítimo, não falha acumulada).

## Escalation

- Ao escalar: `escalation.active = true`, com `phase` e `reason` específicos.
- **Ao retomar** por instrução explícita do humano: zere `escalation` inteiro E zere `attempts` da fase. Sem isso o estado trava e o pipeline escala de novo na primeira rodada.
- Informação nova vinda do humano vai para `clarifications` antes de retomar.

## `phase_status` — semântica de retomada

| valor | próxima ação do orquestrador |
|---|---|
| `not_started` | dispare o executor |
| `awaiting_execution` | dispare o executor com o feedback do verifier |
| `awaiting_verification` | dispare o verifier |
| `awaiting_human` | **pare** — pergunte e espere. Não dispare nada |
| `rejected` | incremente `attempts`, dispare executor com o motivo |
| `verified` | avance `current_phase` |

## `current_phase: done`

Quando `ship-verifier` retorna `pass`: `current_phase: "done"`, `phase_status: "verified"`, **pare**. Reporte quais critérios foram satisfeitos e com que evidência. Mudanças posteriores são um ciclo novo: adicione critérios e volte a `validate` explicitamente — nunca continue de `done` em silêncio.

## Regras de integridade

- Só o **orquestrador** escreve neste arquivo. Subagents retornam resultado estruturado; quem persiste é o processo principal.
- Nenhum critério vira `met`/`measured` sem `evidence` concreta. "Parece correto" não é evidência.
- `phase_status: verified` só depois do verifier retornar `pass`. Nunca pelo executor.
- Trabalho fora de `scope.out_of_scope` é rejeitado, não celebrado como iniciativa.
