#!/usr/bin/env python3
"""Gera relatório técnico HTML a partir de resultados AGREGADOS do Grupo 1.

Uso (executar na raiz do repositório):
    python gerar_relatorio.py
    python gerar_relatorio.py --atualizar

A opção --atualizar executa os três scripts de análise e a simulação antes do relatório.
Não inclui os questionários individuais no relatório; apenas agregações.
Não valida PMV/ePMV nem substitui medições ambientais sincronizadas.
A seção de simulações é identificada como hipotética e separada do TSV real.
"""

import argparse
import base64
import csv
import json
import math
from html import escape
from pathlib import Path
import subprocess
import sys
from datetime import datetime

ZONAS = [f"R{i}" for i in range(1, 7)]
SCRIPTS = [
    "analisar_questionarios.py",
    "analisar_met_clo.py",
    "analisar_preferencia_satisfacao.py",
    "simular_conforto.py",
]
CSV_NOMES = [
    "resumo_por_zona.csv",
    "resumo_met_clo_por_zona.csv",
    "resumo_preferencia_satisfacao_por_zona.csv",
    "tsv_versus_preferencia.csv",
]
FIGURAS = [
    ("tsv_por_zona.png", "Figura 1 — Sensação térmica média por zona"),
    ("clo_versus_tsv.png", "Figura 2 — Relação entre clo estimado e TSV"),
    ("preferencia_por_zona.png", "Figura 3 — Preferência térmica por zona"),
    ("satisfacao_por_zona.png", "Figura 4 — Satisfação térmica por zona"),
    ("tsv_versus_preferencia.png", "Figura 5 — TSV e preferência térmica"),
]


def ler_csv(caminho):
    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def numero(texto, padrao=0.0):
    if texto is None or str(texto).strip() == "":
        return padrao
    return float(str(texto).replace(",", "."))


def inteiro(texto):
    return int(numero(texto))


def formatar_numero(valor, casas=2):
    return f"{valor:.{casas}f}".replace(".", ",")


def porc(parte, total):
    return "—" if total == 0 else formatar_numero(100 * parte / total, 1) + "%"


def por_zona(linhas):
    dados = {linha["Zona"].strip().upper(): linha for linha in linhas}
    faltam = [zona for zona in ZONAS if zona not in dados]
    if faltam:
        raise ValueError("Faltam zonas nos resultados agregados: " + ", ".join(faltam))
    return dados


def imagem_html(arquivo, titulo):
    if not arquivo.is_file():
        return f'<p class="aviso">Gráfico não encontrado: {escape(arquivo.name)}.</p>'
    dados = base64.b64encode(arquivo.read_bytes()).decode("ascii")
    return (f'<figure><img alt="{escape(titulo)}" src="data:image/png;base64,{dados}">'
            f'<figcaption>{escape(titulo)}</figcaption></figure>')




