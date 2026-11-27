# Revisão metodológica — met, clo e ePMV

**Projeto:** Análise e Validação do Conforto Térmico Multiusuário  
**Disciplina:** Instrumentação — Engenharia de Computação, UFC Quixadá  
**Situação:** Revisão documental dos parâmetros e testes computacionais; **não** é validação experimental.

## 1. Objetivo e escopo

Verificar a coerência das estimativas de taxa metabólica (**met**), isolamento das vestimentas (**clo**) e implementações do voto médio previsto estendido (**ePMV**), preservando a rastreabilidade dos 40 questionários do Grupo 1.

A revisão foi realizada a partir de trechos de `analisar_met_clo.py`, `calcular_conforto.py` e `simular_conforto.py`, das saídas de execução fornecidas e de consultas às tabelas disponibilizadas pelo `pythermalcomfort` 4.6.2. Não houve nova coleta ou acesso a medições ambientais sincronizadas aos questionários.

## 2. Taxa metabólica (met)

O Grupo 1 atribuiu valores às atividades declaradas pelos estudantes. Quatro equivalências foram conferidas diretamente na tabela `met_typical_tasks` da biblioteca instalada:

| Atividade registrada no Grupo 1 | Valor adotado (met) | Categoria de referência | Valor da referência (met) | Observação |
|---|---:|---|---:|---|
| Sentado, estudando ou lendo | 1,0 | `Reading, seated` | 1,0 | Correspondência plausível |
| Sentado, utilizando computador | 1,1 | `Typing` | 1,1 | Aproximação: usar computador nem sempre envolve digitar |
| Sentado, escrevendo ou fazendo anotações | 1,0 | `Writing` | 1,0 | Correspondência plausível |
| Em pé, realizando atividade leve | 1,2 | `Standing, relaxed` | 1,2 | Os números coincidem, mas as descrições não são equivalentes em todos os casos |

**Resultado observado:** média de **1,058 met** nas 40 respostas. As outras categorias do mapeamento não foram todas verificadas individualmente nesta revisão.

**Decisão:** manter os valores como **estimativas**, sem classificá-los como metabolismo medido ou normativamente validado. Conferir categorias ambíguas caso sejam feitos novos refinamentos.

## 3. Isolamento das vestimentas (clo)

O script soma os valores atribuídos às peças de roupa declaradas, incluindo peça superior, inferior, camada adicional, meias e calçados.

### 3.1. Comparação de categorias

| Item do Grupo 1 | Valor (clo) | Categoria disponível no `pythermalcomfort` 4.6.2 | Valor (clo) | Interpretação |
|---|---:|---|---:|---|
| Camiseta ou camisa de manga curta | 0,09 | `T-shirt` | 0,08 | Categorias não necessariamente idênticas |
| Camisa de manga longa | 0,15 | `Long sleeve shirt (thin)` | 0,25 | Divergência que exige verificar modelo/material da peça |
| Calça jeans | 0,25 | `Thick trousers` | 0,24 | Valores próximos; categorias aproximadas |
| Bota | 0,10 | `Boots` | 0,10 | Valores coincidentes |

A biblioteca também disponibiliza referências para `Men's underwear` (**0,04 clo**) e `Women's underwear` (**0,03 clo**). Esses itens **não aparecem explicitamente** no mapeamento examinado; isso é uma limitação documentada, não motivo automático para adicionar valores às respostas.

### 3.2. Método de combinação e suas limitações

O Grupo 1 utiliza `clo = soma(clo_das_peças)`. A **ISO 9920:2007** apresenta tanto uma estimativa empírica para conjuntos de vestimentas, `I_cl = 0,161 + 0,835 × Σ I_clu`, quanto uma soma simplificada `I_cl ≈ Σ I_clu`, esta de menor precisão. A escolha depende da definição correta dos valores individuais e de sua correspondência com as peças reais. Não substituir um método pelo outro sem recalcular e justificar o conjunto inteiro.

**Verificação de duplicação:** em 40 questionários, **0** respostas registraram simultaneamente `Casaco ou moletom` como peça superior e como camada adicional. Esse teste detecta apenas essa combinação exata; não elimina outras inconsistências de vestuário.

**Resultado observado:** média de **0,379 clo** nas 40 respostas.

**Decisão:** preservar os mapeamentos atuais para garantir consistência com os resultados existentes. Uma eventual correção exige revisão das categorias originais e nova execução das análises, simulações e relatório.

## 4. Implementações de PMV e ePMV

A função `calcular()` em `calcular_conforto.py` utiliza `pmv_ppd_iso()` e `pmv_e()` da biblioteca **pythermalcomfort 4.6.2**, com velocidade relativa calculada por `v_relative()` e clo dinâmico por `clo_dynamic_iso()`.

