#!/usr/bin/env python3
"""Simulação DIDÁTICA de PMV, PPD e ePMV a partir de perfis agregados do Grupo 1.

Não usa medições ambientais reais e não valida PMV/ePMV contra TSV.
Entrada: resultados/resumo_met_clo_por_zona.csv (criado por analisar_met_clo.py).
Reaproveita a função calcular() de calcular_conforto.py, sem gravar no InfluxDB.

Execução:
    python analisar_met_clo.py
    python simular_conforto.py
"""

import csv
import json
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # funciona no terminal sem abrir janela de gráficos
import matplotlib.pyplot as plt

from calcular_conforto import calcular

ENTRADA = Path("resultados/resumo_met_clo_por_zona.csv")
SAIDA = Path("resultados/simulacoes")

# Hipóteses DIDÁTICAS: não são medições da sala.
UMIDADE_HIPOTETICA = 50.0  # %
VELOCIDADE_HIPOTETICA = 0.10  # m/s
EXPECTATIVA_HIPOTETICA = 0.80  # exemplo, NÃO calibrado para sala climatizada
TEMP_MIN, TEMP_MAX = 20, 30  # °C
TEMP_COMPARACAO_ZONAS = 25.0  # °C, igual em TODAS as zonas hipotéticas


def ler_zonas(caminho):
    if not caminho.is_file():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}. Execute primeiro: python analisar_met_clo.py"
        )
    zonas = []
    with caminho.open("r", encoding="utf-8-sig", newline="") as arq:
        for linha in csv.DictReader(arq):
            n = int(linha["Respostas"])
            if n == 0:
                continue  # R3 e R4 sem respostas NÃO são consideradas neutras
            zonas.append({
                "zona": linha["Zona"].strip(),
                "n": n,
                "met": float(linha["met médio"].replace(",", ".")),
                "clo": float(linha["clo médio"].replace(",", ".")),
            })
    if not zonas:
        raise ValueError("O resumo não contém zonas com respostas.")
    return zonas


def media_ponderada(zonas, nome):
    total = sum(z["n"] for z in zonas)
    return sum(z[nome] * z["n"] for z in zonas) / total


def calcular_cenario(temperatura, met, clo):
    # ATENÇÃO: no script original, o parâmetro 'te' é chamado temperatura externa.
    # Aqui passamos te=temperatura apenas para representar a hipótese Tr = T_ar.
    # Essa variável NÃO corresponde a uma medição externa ou radiante.
    # O script do Grupo 1 levanta ValueError se o modelo ISO retornar NaN.
    # Aqui o aviso de aplicabilidade é tratado em rodar_cenario(), sem ocultar
    # o problema. Não interpretar resultados fora do domínio como zero.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", message=r".*outside the applicability limits.*", category=UserWarning
        )
        resultado = calcular(
            ta=float(temperatura),
            rh=UMIDADE_HIPOTETICA,
            te=float(temperatura),
            met=float(met),
            clo=float(clo),
            v=VELOCIDADE_HIPOTETICA,
            e=EXPECTATIVA_HIPOTETICA,
        )
    pmv = resultado["pmv"]
    return {
        "pmv": pmv,
        "ppd": resultado["ppd"],
        # Equação simplificada usada no artigo: ePMV = e * PMV.
        "epmv_artigo": EXPECTATIVA_HIPOTETICA * pmv,
        # Calculado pela função pmv_e() usada pelo Grupo 1.
        # Pode não coincidir numericamente com a expressão simplificada.
        "epmv_grupo1": resultado["epmv"],
    }


def rodar_cenario(temperatura, met, clo):
    """Calcula o cenário ou marca explicitamente a falta de aplicabilidade.

    Não ignora erros inesperados de programação ou de entrada.
    """
    try:
        resultados = calcular_cenario(temperatura, met, clo)
        return resultados, "calculado", ""
    except ValueError as erro:
        mensagem = str(erro)
        limites = (
            "fora dos limites do modelo" in mensagem
            or "ePMV fora dos limites" in mensagem
        )
        if not limites:
            raise
        sem_valores = {
            "pmv": None,
            "ppd": None,
            "epmv_artigo": None,
            "epmv_grupo1": None,
        }
        return sem_valores, "fora_dos_limites", mensagem