def bloco_simulacoes(pasta):
    """Inclui simulações já produzidas; nunca mistura valores com TSV real."""
    subpasta = pasta / "simulacoes"
    nomes = ["simulacao_por_temperatura.csv", "simulacao_por_zona.csv", "premissas.json"]
    ausentes = [nome for nome in nomes if not (subpasta / nome).is_file()]
    if ausentes:
        return (
            '<h2>5. Simulações computacionais — dados hipotéticos</h2>'
            '<div class="nota"><p>Os arquivos de simulação ainda não foram encontrados. '
            'Execute <code>python simular_conforto.py</code> e gere novamente o relatório. '
            'Esta seção não representa uma validação experimental.</p></div>'
        )

    por_temperatura = ler_csv(subpasta / "simulacao_por_temperatura.csv")
    por_zona = ler_csv(subpasta / "simulacao_por_zona.csv")
    with (subpasta / "premissas.json").open("r", encoding="utf-8") as arq:
        premissas = json.load(arq)
    if not por_temperatura:
        raise ValueError("O arquivo de simulação por temperatura está vazio.")

    def formatar_hipotetico(valor, casas=2):
        if valor is None or str(valor).strip() == "":
            return "—"
        try:
            n = float(str(valor).replace(",", "."))
        except ValueError:
            return "—"
        return formatar_numero(n, casas) if math.isfinite(n) else "—"

    def valido(linha):
        return linha.get("situacao", "").strip() == "calculado"

    validos = [x for x in por_temperatura if valido(x)]
    invalidos = [x for x in por_temperatura if not valido(x)]
    temperaturas_invalidas = ", ".join(
        formatar_hipotetico(x.get("temperatura_hipotetica_C"), 0)
        for x in invalidos
    ) or "nenhuma"
    parametros = (
        f"Umidade relativa: {formatar_hipotetico(premissas.get('umidade_hipotetica_pct'), 0)}%; "
        f"velocidade do ar: {formatar_hipotetico(premissas.get('velocidade_hipotetica_m_s'))} m/s; "
        "temperatura radiante assumida igual à do ar; "
        f"coeficiente de expectativa: {formatar_hipotetico(premissas.get('coeficiente_expectativa_hipotetico'))} "
        "(hipotético, não calibrado)."
    )

    menor_ppd = None
    for linha in validos:
        valor = linha.get("ppd", "")
        if valor.strip():
            ppd = numero(valor)
            if math.isfinite(ppd) and (menor_ppd is None or ppd < menor_ppd[0]):
                menor_ppd = (ppd, linha.get("temperatura_hipotetica_C", ""))
    if menor_ppd:
        frase_ppd = (
            f"Na grade de temperaturas analisada, o menor PPD previsto foi de "
            f"{formatar_numero(menor_ppd[0], 1)}%, em "
            f"{formatar_hipotetico(menor_ppd[1], 0)} °C. "
            "Esse valor não define a temperatura ideal do laboratório."
        )
    else:
        frase_ppd = "Nenhum PPD válido foi obtido nos cenários avaliados."

    linhas_temperatura = []
    for linha in por_temperatura:
        status = "Calculado" if valido(linha) else "Fora dos limites"
        colunas = [
            formatar_hipotetico(linha.get("temperatura_hipotetica_C"), 0),
            formatar_hipotetico(linha.get("pmv")),
            formatar_hipotetico(linha.get("ppd"), 1),
            formatar_hipotetico(linha.get("epmv_artigo")),
            formatar_hipotetico(linha.get("epmv_grupo1")),
            status,
        ]
        linhas_temperatura.append("<tr>" + "".join(f"<td>{escape(x)}</td>" for x in colunas) + "</tr>")

    linhas_zona = []
    for linha in por_zona:
        colunas = [
            linha.get("zona", ""),
            linha.get("respostas", ""),
            formatar_hipotetico(linha.get("met_medio_estimado"), 3),
            formatar_hipotetico(linha.get("clo_medio_estimado"), 3),
            formatar_hipotetico(linha.get("pmv")),
            formatar_hipotetico(linha.get("epmv_artigo")),
            formatar_hipotetico(linha.get("epmv_grupo1")),
        ]
        linhas_zona.append("<tr>" + "".join(f"<td>{escape(str(x))}</td>" for x in colunas) + "</tr>")

    figuras_sim = [
        ("pmv_epmv_por_temperatura.png", "Figura 6 — PMV e ePMV versus temperatura hipotética"),
        ("ppd_por_temperatura.png", "Figura 7 — PPD versus temperatura hipotética"),
        ("indices_por_zona_simulados.png", "Figura 8 — Perfis de met/clo por região sob temperatura hipotética comum"),
    ]
    graficos = "\n".join(imagem_html(subpasta / nome, legenda)
                         for nome, legenda in figuras_sim)
    return f"""<h2>5. Simulações computacionais — dados hipotéticos</h2>
<div class="nota"><p><strong>ATENÇÃO: cenários simulados, não medições reais.</strong>
Os resultados abaixo não foram calculados com temperaturas e umidades medidas no laboratório.
Os valores de met e clo são médias estimadas de respostas reais, mas as condições ambientais
foram definidas para uma demonstração didática. Não há validação contra os votos TSV.</p></div>
<p><strong>Premissas:</strong> {escape(parametros)}</p>
<p>Foram calculados <strong>{len(validos)} de {len(por_temperatura)}</strong> cenários da série
por temperatura dentro dos limites adotados pelo modelo.
Cenários sem cálculo: <strong>{escape(temperaturas_invalidas)} °C</strong>.
Uma célula vazia indica ausência de cálculo válido, nunca índice igual a zero.</p>
<p>{escape(frase_ppd)}</p>
<h3>5.1. Índices versus temperatura hipotética</h3>
<table><thead><tr><th>T_ar (°C)</th><th>PMV</th><th>PPD (%)</th>
<th>ePMV simplificado</th><th>ePMV Grupo 1</th><th>Situação</th></tr></thead>
<tbody>{''.join(linhas_temperatura)}</tbody></table>
{graficos}
<h3>5.2. Perfis por região (mesma temperatura hipotética de 25 °C)</h3>
<p>Esta comparação modifica os perfis médios de met e clo, mantendo a condição
ambiental hipotética igual entre as regiões. R3 e R4 não possuem questionários.
Os valores abaixo não são a sensação térmica realmente observada nas zonas.</p>
<table><thead><tr><th>Zona</th><th>N</th><th>met</th><th>clo</th>
<th>PMV</th><th>ePMV simplificado</th><th>ePMV Grupo 1</th></tr></thead>
<tbody>{''.join(linhas_zona)}</tbody></table>
<p><strong>Diferença metodológica:</strong> o ePMV simplificado segue a relação
<code>e × PMV</code> usada no artigo; o ePMV do Grupo 1 usa a função
<code>pmv_e()</code> da biblioteca. As duas implementações não são consideradas
matematicamente equivalentes. O coeficiente adotado é apenas ilustrativo para
este laboratório com ar-condicionado.</p>"""

