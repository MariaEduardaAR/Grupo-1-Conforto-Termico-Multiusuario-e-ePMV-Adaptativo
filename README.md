# Grupo 1 — Caracterização de Ocupação e Conforto Térmico

Repositório do **Grupo 1** do projeto de conforto térmico do Laboratório de Arquitetura de Computadores — Bloco 4, **UFC Campus Quixadá**.

## Sobre o projeto

O Grupo 1 é responsável pela caracterização da ocupação do ambiente, considerando a divisão espacial em **seis zonas (R1–R6)** e diferentes períodos de ocupação.

A partir dos questionários aplicados aos ocupantes, são obtidos e organizados:

* **Taxa metabólica (`met`)**
* **Isolamento térmico das vestimentas (`clo`)**
* **Schedules de ocupação**
* Distribuição espacial e temporal dos ocupantes
* Percepção e preferência térmica

Os dados são organizados para posterior utilização na **modelagem e simulação computacional** realizada pelo Grupo 2.

## Estrutura

```text
├── Grupo1_Schedules_met_clo_ASHRAE55.xlsx
├── Relatório.pdf
└── README.md
```

## Zonas

O laboratório foi dividido em seis regiões:

```text
R1 | R2
---+---
R3 | R4
---+---
R5 | R6
```

## Coleta

Os questionários foram aplicados entre **28/09/2026 e 01/10/2026**, totalizando **40 respostas válidas**.

As respostas são agrupadas nas seguintes faixas:

* **Manhã — 10h**
* **Tarde 1 — 13:30**
* **Tarde 2 — 15:30**

A classificação considera o horário real de envio das respostas.

## Dados para simulação

O principal produto do Grupo 1 é o **schedule de ocupação**, contendo os valores de `met` e `clo` associados às diferentes zonas e períodos.

Esses dados serão integrados posteriormente às variáveis ambientais obtidas na etapa de simulação para a avaliação de conforto térmico e cálculo do **ePMV**, conforme a metodologia definida no projeto.

## Referências

* **ANSI/ASHRAE Standard 55-2023 — Thermal Environmental Conditions for Human Occupancy**
* Dados e conversões utilizados no projeto.

## Equipe

* Davi Medeiros
* Maria Eduarda
* Nathalia Lima
* Pablo Brandão

**Universidade Federal do Ceará — Campus Quixadá**
**Engenharia de Computação — 2026**
