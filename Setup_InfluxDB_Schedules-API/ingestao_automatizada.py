import pandas as pd
import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime
import pytz

# --- 1. CONFIGURAÇÕES DO BANCO DE DADOS ---
URL = "http://localhost:8086"
TOKEN = "token-api-grupo1-2026"
ORG = "ufc_quixada"
BUCKET = "instrumentacao_2026"

# --- 2. MAPEAMENTO ASHRAE 55 ---
map_met = {
    'Sentado, estudando ou lendo': 1.0, 'Sentado, utilizando computador': 1.1,
    'Sentado, assistindo aula': 1.0, 'Sentado, conversando': 1.1,
    'Em pé, realizando atividade leve': 1.2, 'Sentado, escrevendo ou fazendo anotações': 1.0,
    'Sentado, conversando e usando o computador': 1.1
}

map_clo_sup = {
    'Regata': 0.08, 'Camiseta ou camisa de manga curta': 0.09, 'Camisa longa de manga curta': 0.09,
    'Camisa longa com manga curta': 0.09, 'camisa polo': 0.09, 'Camisa de manga longa': 0.15,
    'Camisa oversize': 0.10, 'Casaco ou moletom': 0.35
}

map_clo_inf = {
    'Short': 0.06, 'Bermuda': 0.11, 'Calça leve': 0.15, 
    'Calça de tecido médio': 0.20, 'Calça tecido médio ': 0.20,
    'Calça de tecido pesado': 0.25, 'Calça jeans': 0.25
}

map_clo_add = {'Jaqueta': 0.36, 'Casaco ou moletom': 0.35, 'Não': 0.0}
map_clo_meias = {'Não': 0.0, 'Sim, meias curtas': 0.02, 'Sim, meias longas': 0.03}
map_clo_calcado = {'Sandália ou chinelo': 0.02, 'Tênis': 0.04, 'Sapato fechado': 0.04, 'Bota ': 0.10, 'Bota': 0.10}

# --- 3. PROCESSAMENTO DOS DADOS ---
# Usando o arquivo CSV que já está na sua pasta
df = pd.read_csv("Questionário de Percepção Térmica — Salas de Aula UFC Quixadá.csv")

# Tratando a data para remover o 'GMT-3' e converter para formato temporal
df['Carimbo de data/hora'] = df['Carimbo de data/hora'].str.replace(' GMT-3', '')
df['Timestamp'] = pd.to_datetime(df['Carimbo de data/hora'], format='%Y/%m/%d %I:%M:%S %p')
df['Data'] = df['Timestamp'].dt.date
df['Hora'] = df['Timestamp'].dt.hour 

# Mapeamento
df['Met_Calc'] = df['Qual atividade você realizou predominantemente nos últimos 30 minutos?'].map(map_met).fillna(1.0)
df['Clo_Calc'] = (
    df['Qual peça você utiliza na parte superior do corpo?'].map(map_clo_sup).fillna(0.09) +
    df['Qual peça você utiliza na parte inferior do corpo?'].map(map_clo_inf).fillna(0.15) +
    df['Você está utilizando alguma camada adicional sobre a peça principal da parte superior?'].map(map_clo_add).fillna(0.0) +
    df['Você está utilizando meias?'].map(map_clo_meias).fillna(0.0) +
    df['Qual tipo de calçado você está utilizando?'].map(map_clo_calcado).fillna(0.04)
)

col_zona = 'Em qual região da sala você está neste momento?'
df_grouped = df.groupby([col_zona, 'Data', 'Hora']).agg(
    met_medio=('Met_Calc', 'mean'),
    clo_medio=('Clo_Calc', 'mean'),
    ocupacao=('Carimbo de data/hora', 'count')
).reset_index()

# --- 4. INJEÇÃO NO INFLUXDB ---
client = influxdb_client.InfluxDBClient(url=URL, token=TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

for _, row in df_grouped.iterrows():
    # Fixando o fuso horário (ajuste para o fuso local do banco de dados)
    dt_str = f"{row['Data']} {row['Hora']:02d}:00:00"
    dt_obj = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    timestamp_ms = int(dt_obj.timestamp() * 1000)
    
    zona = str(row[col_zona]).strip()
    
    p = (
        Point("schedules_r1_r6")
        .tag("zona", zona)
        .field("met", round(row['met_medio'], 2))
        .field("clo", round(row['clo_medio'], 2))
        .field("ocupacao", int(row['ocupacao']))
        .field("temperatura", 0.0)  
        .field("umidade", 0.0)      
        .field("epmv", 0.0)         
        .time(timestamp_ms, write_precision=influxdb_client.WritePrecision.MS)
    )
    write_api.write(bucket=BUCKET, org=ORG, record=p)

print("✅ Dados processados do CSV e injetados com sucesso no InfluxDB!")