### 4.1. Formulação simplificada

`ePMV_simplificado = e × PMV`

### 4.2. Implementação da biblioteca instalada

A inspeção de `inspect.getsource(pmv_e)` confirmou o seguinte procedimento:

1. Calcula inicialmente o PMV.
2. Se o PMV inicial for positivo, ajusta a taxa metabólica: `met_ajustado = met × (1 - 0,067 × PMV_inicial)`.
3. Recalcula o PMV com a taxa metabólica ajustada; nos demais casos, preserva o met.
4. Aplica `e_coefficient` e arredonda o resultado final a duas casas decimais.

Assim, as duas versões **não são necessariamente equivalentes**. A função `pmv_e()` também utiliza o modelo ISO 7730:2025 internamente na versão examinada. O fator `e = 0,80` foi escolhido apenas como **hipótese de demonstração**, sem calibração para o laboratório.

### 4.3. Testes computacionais reproduzidos

Condições: `UR = 50%`, `v_ar = 0,10 m/s`, `Tr = T_ar`, `met = 1,058`, `clo = 0,379`, `e = 0,80`.

| Indicador | Cenário 27 °C | Cenário 29 °C |
|---|---:|---:|
| PMV original | -0,090 | 0,770 |
| PPD | 5,20% | Não verificado neste teste |
| ePMV simplificado (`0,8 × PMV`) | -0,072 | 0,616 |
| ePMV `pmv_e()` do Grupo 1 | -0,070 | 0,540 |
| Diferença absoluta | 0,002 | 0,076 |

**Interpretação:** a 27 °C, o PMV negativo não aciona a correção metabólica e a diferença observada é compatível com o arredondamento. A 29 °C, o PMV positivo aciona o ajuste e a diferença aumenta. Isso demonstra **diferença entre implementações**, e **não** superioridade de precisão ou validade para a sala.

### 4.4. Aplicabilidade dos cenários

Na varredura hipotética de **20 °C a 30 °C**, **8** cenários tiveram resultados aceitos pela implementação, enquanto **20 °C, 21 °C e 22 °C** produziram PMV fora do limite de aplicabilidade usado pela função e foram sinalizados como sem resultado válido. Não interpretar células vazias como zero.

A temperatura radiante foi **assumida igual à do ar** na simulação. No código original, o argumento `te` é rotulado como temperatura externa; passá-lo como `tr` somente é justificável quando a hipótese/proxy está explicitada. Temperatura externa e temperatura radiante média não são, em geral, equivalentes.

## 5. Limitações e decisão metodológica

- Os 40 questionários são dados reais de percepção, mas as entradas ambientais da simulação **não** são medições do laboratório.
- As regiões **R3 e R4** não possuem respostas; as demais regiões têm tamanhos amostrais desiguais.
- Os parâmetros de met e clo são estimados por correspondência de categorias e não medidos diretamente.
- O fator de expectativa não foi estimado com dados do laboratório.
- O ePMV de Fanger e Toftum foi apresentado para edifícios **não climatizados em climas quentes**; seu uso em uma sala com ar-condicionado é exploratório.
- Não foi possível comparar previsões PMV/ePMV e TSV do **mesmo instante** porque faltam medições ambientais sincronizadas.
- O mínimo do PPD simulado próximo de 27 °C **não demonstra** temperatura ideal do laboratório.

**Decisão geral:** manter os códigos, mapeamentos e resultados atuais **sem alterações numéricas**. Utilizá-los na apresentação como análises descritivas e **demonstrações computacionais**; não afirmar validação experimental dos índices.

## 6. Próximas ações

1. Conferir a coerência dos números do relatório HTML e a identificação de cenários hipotéticos.
2. Preparar slides e roteiro, destacando resultados reais, modelos utilizados e limitações.
3. Se houver futuros dados ambientais reais sincronizados, realizar nova etapa de validação quantitativa.

## 7. Referências e materiais consultados

- FANGER, P. O.; TOFTUM, J. **Extension of the PMV model to non-air-conditioned buildings in warm climates**. *Energy and Buildings*, v. 34, n. 6, p. 533–536, 2002. DOI: https://doi.org/10.1016/S0378-7788(02)00003-8
- ISO. **ISO 9920:2007 — Ergonomics of the thermal environment: Estimation of thermal insulation and water vapour resistance of a clothing ensemble**. https://www.iso.org/standard/39257.html
- `pythermalcomfort`, versão **4.6.2**, verificações locais de `met_typical_tasks`, `clo_individual_garments` e fonte da função `pmv_e()`. Documentação: https://pythermalcomfort.readthedocs.io/
- Código do **Grupo 1 — Conforto Térmico Multiusuário e ePMV Adaptativo** e saídas locais dos scripts do repositório individual.
