#!/usr/bin/env python3
"""Placar: coleta as notas agregadas dos runs e gera placar/index.html e
placar/completo.html (nenhuma pergunta, gabarito ou resposta: só contagens).
Uso: python3 placar/gerar.py                      # regenera a página a partir de placar/resultados.json
     python3 placar/gerar.py output/lumitest      # antes, atualiza resultados.json com os runs dessa pasta
Um run só entra quando a avaliação cobre todas as perguntas e não tem "Judge Error".
Para incluir um modelo, acrescente-o em MODELOS (a chave é o nome do run sem -think/-nothink).
O hub (ceia-pdc-slms.github.io) publica a página em até uma hora após o merge na main."""
import json, os, re, sys, html, datetime
AQUI = os.path.dirname(os.path.abspath(__file__)); JS = f"{AQUI}/resultados.json"
MODELOS = [("Qwen3.8-Flash-Next (FP8)", "", "qwen3.8-flash"), ("Nemotron 3 Nano 4B", "", "nemotron-3-nano-4b"),
           ("Lumi 4B", "https://huggingface.co/ceia-research/lumi-4b", "lumi-4b"),
           ("T6-Lumi 4B", "https://huggingface.co/gustavobarrosss/t6-lumi-4b", "t6-lumi-4b")]
MODOS = [("nothink", "sem thinking"), ("think", "com thinking")]
TOT = {1: 285, 2: 359}; NOME = {1: "BI APIs", 2: "Dashboard APIs"}
def le(run, c):
    p = f"{sys.argv[1]}/{run}/cap{c}/eval/results.json"
    if not os.path.exists(p): return None
    t = open(p).read(); D = json.loads(t)["domains"]
    if "Judge Error" in t or sum(d["n_groundtruth"] for d in D.values()) != TOT[c]: return None   # eval incompleto não entra
    return {k: (int(d["summary"]["num_correct"]), d["n_groundtruth"]) for k, d in sorted(D.items())}
CONN = re.compile(r"ClosedResource|Connection closed|Connection error|Failed to connect")
def tipos(run, c):
    """O que aconteceu com cada pergunta, só em contagens: ok, nao (errada), sem (sem apoio nas tools), exec (timeout, limite), conn (tools caíram)."""
    ev = json.load(open(f"{sys.argv[1]}/{run}/cap{c}/eval/results.json"))["domains"]; o = {}
    for d, e in sorted(ev.items()):
        nota = {x["uuid"]: x for x in e["dialogues"]}; n = {}
        for x in json.load(open(f"{sys.argv[1]}/{run}/cap{c}/{d}.json")):
            y = nota.get(x["uuid"])
            if y and y["score"] == 1: k = "ok"
            elif x["status"] == "error": k = "conn" if CONN.search(str(x.get("error") or "")) else "exec"
            else: k = "sem" if y["details"]["per_turn"][-1]["metadata"].get("groundedness_score") == 0 else "nao"
            n[k] = n.get(k, 0) + 1
        if sum(n.values()) != e["n_groundtruth"] or n.get("ok", 0) != int(e["summary"]["num_correct"]): sys.exit(f"contagem não bate: {run} cap {c} {d} {n}")
        o[d] = n
    return o
JT = f"{AQUI}/tipos.json"
res = json.load(open(JS)) if os.path.exists(JS) else {}   # "<run>/cap<c>": {domínio: [certas, total]}
tip = json.load(open(JT)) if os.path.exists(JT) else {}   # "<run>/cap<c>": {domínio: {tipo: contagem}}
if len(sys.argv) > 1:
    for _, _, k in MODELOS:
        for m, _ in MODOS:
            for c in (1, 2):
                v = le(f"{k}-{m}", c)
                if v: res[f"{k}-{m}/cap{c}"] = v; tip[f"{k}-{m}/cap{c}"] = tipos(f"{k}-{m}", c)
    json.dump(tip, open(JT, "w"), indent=1, sort_keys=True); open(JT, "a").write("\n")
    json.dump(res, open(JS, "w"), indent=1, sort_keys=True); open(JS, "a").write("\n")
R = {(k, m, c): res.get(f"{k}-{m}/cap{c}") for _, _, k in MODELOS for m, _ in MODOS for c in (1, 2)}
f2 = lambda v: f"{v:.2f}".replace(".", ",")
def nota(r, c): return sum(a for a, _ in r.values()) / TOT[c]
def barras(c):
    o = []
    for n, url, k in MODELOS:
        nm = f'<a href="{url}">{n}</a>' if url else n
        ls = ""
        for i, (m, rot) in enumerate(MODOS):
            r = R[k, m, c]
            if r is not None:
                v = nota(r, c); a = sum(x for x, _ in r.values())
                ls += f'<div class="lin" title="{html.escape(n)}, {rot}: {a} de {TOT[c]} certas"><span class="modo">{rot}</span><span class="trilho"><i class="s{i+1}" style="width:{v*100:.1f}%"></i></span><b class="val num">{f2(v)} <small>{a}/{TOT[c]}</small></b></div>'
        if ls: o.append(f'<div class="mod"><h3>{nm}</h3>{ls}</div>')
    return "".join(o)
