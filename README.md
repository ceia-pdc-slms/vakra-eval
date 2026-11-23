# Eval oficial do Desafio Lumi Agêntico

Código que o PDC usa para avaliar os modelos dos times na **VAKRA** (caps 1 e 2), nos 9 domínios reservados. É uma cópia do [IBM/vakra](https://github.com/IBM/vakra) (commit `00dc68f`) com as mudanças listadas abaixo; o README original está em [`README.vakra.md`](README.vakra.md).

## Pedir uma avaliação

1. Subam o modelo e o `eval.yaml` para o repositório do time no Hugging Face: [`lumi-4b-time-a`](https://huggingface.co/ceia-pdc-slms/lumi-4b-time-a) ou [`lumi-4b-time-b`](https://huggingface.co/ceia-pdc-slms/lumi-4b-time-b).
2. Criem a tag, que fixa o commit avaliado: `hf repos tag create <repo> eval-v1 -m "o que mudou"`.
3. Abram uma issue com o formulário [**Pedir eval de um modelo**](../../issues/new?template=pedir-eval.yml).

O resultado volta na própria issue.

## Placar

- **Hub oficial do PDC:** https://ceia-pdc-slms.github.io (o placar aparece na lista, como Leaderboard)
- **Placar completo:** https://ceia-pdc-slms.github.io/vakra-eval/placar/ (gerado a partir de [`placar/`](placar/) deste repositório)

Para atualizar: `python3 placar/gerar.py <pasta dos runs>` e um PR.

## Regras

- Nada dos domínios reservados no treino: `airline`, `cookbook`, `law_episode`, `mental_health_survey`, `music_tracker`, `shakespeare`, `student_loan`, `university`, `world_development_indicators`. Vale para todas as capacidades e para dados sintéticos gerados a partir deles.
- BFCL (todas as versões) também fora do treino.
- Não movam nem apaguem uma tag já avaliada: criem a próxima (`eval-v2`, `eval-v3`...).

## O que muda em relação ao original

| Arquivo | Mudança |
|---|---|
| `benchmark_runner.py` | `--parallel-domains`: vários domínios ao mesmo tempo, cada um no seu processo |
| `agents/llm.py`, `agents/think_log.py` | campos extras na requisição (`OPENAI_EXTRA_BODY`) e registro do raciocínio de cada chamada em `think.jsonl` |
| `evaluator/evaluator.py`, `evaluator/judge.py` | juiz em paralelo (`JUDGE_WORKERS`), com provedor configurável e novas tentativas em 429 |
| `environment/configs/generate_task_1_tool_universe_mapping.py` | opção `--split` |
| `scripts/` | `run_lumitest.sh` (roda), `run_wdi_isolado.sh` e `eval_cap1.sh` (domínio que estoura memória, uma pergunta por sessão), `eval_lumitest.sh` (avalia) |

Juiz: `gpt-oss-120b`, o mesmo da VAKRA. Uma resposta com "Judge Error" conta como 0, então o eval só vale com 0 Judge Error.

## Rodar (coordenação)

```bash
make setup                                                          # ver setup.md
python environment/configs/generate_task_1_tool_universe_mapping.py --split train   # exigido pela cap 1
export MODEL=<nome servido> OPENAI_API_BASE=http://<host>:<porta>/v1 RUN_NAME=<run>
DOMINIOS_1="airline cookbook law_episode music_tracker shakespeare university" scripts/run_lumitest.sh 1
scripts/run_wdi_isolado.sh <run>      # último domínio da cap 1
scripts/run_lumitest.sh 2
scripts/eval_cap1.sh <run>; scripts/eval_lumitest.sh <run> 2
```

`.env`: `HF_TOKEN`, `VERTEX_PROJECT` (juiz no Vertex AI, token do `gcloud`). Dados, resultados e o `mcp_tool_universe_id_mapping.yaml` gerado ficam fora do Git, porque contêm perguntas do teste reservado.
