#!/usr/bin/env python3
"""Placar: coleta as notas agregadas dos runs e gera placar/index.html (nenhuma pergunta, gabarito ou resposta).
Uso: python3 placar/gerar.py                      # regenera a página a partir de placar/resultados.json
     python3 placar/gerar.py output/lumitest      # antes, atualiza resultados.json com os runs dessa pasta
Um run só entra quando a avaliação cobre todas as perguntas e não tem "Judge Error".
Para incluir um modelo, acrescente-o em MODELOS (a chave é o nome do run sem -think/-nothink; o último campo é o time: "a", "b" ou "base").
O hub (ceia-pdc-slms.github.io) publica a página em até uma hora após o merge na main."""
import json, os, sys, html, datetime
AQUI = os.path.dirname(os.path.abspath(__file__)); JS = f"{AQUI}/resultados.json"
MODELOS = [("eval-v1", "https://github.com/ceia-pdc-slms/vakra-eval/issues/5", "time-a-eval-v1", "a"),
           ("Qwen3.8-Flash-Next (FP8)", "", "qwen3.8-flash", "base"), ("Nemotron 3 Nano 4B", "", "nemotron-3-nano-4b", "base"),
           ("Lumi 4B", "https://huggingface.co/ceia-research/lumi-4b", "lumi-4b", "base"),
           ("T6-Lumi 4B", "https://huggingface.co/gustavobarrosss/t6-lumi-4b", "t6-lumi-4b", "base")]
GRUPOS = [("a", "Time A"), ("b", "Time B"), ("base", "Modelos de base")]   # A: cores quentes; B: cores frias; base: cinza
MODOS = [("nothink", "sem thinking"), ("think", "com thinking")]
TOT = {1: 285, 2: 359}; NOME = {1: "BI APIs", 2: "Dashboard APIs"}
def le(run, c):
    p = f"{sys.argv[1]}/{run}/cap{c}/eval/results.json"
    if not os.path.exists(p): return None
    t = open(p).read(); D = json.loads(t)["domains"]
    if "Judge Error" in t or sum(d["n_groundtruth"] for d in D.values()) != TOT[c]: return None   # eval incompleto não entra
    return {k: (int(d["summary"]["num_correct"]), d["n_groundtruth"]) for k, d in sorted(D.items())}
res = json.load(open(JS)) if os.path.exists(JS) else {}   # "<run>/cap<c>": {domínio: [certas, total]}
if len(sys.argv) > 1:
    for _, _, k, _ in MODELOS:
        for m, _ in MODOS:
            for c in (1, 2):
                v = le(f"{k}-{m}", c)
                if v: res[f"{k}-{m}/cap{c}"] = v
    json.dump(res, open(JS, "w"), indent=1, sort_keys=True); open(JS, "a").write("\n")
R = {(k, m, c): res.get(f"{k}-{m}/cap{c}") for _, _, k, _ in MODELOS for m, _ in MODOS for c in (1, 2)}
f2 = lambda v: f"{v:.2f}".replace(".", ",")
def nota(r, c): return sum(a for a, _ in r.values()) / TOT[c]
def barras(c):
    o = []
    for g, gn in GRUPOS:
        o.append(f'<div class="grupo g-{g}"><h3 class="gt">{gn}</h3>')
        tem = False
        for n, url, k, t in MODELOS:
            if t != g: continue
            nm = f'<a href="{url}">{n}</a>' if url else n
            ls = ""
            for i, (m, rot) in enumerate(MODOS):
                r = R[k, m, c]
                if r is not None:
                    v = nota(r, c); a = sum(x for x, _ in r.values())
                    ls += f'<div class="lin" title="{gn}, {html.escape(n)}, {rot}: {a} de {TOT[c]} certas"><span class="modo">{rot}</span><span class="trilho"><i class="s{i+1}" style="width:{v*100:.1f}%"></i></span><b class="val num">{f2(v)} <small>{a}/{TOT[c]}</small></b></div>'
            if ls: tem = True; o.append(f'<div class="mod"><h4>{nm}</h4>{ls}</div>')
        o.append(("" if tem else '<p class="muted vazio">Nenhum modelo avaliado ainda.</p>') + '</div>')
    return "".join(o)
