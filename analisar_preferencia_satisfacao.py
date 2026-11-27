#!/usr/bin/env python3
"""Análise descritiva de preferência, satisfação e sensação térmica (TSV).

Dados: questionários do Grupo 1, UFC Quixadá.
Não calcula PMV/ePMV nem faz validação de medições ambientais.
Não exporta dados pessoais: gera somente agregações por zona e categorias.

Uso:
    python analisar_preferencia_satisfacao.py
    python analisar_preferencia_satisfacao.py dados/questionarios.csv
    python analisar_preferencia_satisfacao.py --saida resultados
"""

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

ZONAS = [f"R{i}" for i in range(1, 7)]
TSV = {"Muito frio": -3, "Frio": -2, "Levemente frio": -1,
       "Neutro": 0, "Levemente quente": 1, "Quente": 2, "Muito quente": 3}
PREFERENCIAS = ["Mais quente", "Sem mudança", "Mais fria"]
SATISFACAO = {
    "Muito insatisfeito": -3,
    "Insatisfeito": -2,
    "Levemente insatisfeito": -1,
    "Neutro": 0,
    "Levemente satisfeito": 1,
    "Satisfeito": 2,
    "Muito satisfeito": 3,
}
CLASSES_SAT = ["Insatisfeito", "Neutro", "Satisfeito"]
COL_ZONA = "Em qual região da sala você está neste momento?"
COL_TSV = "Como você está se sentindo em relação à temperatura neste momento?"
COL_PREF = "Neste momento, você preferiria que a sala estivesse:"
COL_SAT = "O quão satisfeito você está com as condições térmicas da sala neste momento?"


def ler_respostas(caminho):
    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        ausentes = [col for col in [COL_ZONA, COL_TSV, COL_PREF, COL_SAT]
                    if col not in (leitor.fieldnames or [])]
        if ausentes:
            raise ValueError("Colunas ausentes no arquivo: " + "; ".join(ausentes))
        validos, invalidos = [], []
        for numero, linha in enumerate(leitor, start=2):
            zona = (linha[COL_ZONA] or "").strip().upper()
            voto = (linha[COL_TSV] or "").strip()
            pref = (linha[COL_PREF] or "").strip()
            sat = (linha[COL_SAT] or "").strip()
            erros = []
            if zona not in ZONAS: erros.append("zona")
            if voto not in TSV: erros.append("TSV")
            if pref not in PREFERENCIAS: erros.append("preferência")
            if sat not in SATISFACAO: erros.append("satisfação")
            if erros:
                invalidos.append((numero, ", ".join(erros)))
                continue
            valor_sat = SATISFACAO[sat]
            classe_sat = "Satisfeito" if valor_sat > 0 else "Insatisfeito" if valor_sat < 0 else "Neutro"
            validos.append({"zona": zona, "tsv": TSV[voto], "preferencia": pref,
                            "satisfacao": valor_sat, "classe_sat": classe_sat})
    return validos, invalidos