def tabela(c):
    cols = [(n, k, m, rot) for n, _, k in MODELOS for m, rot in MODOS if R[k, m, c]]   # só runs finalizados
    doms = {}
    for n, k, m, _ in cols:
        for d, (_, t) in (R[k, m, c] or {}).items(): doms[d] = t
    h = "".join(f'<th class="r">{n}<br><span>{rot}</span></th>' for n, _, _, rot in cols)
    ls = ""
    for d in sorted(doms):
        tds = ""
        for _, k, m, _ in cols:
            r = R[k, m, c]
            if r is None or d not in r: tds += '<td class="r muted">–</td>'
            else:
                v = r[d][0] / r[d][1]; tds += f'<td class="r" style="background:color-mix(in srgb,var(--c1) {round(v*45)}%,transparent)">{f2(v)}</td>'
        ls += f'<tr><th scope="row"><code>{d}</code></th><td class="r">{doms[d]}</td>{tds}</tr>'
    return f'<div class="rolar"><table class="tabela"><thead><tr><th>Domínio</th><th class="r">Perguntas</th>{h}</tr></thead><tbody>{ls}</tbody></table></div>'
falta = [f"{n} {rot} (cap {c})" for n, _, k in MODELOS for m, rot in MODOS for c in (1, 2) if R[k, m, c] is None]
hoje = datetime.date.today().strftime("%d/%m/%Y")
SVG = '<svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" style="fill:var(--accent)"/><g fill="#fff"><rect x="6.5" y="7" width="3.6" height="18" rx="1.3"/><rect x="12" y="10.5" width="3.6" height="14.5" rx="1.3"/><rect x="17.5" y="14" width="3.6" height="11" rx="1.3"/><rect x="23" y="17.5" width="3.6" height="7.5" rx="1.3"/></g></svg>'
P = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Placar VAKRA: modelos de base do Desafio Lumi Agêntico</title>
<meta name="description" content="Notas de Lumi 4B, T6-Lumi 4B, Nemotron 3 Nano 4B e Qwen3.8-Flash, com e sem thinking, nas capacidades 1 e 2 da VAKRA (9 domínios reservados).">
<meta name="hub:kind" content="leaderboard">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<link rel="stylesheet" href="../../assets/tokens.css">
<link rel="stylesheet" href="../../assets/tema.css">
<script src="../../assets/tema.js" defer></script>
<style>
main.wrap {{ padding-top: 48px; padding-bottom: 96px; }}
h1.display {{ font-size: clamp(2rem, 4.4vw, 3.2rem); }}
h2 {{ font: 600 1.35rem/1.2 var(--font-display); margin: 48px 0 6px; }}
section > p {{ max-width: 72ch; }}
.duas {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 20px; margin-top: 24px; }}
.duas .card {{ padding: 22px 24px; }}
.duas h2 {{ margin: 0 0 4px; }}
.mod {{ margin-top: 18px; }}
.mod h3 {{ font-size: .95rem; font-weight: 600; margin: 0 0 6px; }}
.lin {{ display: grid; grid-template-columns: 98px 1fr 112px; gap: 10px; align-items: center; font-size: .84rem; margin: 4px 0; }}
.modo, .val small {{ color: var(--muted); font-weight: 400; }}
.trilho {{ height: 12px; display: block; border-left: 1px solid var(--line-strong); }}
.trilho i {{ display: block; height: 100%; min-width: 2px; border-radius: 0 4px 4px 0; }}
.s1 {{ background: var(--c1); }} .s2 {{ background: var(--c2); }}
.val {{ font-weight: 600; }}
.leg {{ display: flex; gap: 18px; font-size: .84rem; color: var(--muted); margin: 20px 0 0; }}
.leg i {{ display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; }}
.rolar {{ overflow-x: auto; margin-top: 14px; border: 1px solid var(--line); border-radius: var(--r); }}
.rolar th span {{ text-transform: none; letter-spacing: 0; }}
.rolar th, .rolar td {{ padding: 8px 10px; }}
.rolar thead th {{ min-width: 92px; }}
.rolar tbody th code {{ font-size: .82rem; }}
.rolar tbody th {{ text-transform: none; vertical-align: middle; letter-spacing: 0; color: var(--fg); }}
li {{ max-width: 76ch; margin: 6px 0; }}
</style>
</head>
<body>
<header class="appbar"><div class="appbar-in">
  <a class="marca" href="../../" aria-label="Início">{SVG}<span><b>PDC · SLMs</b><small>CEIA · UFG</small></span></a>
  <nav class="appnav"><a href="../../">Hub</a><button class="tema-btn" data-tema-alternar aria-label="Alternar tema claro/escuro"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/></svg></button></nav>