def valor_grafico(valor):
    """O NaN cria uma lacuna nos gráficos, nunca uma barra de valor zero."""
    return float(valor) if valor is not None else float("nan")


def escrever_csv(caminho, linhas, colunas):
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(linhas)


def grafico_temperatura(linhas):
    temp = [r["temperatura_hipotetica_C"] for r in linhas]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(temp, [valor_grafico(r["pmv"]) for r in linhas], marker="o", label="PMV")
    ax.plot(temp, [valor_grafico(r["epmv_artigo"]) for r in linhas], marker="s",
            label="ePMV simplificado (e × PMV)")
    ax.plot(temp, [valor_grafico(r["epmv_grupo1"]) for r in linhas], marker="^",
            label="ePMV do script do Grupo 1")
    invalidos = [str(r["temperatura_hipotetica_C"]) for r in linhas
                if r["situacao"] != "calculado"]
    if invalidos:
        ax.text(0.02, 0.02, "Sem cálculo dentro dos limites: " + ", ".join(invalidos) + " °C",
                fontsize=8, transform=ax.transAxes)
    ax.axhline(0, linewidth=1, linestyle=":", label="Sensação neutra (0)")
    ax.set_title("Simulação: índices previstos × temperatura do ar")
    ax.set_xlabel("Temperatura hipotética do ar (°C) | Tr assumida igual a T_ar")
    ax.set_ylabel("Índice de sensação térmica previsto")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(SAIDA / "pmv_epmv_por_temperatura.png", dpi=160)
    plt.close(fig)


def grafico_ppd(linhas):
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot([r["temperatura_hipotetica_C"] for r in linhas],
            [valor_grafico(r["ppd"]) for r in linhas], marker="o")
    ax.set_title("Simulação: PPD do modelo PMV × temperatura")
    ax.set_xlabel("Temperatura hipotética do ar (°C)")
    ax.set_ylabel("PPD previsto (%)")
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.25)
    invalidos = [str(r["temperatura_hipotetica_C"]) for r in linhas
                if r["situacao"] != "calculado"]
    if invalidos:
        ax.text(0.02, 0.02, "Sem cálculo dentro dos limites: " + ", ".join(invalidos) + " °C",
                fontsize=8, transform=ax.transAxes)
    fig.tight_layout()
    fig.savefig(SAIDA / "ppd_por_temperatura.png", dpi=160)
    plt.close(fig)


def grafico_zonas(linhas):
    fig, ax = plt.subplots(figsize=(9, 5))
    indices = list(range(len(linhas)))
    largura = 0.26
    ax.bar([x - largura for x in indices], [valor_grafico(r["pmv"]) for r in linhas],
           width=largura, label="PMV")
    ax.bar(indices, [valor_grafico(r["epmv_artigo"]) for r in linhas],
           width=largura, label="ePMV simplificado (artigo)")
    ax.bar([x + largura for x in indices], [valor_grafico(r["epmv_grupo1"]) for r in linhas],
           width=largura, label="ePMV do Grupo 1")
    ax.set_xticks(indices, [r["zona"] for r in linhas])
    for indice, linha in enumerate(linhas):
        if linha["situacao"] != "calculado":
            ax.annotate("sem cálculo", (indice, 0), xytext=(0, 8),
                        textcoords="offset points", ha="center", fontsize=8)
    ax.set_ylabel("Índice de sensação térmica previsto")
    ax.set_title("Cenários hipotéticos por zona: mesma temperatura de 25 °C")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(SAIDA / "indices_por_zona_simulados.png", dpi=160)
    plt.close(fig)