def main():
    parser = argparse.ArgumentParser(description="Análise de preferência e satisfação térmica por zona")
    parser.add_argument("arquivo", nargs="?", default="dados/questionarios.csv")
    parser.add_argument("--saida", default="resultados", help="Pasta dos resultados agregados")
    args = parser.parse_args()
    arquivo = Path(args.arquivo)
    if not arquivo.is_file():
        parser.error(f"Arquivo não encontrado: {arquivo}")
    try:
        dados, invalidos = ler_respostas(arquivo)
    except ValueError as erro:
        parser.error(str(erro))
    if invalidos:
        for linha, campos in invalidos:
            print(f"Aviso: linha {linha} ignorada (valor inválido em {campos})")
    if not dados:
        parser.error("Não foram encontradas respostas válidas")

    por_zona = defaultdict(list)
    for registro in dados:
        por_zona[registro["zona"]].append(registro)

    pasta = Path(args.saida)
    pasta.mkdir(parents=True, exist_ok=True)

    # Somente agregados, sem linhas individuais e sem respostas em texto livre.
    resumo = pasta / "resumo_preferencia_satisfacao_por_zona.csv"
    with resumo.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Zona", "Respostas", "Prefere mais quente", "Prefere sem mudança",
                    "Prefere mais fria", "Insatisfeitos", "Neutros", "Satisfeitos",
                    "Satisfação média (-3 a +3)"])
        for zona in ZONAS:
            regs = por_zona[zona]
            preferencias = Counter(r["preferencia"] for r in regs)
            satisfacoes = Counter(r["classe_sat"] for r in regs)
            media = (f"{sum(r['satisfacao'] for r in regs) / len(regs):.3f}" if regs else "")
            w.writerow([zona, len(regs), preferencias["Mais quente"],
                        preferencias["Sem mudança"], preferencias["Mais fria"],
                        satisfacoes["Insatisfeito"], satisfacoes["Neutro"],
                        satisfacoes["Satisfeito"], media])

    cruzamento = pasta / "tsv_versus_preferencia.csv"
    contagem_tsv_pref = Counter((r["tsv"], r["preferencia"]) for r in dados)
    with cruzamento.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["TSV", *PREFERENCIAS, "Total"])
        for tsv in range(-3, 4):
            valores = [contagem_tsv_pref[(tsv, p)] for p in PREFERENCIAS]
            w.writerow([tsv, *valores, sum(valores)])

    import matplotlib
    matplotlib.use("Agg")  # Gera arquivos mesmo sem interface gráfica.
    import matplotlib.pyplot as plt

    # Preferências por zona, em contagens para deixar visível a amostra desigual.
    fig, ax = plt.subplots(figsize=(10, 5.5))
    largura = 0.24
    posicoes = list(range(len(ZONAS)))
    for idx, pref in enumerate(PREFERENCIAS):
        valores = [sum(r["preferencia"] == pref for r in por_zona[z]) for z in ZONAS]
        ax.bar([p + (idx - 1) * largura for p in posicoes], valores,
               width=largura, label=pref)
    ax.set_xticks(posicoes, [f"{z}\n(n={len(por_zona[z])})" for z in ZONAS])
    ax.set_ylabel("Número de respostas")
    ax.set_title("Preferência térmica dos estudantes por região")
    ax.legend()
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    imagem_pref = pasta / "preferencia_por_zona.png"
    fig.savefig(imagem_pref, dpi=160)
    plt.close(fig)

    # Satisfação em três classes, mantendo o significado original do questionário.
    fig, ax = plt.subplots(figsize=(10, 5.5))
    base = [0] * len(ZONAS)
    for classe in CLASSES_SAT:
        valores = [sum(r["classe_sat"] == classe for r in por_zona[z]) for z in ZONAS]
        ax.bar(ZONAS, valores, bottom=base, label=classe)
        base = [x + y for x, y in zip(base, valores)]
    for z, n in zip(ZONAS, base):
        ax.annotate("sem respostas" if n == 0 else f"n={n}",
                    (z, n), xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=9)
    ax.set_ylabel("Número de respostas")
    ax.set_ylim(top=max(base) + 4)
    ax.set_title("Satisfação térmica por região")
    ax.legend()
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    imagem_sat = pasta / "satisfacao_por_zona.png"
    fig.savefig(imagem_sat, dpi=160)
    plt.close(fig)

    # Matriz para identificar divergências sem supor erro na resposta.
    matriz = [[contagem_tsv_pref[(tsv, p)] for p in PREFERENCIAS]
              for tsv in range(-3, 4)]
    fig, ax = plt.subplots(figsize=(8, 6))
    m = ax.imshow(matriz, aspect="auto")
    ax.set_xticks(range(len(PREFERENCIAS)), PREFERENCIAS)
    ax.set_yticks(range(7), [str(x) for x in range(-3, 4)])
    ax.set_xlabel("Preferência térmica")
    ax.set_ylabel("TSV informado")
    ax.set_title("TSV × preferência térmica (número de respostas)")
    for i, linha in enumerate(matriz):
        for j, numero in enumerate(linha):
            rgba = m.cmap(m.norm(numero))
            luminancia = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
            ax.text(j, i, str(numero), ha="center", va="center",
                    color="black" if luminancia > 0.55 else "white")
    fig.colorbar(m, ax=ax, label="Respostas")
    fig.tight_layout()
    imagem_cruz = pasta / "tsv_versus_preferencia.png"
    fig.savefig(imagem_cruz, dpi=160)
    plt.close(fig)

    pref_totais = Counter(r["preferencia"] for r in dados)
    sat_totais = Counter(r["classe_sat"] for r in dados)
    divergencias = sum(r["tsv"] < 0 and r["preferencia"] == "Mais fria" for r in dados)
    print(f"\nRespostas analisadas: {len(dados)}")
    print(f"Respostas ignoradas: {len(invalidos)}")
    print("Preferência térmica geral:", dict(pref_totais))
    print("Satisfação térmica geral:", dict(sat_totais))
    print(f"Relatos de frio com preferência por sala mais fria: {divergencias}")
    print("\nZona | N | Mais quente | Sem mudança | Mais fria | Insatisfeitos | Neutros | Satisfeitos")
    for zona in ZONAS:
        regs = por_zona[zona]
        p = Counter(r["preferencia"] for r in regs)
        s = Counter(r["classe_sat"] for r in regs)
        print(f"{zona:>4} | {len(regs):>2} | {p['Mais quente']:>11} | {p['Sem mudança']:>11} | "
              f"{p['Mais fria']:>9} | {s['Insatisfeito']:>13} | {s['Neutro']:>7} | {s['Satisfeito']:>10}")
    print("\nArquivos gerados:")
    for item in [resumo, cruzamento, imagem_pref, imagem_sat, imagem_cruz]:
        print(f"- {item}")
    print("Observação: estudo descritivo das respostas, sem validação ambiental nem PMV/ePMV.")


if __name__ == "__main__":
    main()
