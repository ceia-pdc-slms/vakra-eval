#!/usr/bin/env bash
# Roda o lumitest: os 9 domínios reservados do Desafio Lumi Agêntico (split train).
# Uso: MODEL=... OPENAI_API_BASE=... scripts/run_lumitest.sh   # cap 1 e cap 2 em paralelo
#      P=3 scripts/run_lumitest.sh 1  # 3 domínios por vez (padrão 6)
#      scripts/run_lumitest.sh 1      # só cap 1 (7 domínios)
#      scripts/run_lumitest.sh 2      # só cap 2 (9 domínios)
# Rodar de novo retoma de onde parou.
set -e
# Ctrl+C no script também mata os runs em background (senão eles continuam vivos)
trap 'kill $(jobs -p) 2>/dev/null' INT TERM
cd "$(dirname "$0")/.."
set -a; source .env; set +a

# Modelo e endpoint (API compatível com a da OpenAI, ex.: vLLM), pelo ambiente:
#   MODEL=<nome servido> OPENAI_API_BASE=http://<host>:<porta>/v1 RUN_NAME=<pasta> scripts/run_lumitest.sh
# THINKING=true|false manda chat_template_kwargs.enable_thinking em cada requisição; vazio = padrão do servidor.
: "${MODEL:?informe MODEL}" "${OPENAI_API_BASE:?informe OPENAI_API_BASE}"
OPENAI_API_KEY="${OPENAI_API_KEY:-EMPTY}"
if [ -n "${THINKING:-}" ]; then
  export OPENAI_EXTRA_BODY="{\"chat_template_kwargs\": {\"enable_thinking\": $THINKING}}"
fi

PROVIDER="${PROVIDER:-openai}"   # os pares acima sem PROVIDER usam a API compatível com OpenAI
CAPS="${1:-1 2}"

export OPENAI_API_BASE OPENAI_API_KEY
export OPENAI_BASE_URL=$OPENAI_API_BASE
export PYTHONUNBUFFERED=1   # progresso aparece na hora, mesmo passando pelo grep
export CAPABILITY_1_DIR="${DADOS_1:-$PWD/data/train/capability_1_bi_apis}"
export CAPABILITY_2_DIR="$PWD/data/train/capability_2_dashboard_apis"
OUT="${OUT_DIR:-output/lumitest/${RUN_NAME:-$MODEL}}"

TODOS="airline cookbook law_episode music_tracker shakespeare university world_development_indicators"
DOMS_1="${DOMINIOS_1:-$TODOS}"   # DOMINIOS_1 limita a cap 1
DOMS_2="$TODOS mental_health_survey student_loan"
ITER_1=15   # cap 1: até 12 tool calls por pergunta
ITER_2=5    # cap 2: sempre 1 tool call

P="${P:-6}"                               # quantos domínios de cada cap rodam ao mesmo tempo
# SAMPLES="--max-samples-per-domain 10"      
SAMPLES=""      

# um runner por cap (as caps rodam juntas); dentro dele, até P domínios em paralelo,
# cada um no seu subprocesso (cap<N>/parts/<domínio>/), juntados em cap<N>/ ao terminar
for c in $CAPS; do
  eval "doms=\$DOMS_$c; iter=\$ITER_$c"
  # outro runner já grava nesta pasta: espera ele terminar (depois só completa o que faltar)
  while pgrep -f "benchmark_runner.py .*--output $OUT/cap$c( |\$)" >/dev/null; do sleep 20; done
  .venv/bin/python benchmark_runner.py --capability_id "$c" $(printf -- '--domain %s ' $doms) \
    --parallel-domains "$P" --max-iterations "$iter" $SAMPLES \
    --provider "$PROVIDER" --model "$MODEL" --output "$OUT/cap$c" 2>&1 | grep --line-buffered "\[capability\|Finished\|Interrupted" &
done
wait

for c in $CAPS; do .venv/bin/python validate_output.py "$OUT/cap$c"; done
