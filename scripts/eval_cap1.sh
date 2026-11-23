#!/usr/bin/env bash
# Avalia a cap 1 com o wdi isolado (uma pergunta por sessão), porque o evaluator executa as tools do
# domínio inteiro numa sessão só e uma pergunta que estoura a memória invalida todas as seguintes.
# Perguntas sem resposta por falta de memória (erro de conexão) entram como faltantes (contam 0 no total).
# Uso: [REFAZER="airline"] scripts/eval_cap1.sh <run>
set -eu
cd "$(dirname "$0")/.."
set -a; source .env; set +a
export JUDGE_BACKEND=groq API_KEY=gcloud JUDGE_MODEL=openai/gpt-oss-120b-maas
export JUDGE_BASE_URL=https://aiplatform.googleapis.com/v1/projects/${VERTEX_PROJECT:?defina VERTEX_PROJECT no .env}/locations/global/endpoints/openapi
export JUDGE_WORKERS=1
D=world_development_indicators; R="output/lumitest/${1:?run}/cap1"; W="$R/wdi_isolado/ev"; mkdir -p "$W"
GT=data/train/capability_1_bi_apis/output/$D.json; PR="$R/$D.json"
[ -f "$PR" ] || { echo "sem $PR"; exit 1; }
um() { u=$1; d="$W/$u"; [ -f "$d/results.json" ] && ! grep -q "Judge Error" "$d/results.json" && return 0
  rm -rf "$d"; mkdir -p "$d/gt" "$d/pred"
  jq --arg u "$u" '[.[]|select(.uuid==$u)]' "$GT" > "$d/gt/$D.json"; jq --arg u "$u" '[.[]|select(.uuid==$u)]' "$PR" > "$d/pred/$D.json"
  .venv/bin/python evaluator/evaluator.py --capability_name capability_bi_apis --gt_root "$d/gt" --pred_root "$d/pred" --output "$d/results.json" > "$d/eval.log" 2>&1 || echo "falhou: $u"; }
export -f um; export D R W GT PR
jq -r '.[]|select((.error|tostring|test("ClosedResource|Connection closed|Failed to connect"))|not)|.uuid' "$PR" > "$W/uuids.txt"
jq -r '.[]|select(.error|tostring|test("ClosedResource|Connection closed|Failed to connect"))|.uuid' "$PR" > "$W/faltantes.txt"
xargs -P "${P:-3}" -I{} bash -c 'um {}' < "$W/uuids.txt"
EV="$R/eval"; mkdir -p "$EV"
python3 - "$W" "$EV/results.json" "$D" "${REFAZER:-}" "$R" <<'P'
import json,os,sys
W,out,D,ref,R=sys.argv[1:]
us=open(W+"/uuids.txt").read().split(); ms=open(W+"/faltantes.txt").read().split()
ds=[]
for u in us:
    r=json.load(open(f"{W}/{u}/results.json"))["domains"][D]; assert len(r["dialogues"])==1,u; ds+=r["dialogues"]
sc=[d["score"] for d in ds]; n=len(us)+len(ms)
dom={"domain":D,"n_groundtruth":n,"n_prediction":n,"n_paired":len(ds),"missing_prediction_uuids":ms,"extra_prediction_uuids":[],"dialogues":ds,
 "summary":{"num_samples":n,"num_correct":sum(sc),"mean_dialogue_score":sum(sc)/n,"min_dialogue_score":0.0 if ms else min(sc),"max_dialogue_score":max(sc)}}
res=json.load(open(out)) if os.path.exists(out) else {"capability_name":"capability_bi_apis","groundtruth_dir":R+"/eval/groundtruth","prediction_dir":R,"domains":{},"summary":{}}
for d in ref.split()+[D]: res["domains"].pop(d,None)
res["domains"][D]=dom
json.dump(res,open(out,"w"),indent=2,ensure_ascii=False)
print(f"wdi: {sum(sc):.0f} certas de {n} ({len(ms)} sem resposta por memória)")
P
RESUME=1 JUDGE_WORKERS=12 bash scripts/eval_lumitest.sh "$1" 1
