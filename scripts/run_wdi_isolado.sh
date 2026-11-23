#!/usr/bin/env bash
# Cap 1, domínio world_development_indicators: uma pergunta por sessão MCP.
# Uma pergunta com join enorme derruba o processo das tools por falta de memória e, no run normal,
# todas as seguintes falham em cascata. Aqui só ela falha (e ganha uma 2a tentativa sozinha).
# Uso: MODEL=... OPENAI_API_BASE=... [P=2] scripts/run_wdi_isolado.sh <pasta do run>
set -u
cd "$(dirname "$0")/.."
D=world_development_indicators
CAP="output/lumitest/${1:?informe a pasta do run}/cap1"; W="$CAP/wdi_isolado"; mkdir -p "$W"
SRC=data/train/capability_1_bi_apis/input/$D.json
N=$(jq length "$SRC")
um() { i=$1; [ -f "$W/$i/cap1/$D.json" ] && return 0
  mkdir -p "$W/ds$i/input"; jq --argjson i "$i" '[.[$i]]' "$SRC" > "$W/ds$i/input/$D.json"
  OUT_DIR="$W/$i" DADOS_1="$PWD/$W/ds$i" DOMINIOS_1=$D P=1 bash scripts/run_lumitest.sh 1 > "$W/$i.log" 2>&1; }
export -f um; export W D SRC
# 1a passada: em paralelo
seq 0 $((N-1)) | xargs -P "${P:-2}" -I{} bash -c 'um {}'
# 2a passada: só as que caíram por conexão, uma por vez (trava entre runs: uma por vez em toda a máquina)
for i in $(seq 0 $((N-1))); do f="$W/$i/cap1/$D.json"
  if [ ! -f "$f" ] || jq -e 'any(.[]; .error|tostring|test("ClosedResource|Connection closed|Failed to connect"))' "$f" >/dev/null; then
    rm -rf "$W/$i"; until mkdir /tmp/wdi_lock 2>/dev/null; do sleep 10; done; um "$i"; rmdir /tmp/wdi_lock; fi
done
# junta na ordem original
fs=(); ts=(); for i in $(seq 0 $((N-1))); do [ -f "$W/$i/cap1/$D.json" ] && fs+=("$W/$i/cap1/$D.json"); [ -f "$W/$i/cap1/${D}_tools.json" ] && ts+=("$W/$i/cap1/${D}_tools.json"); done
echo "${#fs[@]} de $N perguntas"
[ "${#fs[@]}" -eq "$N" ] || { echo "incompleto: rode de novo"; exit 1; }
jq -s 'add' "${fs[@]}" > "$CAP/$D.json.tmp" && mv "$CAP/$D.json.tmp" "$CAP/$D.json"
jq -s 'add' "${ts[@]}" > "$CAP/${D}_tools.json.tmp" && mv "$CAP/${D}_tools.json.tmp" "$CAP/${D}_tools.json"
mkdir -p "$CAP/parts/$D"; cat "$W"/*/cap1/think.jsonl > "$CAP/parts/$D/think.jsonl" 2>/dev/null
jq -r '[.[]|.status]|group_by(.)|map("\(.[0])=\(length)")|join(" ")' "$CAP/$D.json"