def gerar_relatorio(pasta):
    faltantes = [nome for nome in CSV_NOMES if not (pasta / nome).is_file()]
    if faltantes:
        raise FileNotFoundError("Arquivos de análise não encontrados em 'resultados/': " +
                                ", ".join(faltantes) +
                                ". Execute os três scripts antes ou use --atualizar.")

    tsv = por_zona(ler_csv(pasta / "resumo_por_zona.csv"))
    metclo = por_zona(ler_csv(pasta / "resumo_met_clo_por_zona.csv"))
    preferencias = por_zona(ler_csv(pasta / "resumo_preferencia_satisfacao_por_zona.csv"))
    cruzamento = ler_csv(pasta / "tsv_versus_preferencia.csv")

    n_por_zona = [inteiro(tsv[z]["Respostas"]) for z in ZONAS]
    total = sum(n_por_zona)
    if total == 0:
        raise ValueError("Não há respostas válidas para compor o relatório.")

    # Os três arquivos devem representar a mesma quantidade de respostas por zona.
    for z in ZONAS:
        n = inteiro(tsv[z]["Respostas"])
        if n != inteiro(metclo[z]["Respostas"]) or n != inteiro(preferencias[z]["Respostas"]):
            raise ValueError(f"Inconsistência no número de respostas da zona {z}. "
                             "Execute os três scripts novamente com o mesmo CSV.")

    # TSV geral é calculado usando a tabela de frequências por voto (sem arredondar médias zonais).
    n_cruz = sum(inteiro(linha["Total"]) for linha in cruzamento)
    if n_cruz != total:
        raise ValueError("Tabela TSV x preferência tem total divergente dos resumos por zona.")
    tsv_medio = sum(int(linha["TSV"]) * inteiro(linha["Total"])
                    for linha in cruzamento) / total
    frio = sum(inteiro(linha["Total"]) for linha in cruzamento if int(linha["TSV"]) < 0)
    divergencia = sum(inteiro(linha["Mais fria"]) for linha in cruzamento
                      if int(linha["TSV"]) < 0)

    pref_quente = sum(inteiro(preferencias[z]["Prefere mais quente"]) for z in ZONAS)
    pref_mantem = sum(inteiro(preferencias[z]["Prefere sem mudança"]) for z in ZONAS)
    pref_fria = sum(inteiro(preferencias[z]["Prefere mais fria"]) for z in ZONAS)
    satis = sum(inteiro(preferencias[z]["Satisfeitos"]) for z in ZONAS)
    insatis = sum(inteiro(preferencias[z]["Insatisfeitos"]) for z in ZONAS)
    neutros = sum(inteiro(preferencias[z]["Neutros"]) for z in ZONAS)
    if pref_quente + pref_mantem + pref_fria != total or satis + insatis + neutros != total:
        raise ValueError("Somatório de preferências/satisfação diverge do total de respostas.")

    # Médias de met/clo calculadas a partir de médias de zona já arredondadas.
    met_medio = sum(inteiro(metclo[z]["Respostas"]) * numero(metclo[z]["met médio"])
                    for z in ZONAS) / total
    clo_medio = sum(inteiro(metclo[z]["Respostas"]) * numero(metclo[z]["clo médio"])
                    for z in ZONAS) / total

    linhas_tabela = []
    for z in ZONAS:
        n = inteiro(tsv[z]["Respostas"])
        fr = inteiro(tsv[z]["Relatos de frio"]) if n else 0
        media = formatar_numero(numero(metclo[z]["TSV médio"]), 3) if n else "—"
        m = formatar_numero(numero(metclo[z]["met médio"]), 3) if n else "—"
        c = formatar_numero(numero(metclo[z]["clo médio"]), 3) if n else "—"
        sat = inteiro(preferencias[z]["Satisfeitos"]) if n else 0
        linhas_tabela.append(
            f"<tr><th>{z}</th><td>{n}</td><td>{media}</td><td>{m}</td>"
            f"<td>{c}</td><td>{str(fr) + ' (' + porc(fr, n) + ')' if n else '—'}</td>"
            f"<td>{str(sat) + ' (' + porc(sat, n) + ')' if n else '—'}</td></tr>"
        )
    zona_mais_fria = min((z for z in ZONAS if inteiro(tsv[z]["Respostas"]) > 0),
                          key=lambda z: numero(metclo[z]["TSV médio"]))
    r5_n = inteiro(tsv["R5"]["Respostas"])
    r5_frios = inteiro(tsv["R5"]["Relatos de frio"])
    r5_sat = inteiro(preferencias["R5"]["Satisfeitos"])
    sem_respostas = ", ".join(z for z in ZONAS if inteiro(tsv[z]["Respostas"]) == 0)

    figuras_html = "\n".join(imagem_html(pasta / nome, legenda) for nome, legenda in FIGURAS)
    simulacoes_html = bloco_simulacoes(pasta)
    atualizado = datetime.now().strftime("%d/%m/%Y às %H:%M")

    html = f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Relatório técnico — Conforto térmico multiusuário</title>
