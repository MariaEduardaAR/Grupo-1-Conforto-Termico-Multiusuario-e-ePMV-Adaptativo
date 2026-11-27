#!/usr/bin/env python3
"""Análise descritiva dos questionários do Grupo 1.

Não calcula PMV/ePMV: faltam medições ambientais sincronizadas.
Uso: python analisar_questionarios.py dados/questionarios.csv
"""

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

ESCALA_TSV = {
    "Muito frio": -3,
    "Frio": -2,
    "Levemente frio": -1,
    "Neutro": 0,
    "Levemente quente": 1,
    "Quente": 2,
    "Muito quente": 3,
}
ZONAS = [f"R{i}" for i in range(1, 7)]
COL_ZONA = "Em qual região da sala você está neste momento?"
COL_TSV = "Como você está se sentindo em relação à temperatura neste momento?"
COL_PREF = "Neste momento, você preferiria que a sala estivesse:"
COL_ATIV = "Qual atividade você realizou predominantemente nos últimos 30 minutos?"
COL_AR = "O movimento do ar está causando algum desconforto?"


def main():
    parser = argparse.ArgumentParser(description="Resumo dos questionários por zona")
    parser.add_argument("arquivo", nargs="?", default="dados/questionarios.csv")
    parser.add_argument("--saida", default="resultados")
    args = parser.parse_args()
    entrada = Path(args.arquivo)
    if not entrada.is_file():
        parser.error(f"Arquivo não encontrado: {entrada}")

    with entrada.open("r", encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f)
        if not leitor.fieldnames:
            parser.error("O CSV não tem cabeçalho")
        faltam = [c for c in (COL_ZONA, COL_TSV, COL_PREF, COL_ATIV, COL_AR)
                  if c not in leitor.fieldnames]
        if faltam:
            parser.error("Colunas ausentes no CSV: " + "; ".join(faltam))
        registros = list(leitor)

    validos = []
    ignorados = 0
    for linha in registros:
        zona = (linha.get(COL_ZONA) or "").strip().upper()
        voto = (linha.get(COL_TSV) or "").strip()
        if zona not in ZONAS or voto not in ESCALA_TSV:
            ignorados += 1
            continue
        validos.append({
            "zona": zona,
            "tsv": ESCALA_TSV[voto],
            "preferencia": (linha.get(COL_PREF) or "").strip(),
            "atividade": (linha.get(COL_ATIV) or "").strip(),
            "ar": (linha.get(COL_AR) or "").strip(),
        })

    if not validos:
        parser.error("Nenhuma resposta com zona e sensação térmica válidas")

    por_zona = defaultdict(list)
    for r in validos:
        por_zona[r["zona"]].append(r)

    pasta = Path(args.saida)
    pasta.mkdir(parents=True, exist_ok=True)
    tabela = pasta / "resumo_por_zona.csv"
    with tabela.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Zona", "Respostas", "TSV médio", "Relatos de frio"])
        for zona in ZONAS:
            obs = por_zona[zona]
            frio = sum(r["tsv"] < 0 for r in obs)
            voto_medio = f"{mean(r['tsv'] for r in obs):.2f}" if obs else ""
            writer.writerow([zona, len(obs), voto_medio, frio])

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 5))
    valores = [mean(r["tsv"] for r in por_zona[z]) if por_zona[z] else 0
               for z in ZONAS]
    barras = ax.bar(ZONAS, valores)
    for zona, barra in zip(ZONAS, barras):
        n = len(por_zona[zona])
        etiqueta = f"n={n}" if n else "sem respostas"
        altura = barra.get_height()
        ax.annotate(etiqueta, (barra.get_x() + barra.get_width() / 2, altura),
                    xytext=(0, -14 if altura < 0 else 5),
                    textcoords="offset points", ha="center",
                    va="bottom" if altura >= 0 else "top", fontsize=9)
    ax.axhline(0, linewidth=0.8)
    ax.set_ylim(-3.2, 1)
    ax.set_ylabel("TSV médio (-3 frio a +3 quente)")
    ax.set_title("Sensação térmica média por região — Grupo 1")
    fig.tight_layout()
    imagem = pasta / "tsv_por_zona.png"
    fig.savefig(imagem, dpi=160)
    plt.close(fig)

    preferencias = Counter(r["preferencia"] for r in validos)
    print(f"\nRespostas analisadas: {len(validos)}")
    print(f"Respostas ignoradas por zona ou TSV inválido: {ignorados}")
    print(f"TSV médio geral: {mean(r['tsv'] for r in validos):.3f}")
    print(f"Relatos de frio (TSV < 0): {sum(r['tsv'] < 0 for r in validos)}")
    print("Preferência térmica:", dict(preferencias))
    print("\nZona | Respostas | TSV médio | Relatos de frio")
    for z in ZONAS:
        obs = por_zona[z]
        if obs:
            print(f"{z:>4} | {len(obs):>9} | {mean(r['tsv'] for r in obs):>9.2f} | {sum(r['tsv']<0 for r in obs):>15}")
        else:
            print(f"{z:>4} | {0:>9} | {'—':>9} | {'—':>15}")
    print(f"\nArquivos gerados: {tabela}, {imagem}")
    print("Observação: análise descritiva. Os resultados não representam PMV/ePMV nem validação ambiental.")

if __name__ == "__main__":
    main()