def tabela(c):
    cols = [(n, k, m, rot, g) for g, _ in GRUPOS for n, _, k, t in MODELOS if t == g for m, rot in MODOS if R[k, m, c]]   # só runs finalizados
    doms = {}
    for n, k, m, _, _ in cols:
        for d, (_, t) in (R[k, m, c] or {}).items(): doms[d] = t
    ini = [i for i, x in enumerate(cols) if i == 0 or cols[i - 1][4] != x[4]]   # primeira coluna de cada grupo
    cl = lambda i: f'g-{cols[i][4]}' + (' ini' if i in ini else '')
    gs = "".join(f'<th class="gh g-{g} ini" colspan="{sum(x[4] == g for x in cols)}">{gn}</th>' for g, gn in GRUPOS if any(x[4] == g for x in cols))
    h = "".join(f'<th class="r {cl(i)}">{n}<br><span>{rot}</span></th>' for i, (n, _, _, rot, _) in enumerate(cols))
    ls = ""
    for d in sorted(doms):
        tds = ""
        for i, (_, k, m, _, _) in enumerate(cols):
            r = R[k, m, c]
            if r is None or d not in r: tds += f'<td class="r muted {cl(i)}">–</td>'
            else:
                v = r[d][0] / r[d][1]; tds += f'<td class="r {cl(i)}" style="background:color-mix(in srgb,var(--cor) {round(v*45)}%,transparent)">{f2(v)}</td>'
        ls += f'<tr><th scope="row"><code>{d}</code></th><td class="r">{doms[d]}</td>{tds}</tr>'
    return f'<div class="rolar"><table class="tabela"><thead><tr><th colspan="2"></th>{gs}</tr><tr><th>Domínio</th><th class="r">Perguntas</th>{h}</tr></thead><tbody>{ls}</tbody></table></div>'
falta = [f"{n} {rot} (cap {c})" for n, _, k, _ in MODELOS for m, rot in MODOS for c in (1, 2) if R[k, m, c] is None]
hoje = datetime.date.today().strftime("%d/%m/%Y")
SVG = '<svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" style="fill:var(--accent)"/><g fill="#fff"><rect x="6.5" y="7" width="3.6" height="18" rx="1.3"/><rect x="12" y="10.5" width="3.6" height="14.5" rx="1.3"/><rect x="17.5" y="14" width="3.6" height="11" rx="1.3"/><rect x="23" y="17.5" width="3.6" height="7.5" rx="1.3"/></g></svg>'
P = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Placar VAKRA do Desafio Lumi Agêntico</title>
<meta name="description" content="Notas dos modelos do Time A e do Time B e de Lumi 4B, T6-Lumi 4B, Nemotron 3 Nano 4B e Qwen3.8-Flash, com e sem thinking, nas capacidades 1 e 2 da VAKRA (9 domínios reservados).">
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
.mod h4 {{ font-size: .95rem; font-weight: 600; margin: 0 0 6px; }}
.lin {{ display: grid; grid-template-columns: 98px 1fr 112px; gap: 10px; align-items: center; font-size: .84rem; margin: 4px 0; }}
.modo, .val small {{ color: var(--muted); font-weight: 400; }}
.trilho {{ height: 12px; display: block; border-left: 1px solid var(--line-strong); }}
.trilho i {{ display: block; height: 100%; min-width: 2px; border-radius: 0 4px 4px 0; }}
.g-a {{ --cor: var(--c2); --fundo: var(--c2-soft); }} .g-b {{ --cor: var(--c1); --fundo: var(--c1-soft); }} .g-base {{ --cor: var(--faint); --fundo: var(--sunken); }}
.grupo {{ border-left: 4px solid var(--cor); padding: 2px 0 2px 16px; margin-top: 22px; }}
.gt {{ display: inline-block; font-size: .84rem; font-weight: 600; margin: 0; padding: 3px 10px; border-radius: var(--r-sm); background: var(--fundo); }}
.grupo .mod {{ margin-top: 12px; }} .vazio {{ margin: 10px 0 0; font-size: .88rem; }}
.rolar th.gh {{ text-align: left; text-transform: none; letter-spacing: 0; color: var(--fg); background: var(--fundo); border-top: 4px solid var(--cor); }}
.rolar .ini {{ border-left: 2px solid var(--cor); }}
.s1 {{ background: color-mix(in srgb, var(--cor) 55%, var(--surface)); }} .s2 {{ background: var(--cor); }}
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
<h1 class="display">Placar VAKRA</h1>
<p class="lede">Fração de perguntas certas em 9 domínios da <a href="https://github.com/IBM/vakra">VAKRA</a> reservados para avaliação. O agente usa ferramentas por MCP e um modelo juiz confere a resposta.</p>
<div class="leg"><span class="g-a"><i class="s2"></i>Time A</span><span class="g-b"><i class="s2"></i>Time B</span><span class="g-base"><i class="s2"></i>Modelos de base</span><span>tom suave: sem thinking · tom cheio: com thinking · escala de 0 a 1</span></div>
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
<li>O <a href="https://github.com/ceia-pdc-slms/vakra-eval/issues/5">eval-v1 do Time A</a> tem os mesmos pesos, código e configuração do Lumi 4B (conferido por hash); a nota é a do run do Lumi 4B com thinking, sem novo run.</li>
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