<style>
:root {{ color-scheme:light; }}
* {{ box-sizing:border-box; }}
body {{ font-family:Arial,Helvetica,sans-serif; color:#233044; margin:0; background:#f3f5f8; line-height:1.55; }}
main {{ max-width:1080px; margin:32px auto; background:#fff; padding:44px 50px; box-shadow:0 3px 15px #1e293b1a; }}
h1 {{ color:#183b61; font-size:28px; line-height:1.3; margin:0 0 10px; }}
h2 {{ color:#21496b; margin-top:33px; padding-bottom:6px; border-bottom:1px solid #d8e2eb; font-size:20px; }}
p {{ margin:10px 0; }} .sub {{ color:#677381; font-size:14px; }}
.cards {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin:22px 0; }}
.card {{ background:#edf3f7; border:1px solid #dfe7ec; padding:14px; border-radius:8px; }}
.card strong {{ display:block; font-size:26px; color:#193a54; }} .card span {{ font-size:12px; color:#516475; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; margin:16px 0; }}
th,td {{ padding:10px 8px; border-bottom:1px solid #dbe4eb; text-align:center; }}
thead th {{ background:#e9f0f6; color:#233a50; }}
tbody tr:nth-child(even) {{ background:#f8fafb; }}
figure {{ margin:25px 0; break-inside:avoid; border:1px solid #edf0f3; padding:12px; }}
figure img {{ display:block; width:100%; height:auto; max-height:570px; object-fit:contain; }}
figcaption {{ color:#5d6d7b; text-align:center; font-size:12px; margin-top:8px; }}
.nota {{ background:#f3f6f8; padding:14px 17px; border-left:4px solid #547690; }}
.aviso {{ color:#993; }} footer {{ color:#5b6670; margin-top:28px; font-size:12px; }}
@media(max-width:700px) {{ main {{padding:18px;margin:0;}} .cards {{grid-template-columns:repeat(2,1fr);}} table {{font-size:11px;}} }}
@media print {{ body {{background:white;}} main {{margin:0;padding:10mm;box-shadow:none;max-width:none;}} .cards {{grid-template-columns:repeat(4,1fr);}} a {{color:inherit;}} }}
</style></head>
<body><main>
<h1>Análise da percepção de conforto térmico multiusuário</h1>
<p class="sub">Relatório técnico automatizado | Grupo 1 — Instrumentação | UFC Quixadá<br>
Gerado em {escape(atualizado)} | Fonte: resultados agregados das respostas do Grupo 1</p>
<h2>1. Objetivo e referência científica</h2>
<p>Reproduzir parcialmente a metodologia do artigo <em>An investigation of indoor thermal environments and thermal comfort in naturally ventilated educational buildings</em> (de la Hoz-Torres et al., 2024), por meio da análise de questionários de percepção térmica, atividade e vestuário, complementada por simulações computacionais didáticas.</p>
<p>Referência: Journal of Building Engineering, vol. 84, 108677. DOI:
<a href="https://doi.org/10.1016/j.jobe.2024.108677">10.1016/j.jobe.2024.108677</a>.</p>
<h2>2. Metodologia de análise</h2>
<p>Foram processados os questionários coletados pelo Grupo 1 e agrupados por regiões R1–R6 do laboratório. A sensação térmica informada (TSV) é convertida para a escala de −3 (muito frio) a +3 (muito quente). A satisfação e a preferência são mantidas como conceitos distintos. Os valores de met e clo são estimativas obtidas a partir dos mapeamentos presentes nos scripts do grupo.</p>
<p>As análises de questionários são descritivas. Os cálculos de PMV, PPD e ePMV apresentados separadamente na seção 5 utilizam condições ambientais hipotéticas e não constituem validação experimental.</p>
<div class="cards">
<div class="card"><strong>{total}</strong><span>Respostas válidas</span></div>
<div class="card"><strong>{formatar_numero(tsv_medio, 3)}</strong><span>TSV médio geral</span></div>
<div class="card"><strong>{frio} ({porc(frio,total)})</strong><span>Relatos de frio</span></div>
<div class="card"><strong>{satis} ({porc(satis,total)})</strong><span>Satisfeitos</span></div>
</div>
<h2>3. Resultados por região</h2>
<table><thead><tr><th>Zona</th><th>N</th><th>TSV médio</th><th>met médio</th><th>clo médio</th><th>Relatos de frio</th><th>Satisfeitos</th></tr></thead>
<tbody>{''.join(linhas_tabela)}</tbody></table>
<p>met médio estimado (aprox.): <strong>{formatar_numero(met_medio, 3)}</strong>; clo médio estimado (aprox.): <strong>{formatar_numero(clo_medio, 3)}</strong>.</p>
<p>Preferências: <strong>{pref_mantem}</strong> sem mudança; <strong>{pref_fria}</strong> por sala mais fria; <strong>{pref_quente}</strong> por sala mais quente.</p>
<p>Satisfação: <strong>{satis}</strong> satisfeitos; <strong>{insatis}</strong> insatisfeitos; <strong>{neutros}</strong> neutro(s).</p>
<h2>4. Visualizações</h2>
{figuras_html}
{simulacoes_html}
<h2>6. Discussão</h2>
<p>A região <strong>{zona_mais_fria}</strong> apresentou o menor TSV médio dentre as regiões com respostas. Na região R5, <strong>{r5_frios} de {r5_n}</strong> relataram algum nível de frio, enquanto <strong>{r5_sat} de {r5_n}</strong> declararam satisfação. Isso evidencia que a sensação de frio e a satisfação não são a mesma variável.</p>
<p><strong>{divergencia}</strong> respondentes relataram frio (TSV negativo) e, ainda assim, prefeririam uma sala mais fria. Esse cruzamento não permite concluir que as respostas sejam inválidas; pode refletir preferências individuais e diferenças de interpretação.</p>
<p>As zonas <strong>{escape(sem_respostas) if sem_respostas else 'nenhuma'}</strong> não tiveram respostas na amostra analisada. As quantidades por zona diferem, o que exige cautela ao comparar médias e percentuais.</p>
<h2>7. Limitações e próximos passos</h2>
<div class="nota"><p><strong>Não se trata de validação experimental do PMV/ePMV.</strong> Sem medições ambientais (temperatura, umidade, velocidade do ar e temperatura radiante) sincronizadas com os questionários, não é possível comparar índices previstos com a sensação real de cada participante.</p>
<p>Os valores de met/clo utilizam mapeamentos já existentes no projeto e devem ser revisados antes de conclusões normativas. Não há inferência causal nem representatividade estatística garantida para todo o laboratório.</p></div>
<p>Próximas etapas recomendadas: revisar tabelas met/clo; confrontar os registros com medições ambientais de mesma zona e horário, caso existam; e avaliar a possível calibração dos índices com novas observações.</p>
<footer>Relatório gerado automaticamente por <code>gerar_relatorio.py</code> a partir de resultados agregados de questionários e arquivos de simulação didática; os questionários individuais não são incorporados ao HTML.</footer>
</main></body></html>'''
    saida = pasta / "relatorio_integrado.html"
    saida.write_text(html, encoding="utf-8")
    print(f"Relatório gerado com sucesso: {saida}")
    print(f"Respostas: {total} | TSV médio: {tsv_medio:.3f} | Frio: {frio} | Satisfeitos: {satis}")
    print("Abra com: xdg-open resultados/relatorio_integrado.html")
    print("Inclui análises descritivas e simulações hipotéticas; não valida PMV/ePMV.")
    return saida


def main():
    parser = argparse.ArgumentParser(description="Integra os resultados do Grupo 1 em um relatório HTML")
    parser.add_argument("--saida", default="resultados", help="Pasta dos resultados")
    parser.add_argument("--atualizar", action="store_true", help="Executa análises antes de gerar o relatório")
    args = parser.parse_args()
    raiz = Path(__file__).resolve().parent
    pasta = (raiz / args.saida).resolve()
    if args.atualizar:
        if args.saida != "resultados":
            parser.error("A simulação utiliza a pasta resultados/ fixa; use --saida resultados com --atualizar.")
        for nome in SCRIPTS:
            caminho = raiz / nome
            if not caminho.is_file():
                parser.error(f"Script ausente: {caminho}")
            print(f"\nExecutando: {nome}", flush=True)
            comando = [sys.executable, str(caminho)]
            if nome != "simular_conforto.py":
                comando += ["--saida", str(pasta)]
            subprocess.run(comando, cwd=raiz, check=True)
    try:
        gerar_relatorio(pasta)
    except (ValueError, FileNotFoundError) as erro:
        parser.error(str(erro))


if __name__ == "__main__":
    main()
