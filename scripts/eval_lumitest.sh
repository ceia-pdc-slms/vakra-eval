#!/usr/bin/env bash
# Avalia um run do lumitest com o evaluator oficial da VAKRA.
# Uso: scripts/eval_lumitest.sh nemotron-3-nano-4b      # cap 1 e cap 2
#      scripts/eval_lumitest.sh nemotron-3-nano-4b 1    # só cap 1
#      RESUME=1 scripts/eval_lumitest.sh nemotron-3-nano-4b   # continua de onde parou
# Resultado: output/lumitest/<modelo>/cap<N>/eval/results.json (+ tabela no terminal)
set -e
cd "$(dirname "$0")/.."
set -a; source .env; set +a

# juiz: gpt-oss-120b (o mesmo da IBM). Para trocar de provedor, comente um bloco e descomente o outro.
export JUDGE_BACKEND=groq     # cliente compatível com a API da OpenAI; serve para os três

# Groq
# export API_KEY=$GROQ_API_KEY

# OpenRouter (provedor fixo: Near AI)
# export API_KEY=$OPENROUTER_API_KEY
# export JUDGE_BASE_URL=https://openrouter.ai/api/v1
# export JUDGE_PROVIDER=near-ai

# Vertex AI (token do gcloud, renovado sozinho)
export API_KEY=gcloud
export JUDGE_BASE_URL=https://aiplatform.googleapis.com/v1/projects/${VERTEX_PROJECT:?defina VERTEX_PROJECT no .env}/locations/global/endpoints/openapi
export JUDGE_MODEL=openai/gpt-oss-120b-maas

export JUDGE_WORKERS="${JUDGE_WORKERS:-12}"     # perguntas avaliadas ao mesmo tempo

MODEL="${1:?informe o modelo, ex.: scripts/eval_lumitest.sh nemotron-3-nano-4b}"
CAPS="${2:-1 2}"

for c in $CAPS; do
  case $c in
    1) name=capability_bi_apis;        gt=data/train/capability_1_bi_apis/output ;;
    2) name=capability_dashboard_apis; gt=data/train/capability_2_dashboard_apis/output ;;
  esac
  pred="output/lumitest/$MODEL/cap$c"
  ev="$pred/eval"
  # padrão: do zero (o evaluator reaproveita o results.json antigo). RESUME=1: pula os domínios já avaliados
  [ -n "${RESUME:-}" ] || rm -rf "$ev"
  mkdir -p "$ev/groundtruth"
  if [ -f "$ev/results.json" ]; then   # ao retomar, refaz os domínios que tiveram erro do juiz
    jq '.domains |= with_entries(select(.value | tostring | contains("Judge Error") | not))' \
      "$ev/results.json" > "$ev/results.tmp" && mv "$ev/results.tmp" "$ev/results.json"
  fi

  # gabarito só com as perguntas que o modelo respondeu (senão as que faltam contam como 0)
  for p in "$pred"/*.json; do
    [ -f "$p" ] || continue
    case $p in *_tools.json) continue ;; esac
    d=$(basename "$p")
    jq --slurpfile pr "$p" '[.[] | select(.uuid as $u | $pr[0] | any(.uuid == $u))]' "$gt/$d" > "$ev/groundtruth/$d"
  done
  [ -n "$(ls "$ev/groundtruth")" ] || { echo "cap $c: nenhum resultado em $pred ainda, pulando"; continue; }

  echo "cap $c · avaliando (log: $ev/eval.log)"
  .venv/bin/python evaluator/evaluator.py --capability_name "$name" \
    --gt_root "$ev/groundtruth" --pred_root "$pred" --output "$ev/results.json" > "$ev/eval.log" 2>&1

  # nota por domínio e média
  jq -r '(.domains | to_entries[] | [.key, .value.summary.num_samples, .value.summary.mean_dialogue_score]),
         ["TOTAL", .summary.n_samples, .summary.mean_dialogue_score]
         | "  \(.[0] | . + " " * (30 - length)) \(.[1]) perguntas  nota \(.[2] * 100 | round / 100)"' "$ev/results.json"
done