</div></header>
<main class="wrap">
<section>
<p class="eyebrow">Desafio Lumi Agêntico · {hoje}</p>
<h1 class="display">Placar VAKRA: modelos de base</h1>
<p class="lede">Fração de perguntas certas em 9 domínios da <a href="https://github.com/IBM/vakra">VAKRA</a> reservados para avaliação. O agente usa ferramentas por MCP e um modelo juiz confere a resposta.</p>
<p class="muted">Veja também o <a href="completo.html">placar completo</a>, com os tipos de erro.</p>
<div class="leg"><span><i class="s1"></i>sem thinking</span><span><i class="s2"></i>com thinking</span><span>escala de 0 a 1</span></div>
<div class="duas">
<div class="card"><h2>Capacidade 1 · {NOME[1]}</h2><p class="muted">285 perguntas, 7 domínios, até 12 chamadas de ferramenta</p>{barras(1)}</div>
<div class="card"><h2>Capacidade 2 · {NOME[2]}</h2><p class="muted">359 perguntas, 9 domínios, uma chamada de ferramenta</p>{barras(2)}</div>
</div>
</section>
<section>
<h2>Por domínio, capacidade 1</h2>{tabela(1)}
<h2>Por domínio, capacidade 2</h2>{tabela(2)}
</section>
<section>
<h2>Como ler</h2>
<ul>
<li>A nota é o número de acertos dividido pelo total de perguntas. Pergunta que estourou o tempo (300 s; 1.200 s no Qwen, por causa da fila do servidor) ou terminou em erro conta como errada.</li>
<li>Juiz: <code>gpt-oss-120b</code>. No Nemotron e no Qwen sem thinking, alguns domínios (<code>airline</code> e <code>cookbook</code>) foram julgados pelo mesmo modelo em outros provedores. Nenhuma nota tem erro do juiz.</li>
<li>Na capacidade 1, 5 das 32 perguntas de <code>world_development_indicators</code> não cabem na memória da máquina das ferramentas e contam como erro em todos os modelos.</li>
<li>O card do Lumi 4B pede thinking desligado e o do T6-Lumi pede ligado. Com ferramentas, ambos às vezes entram em laço e terminam em timeout.</li>
<li>O Lumi e o T6-Lumi rodaram em máquinas diferentes, em parte dos domínios. A velocidade muda quantas perguntas estouram o tempo, então diferenças pequenas entre modos não são conclusivas.</li>
<li>Só entram configurações com a avaliação completa; por isso nem todo modelo aparece nos dois modos e nas duas capacidades.</li>
<li>Cada configuração rodou uma vez, com temperatura 0, e sem intervalo de confiança.</li>
<li>As perguntas, os gabaritos e as respostas não são publicados: os domínios são o teste reservado do desafio.</li>
</ul>
</section>
</main>
</body>
</html>
"""
D = f"{AQUI}/index.html"
open(D, "w").write(P); print("gerado", D, "| fora (não finalizados):", falta)

OBS = ["Só entram runs com a avaliação completa e sem erro do juiz.",
 "Pergunta que estourou o tempo (300 s; 1.200 s no Qwen, por causa da fila do servidor) ou terminou em erro conta como errada.",
 "Na cap 1, 5 das 32 perguntas de world_development_indicators não cabem na memória da máquina das ferramentas e contam como erro em todos os runs (“tools caíram”).",
 "O card do Lumi 4B pede thinking desligado e o do T6-Lumi pede ligado.",
 "Lumi e T6-Lumi rodaram em máquinas diferentes em parte dos domínios, e a velocidade muda quantas perguntas estouram o tempo.",
 "Cada configuração rodou uma vez, com temperatura 0.",
 "Perguntas, gabaritos e respostas não são publicados: os domínios são o teste reservado do desafio."]
E = {"atualizado": hoje, "obs": OBS, "nomes": {f"{k}-{m}": f"{n} {rot}" for n, _, k in MODELOS for m, rot in MODOS},
     "dados": [{"run": a.rsplit("/", 1)[0], "cap": int(a[-1]), "d": d, "n": sum(o.values()), "o": o} for a, ds in sorted(tip.items()) for d, o in sorted(ds.items())]}
open(f"{AQUI}/completo.html", "w").write(open(f"{AQUI}/_modelo.html").read().replace("/*DADOS*/", json.dumps(E, ensure_ascii=False).replace("</", "<\\/")))
print("gerado", f"{AQUI}/completo.html")
