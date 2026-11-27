#!/usr/bin/env python3
"""Analisa met/clo e percepção térmica das respostas do Grupo 1.

Reproduz os mapeamentos do script de ingestão do repositório da equipe.
Os valores são estimativas e precisam de revisão metodológica antes de
serem apresentados como valores normativos definitivos.

Uso:
    python analisar_met_clo.py
    python analisar_met_clo.py dados/questionarios.csv
"""

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

ZONAS = [f"R{x}" for x in range(1, 7)]
TSV = {
    "Muito frio": -3, "Frio": -2, "Levemente frio": -1,
    "Neutro": 0, "Levemente quente": 1, "Quente": 2, "Muito quente": 3,
}

# Fonte: Setup_InfluxDB_Schedules-API/ingestao_automatizada.py
# (mapeamentos do Grupo 1; nao equivalem a validacao normativa)
MAP_MET = {
    "Sentado, estudando ou lendo": 1.0,
    "Sentado, utilizando computador": 1.1,
    "Sentado, assistindo aula": 1.0,
    "Sentado, conversando": 1.1,
    "Em pé, realizando atividade leve": 1.2,
    "Sentado, escrevendo ou fazendo anotações": 1.0,
    "Sentado, conversando e usando o computador": 1.1,
}
MAP_SUP = {
    "Regata": 0.08, "Camiseta ou camisa de manga curta": 0.09,
    "Camisa longa de manga curta": 0.09,
    "Camisa longa com manga curta": 0.09,
    "camisa polo": 0.09, "Camisa de manga longa": 0.15,
    "Camisa oversize": 0.10, "Casaco ou moletom": 0.35,
}
MAP_INF = {
    "Short": 0.06, "Bermuda": 0.11, "Calça leve": 0.15,
    "Calça de tecido médio": 0.20, "Calça tecido médio": 0.20,
    "Calça de tecido pesado": 0.25, "Calça jeans": 0.25,
}
MAP_ADD = {"Jaqueta": 0.36, "Casaco ou moletom": 0.35, "Não": 0.0}
MAP_MEIAS = {"Não": 0.0, "Sim, meias curtas": 0.02, "Sim, meias longas": 0.03}
MAP_CALC = {
    "Sandália ou chinelo": 0.02, "Tênis": 0.04,
    "Sapato fechado": 0.04, "Bota": 0.10,
}

COL = {
    "zona": "Em qual região da sala você está neste momento?",
    "atividade": "Qual atividade você realizou predominantemente nos últimos 30 minutos?",
    "sup": "Qual peça você utiliza na parte superior do corpo?",
    "inf": "Qual peça você utiliza na parte inferior do corpo?",
    "add": "Você está utilizando alguma camada adicional sobre a peça principal da parte superior?",
    "meias": "Você está utilizando meias?",
    "calc": "Qual tipo de calçado você está utilizando?",
    "tsv": "Como você está se sentindo em relação à temperatura neste momento?",
}


def converter(mapa, valor, tipo, indice):
    chave = (valor or "").strip()
    if chave not in mapa:
        raise ValueError(f"Linha {indice}: {tipo} não mapeado: {chave!r}")
    return mapa[chave]


def main():
    p = argparse.ArgumentParser(description="Análise de met, clo e TSV dos questionários")
    p.add_argument("arquivo", nargs="?", default="dados/questionarios.csv")
    p.add_argument("--saida", default="resultados")
    a = p.parse_args()
    origem = Path(a.arquivo)
    if not origem.is_file():
        p.error(f"Arquivo não encontrado: {origem}")

    with origem.open("r", encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f)
        faltantes = [titulo for titulo in COL.values() if titulo not in (leitor.fieldnames or [])]
        if faltantes:
            p.error("Colunas ausentes no CSV: " + "; ".join(faltantes))
        linhas = list(leitor)

    dados = []
    for i, linha in enumerate(linhas, 2):
        zona = (linha[COL["zona"]] or "").strip().upper()
        voto = (linha[COL["tsv"]] or "").strip()
        if zona not in ZONAS or voto not in TSV:
            raise ValueError(f"Linha {i}: zona ou TSV inválido ({zona}, {voto!r})")
        met = converter(MAP_MET, linha[COL["atividade"]], "atividade", i)
        clo = sum([
            converter(MAP_SUP, linha[COL["sup"]], "roupa superior", i),
            converter(MAP_INF, linha[COL["inf"]], "roupa inferior", i),
            converter(MAP_ADD, linha[COL["add"]], "camada adicional", i),
            converter(MAP_MEIAS, linha[COL["meias"]], "meias", i),
            converter(MAP_CALC, linha[COL["calc"]], "calçado", i),
        ])
        dados.append({"zona": zona, "met": met, "clo": round(clo, 3), "tsv": TSV[voto]})

    if not dados:
        p.error("Nenhuma resposta válida")

    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    grupos = defaultdict(list)
    for d in dados:
        grupos[d["zona"]].append(d)

    arq_csv = saida / "resumo_met_clo_por_zona.csv"
    with arq_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Zona", "Respostas", "met médio", "clo médio", "TSV médio"])
        for z in ZONAS:
            regs = grupos[z]
            w.writerow([z, len(regs),
                        f"{mean(x['met'] for x in regs):.3f}" if regs else "",
                        f"{mean(x['clo'] for x in regs):.3f}" if regs else "",
                        f"{mean(x['tsv'] for x in regs):.3f}" if regs else ""])

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Cada ponto é uma resposta anônima; sobreposição é esperada para categorias iguais.
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter([x["clo"] for x in dados], [x["tsv"] for x in dados], alpha=0.55)
    ax.set_xlabel("Isolamento estimado das roupas (clo)")
    ax.set_ylabel("Sensação térmica informada (TSV)")
    ax.set_yticks(range(-3, 4))
    ax.set_ylim(-3.3, 3.3)
    ax.set_title("Relação entre clo estimado e TSV — Grupo 1")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    arq_fig = saida / "clo_versus_tsv.png"
    fig.savefig(arq_fig, dpi=160)
    plt.close(fig)

    print(f"\nRespostas analisadas: {len(dados)}")
    print(f"met médio geral: {mean(x['met'] for x in dados):.3f}")
    print(f"clo médio geral: {mean(x['clo'] for x in dados):.3f}")
    print("Atividades (met):", dict(sorted(Counter(x["met"] for x in dados).items())))
    print("\nZona | N | met médio | clo médio | TSV médio")
    for z in ZONAS:
        regs = grupos[z]
        if regs:
            print(f"{z:>4} | {len(regs):>2} | {mean(x['met'] for x in regs):>9.3f} | "
                  f"{mean(x['clo'] for x in regs):>9.3f} | {mean(x['tsv'] for x in regs):>9.3f}")
        else:
            print(f"{z:>4} |  0 |         — |         — |         —")
    print(f"\nArquivos gerados: {arq_csv}, {arq_fig}")
    print("Importante: são estimativas usando os mapeamentos do Grupo 1, não PMV/ePMV.")
    print("Não há inferência de causalidade ou validação ambiental neste relatório.")


if __name__ == "__main__":
    main()