def main():
    zonas = ler_zonas(ENTRADA)
    SAIDA.mkdir(parents=True, exist_ok=True)
    met_geral = media_ponderada(zonas, "met")
    clo_geral = media_ponderada(zonas, "clo")

    por_temperatura = []
    for temperatura in range(TEMP_MIN, TEMP_MAX + 1):
        resultados, situacao, observacao = rodar_cenario(temperatura, met_geral, clo_geral)
        por_temperatura.append({
            "temperatura_hipotetica_C": temperatura,
            "met_medio_estimado": round(met_geral, 3),
            "clo_medio_estimado": round(clo_geral, 3),
            **resultados,
            "situacao": situacao,
            "observacao": observacao,
        })

    por_zona = []
    for z in zonas:
        resultados, situacao, observacao = rodar_cenario(
            TEMP_COMPARACAO_ZONAS, z["met"], z["clo"]
        )
        por_zona.append({
            "zona": z["zona"],
            "respostas": z["n"],
            "temperatura_hipotetica_C": TEMP_COMPARACAO_ZONAS,
            "met_medio_estimado": z["met"],
            "clo_medio_estimado": z["clo"],
            **resultados,
            "situacao": situacao,
            "observacao": observacao,
        })

    escrever_csv(
        SAIDA / "simulacao_por_temperatura.csv", por_temperatura,
        ["temperatura_hipotetica_C", "met_medio_estimado", "clo_medio_estimado",
         "pmv", "ppd", "epmv_artigo", "epmv_grupo1", "situacao", "observacao"],
    )
    escrever_csv(
        SAIDA / "simulacao_por_zona.csv", por_zona,
        ["zona", "respostas", "temperatura_hipotetica_C",
         "met_medio_estimado", "clo_medio_estimado", "pmv", "ppd",
         "epmv_artigo", "epmv_grupo1", "situacao", "observacao"],
    )
    grafico_temperatura(por_temperatura)
    grafico_ppd(por_temperatura)
    grafico_zonas(por_zona)

    premissas = {
        "classificacao": "SIMULACAO DIDATICA — NAO E MEDICAO DA SALA",
        "temperatura_radiante": "Tr assumida igual a temperatura do ar",
        "umidade_hipotetica_pct": UMIDADE_HIPOTETICA,
        "velocidade_hipotetica_m_s": VELOCIDADE_HIPOTETICA,
        "coeficiente_expectativa_hipotetico": EXPECTATIVA_HIPOTETICA,
        "met_e_clo": "medias estimadas dos questionarios, arredondadas por zona",
        "limite": "nao comparar com TSV real sem dados ambientais simultaneos",
        "alerta": "ePMV exploratorio para laboratorio com ar-condicionado",
        "comparacao": "ePMV simplificado e x PMV versus pmv_e do script original",
        "faixa_de_aplicabilidade": "Valores fora dos limites de aplicabilidade do PMV ISO/pmv_e são omitidos, nunca zerados.",
    }
    (SAIDA / "premissas.json").write_text(
        json.dumps(premissas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("\nSIMULAÇÃO DIDÁTICA CONCLUÍDA — dados ambientais HIPOTÉTICOS")
    print(f"Perfis com respostas: {', '.join(z['zona'] for z in zonas)}")
    print(f"Met médio aproximado: {met_geral:.3f} | Clo médio aproximado: {clo_geral:.3f}")
    print(f"Hipóteses: UR={UMIDADE_HIPOTETICA:.0f}%, ar={VELOCIDADE_HIPOTETICA:.2f} m/s, "
          f"Tr=T_ar, e={EXPECTATIVA_HIPOTETICA:.2f}")
    invalidos_temp = [r["temperatura_hipotetica_C"] for r in por_temperatura
                     if r["situacao"] != "calculado"]
    invalidos_zona = [r["zona"] for r in por_zona if r["situacao"] != "calculado"]
    print(f"Cenários por temperatura: {len(por_temperatura) - len(invalidos_temp)} válidos, "
          f"{len(invalidos_temp)} fora dos limites do modelo.")
    if invalidos_temp:
        print("  Temperaturas sem cálculo (°C): " + ", ".join(map(str, invalidos_temp)))
    if invalidos_zona:
        print("  Zonas sem cálculo para 25 °C: " + ", ".join(invalidos_zona))
    print("  Células vazias nos CSVs e lacunas nos gráficos NÃO significam valor zero.")
    print(f"\nArquivos gerados em: {SAIDA}/")
    print("- simulacao_por_temperatura.csv")
    print("- simulacao_por_zona.csv")
    print("- pmv_epmv_por_temperatura.png")
    print("- ppd_por_temperatura.png")
    print("- indices_por_zona_simulados.png")
    print("- premissas.json")
    print("\nIMPORTANTE: Não são resultados ambientais reais nem validação PMV/ePMV.")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, ImportError) as exc:
        raise SystemExit(f"Não foi possível concluir: {exc}")
