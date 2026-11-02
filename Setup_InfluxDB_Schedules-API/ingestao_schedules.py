import influxdb_client
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime

# 1. Credenciais definidas no Docker Compose
URL = "http://localhost:8086"
TOKEN = "token-api-grupo1-2026"
ORG = "ufc_quixada"
BUCKET = "instrumentacao_2026"

client = influxdb_client.InfluxDBClient(url=URL, token=TOKEN, org=ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# 2. Dados extraídos da Tabela 1 do Relatório (Zonas com respondentes/ocupação)
# Mapeando horários de referência: Manhã (10:00), Tarde 1 (13:30), Tarde 2 (15:30)
data_coleta = "2026-09-30" # Data base para os timestamps

schedules = [
    # Manhã (10h)
    {"zona": "R2", "hora": "10:00:00", "met": 1.05, "clo": 0.42, "ocupacao": 2},
    {"zona": "R5", "hora": "10:00:00", "met": 1.03, "clo": 0.44, "ocupacao": 4},
    {"zona": "R6", "hora": "10:00:00", "met": 1.05, "clo": 0.41, "ocupacao": 2},
    
    # Tarde 1 (13:30)
    {"zona": "R5", "hora": "13:30:00", "met": 1.04, "clo": 0.44, "ocupacao": 7},
    {"zona": "R6", "hora": "13:30:00", "met": 1.13, "clo": 0.51, "ocupacao": 4},
    
    # Tarde 2 (15:30)
    {"zona": "R1", "hora": "15:30:00", "met": 1.03, "clo": 0.62, "ocupacao": 6},
    {"zona": "R2", "hora": "15:30:00", "met": 1.03, "clo": 0.49, "ocupacao": 4},
    {"zona": "R5", "hora": "15:30:00", "met": 1.06, "clo": 0.43, "ocupacao": 10},
    {"zona": "R6", "hora": "15:30:00", "met": 1.00, "clo": 0.49, "ocupacao": 1}
]

# 3. Construção e Injeção dos Pontos
for entrada in schedules:
    # Conversão para timestamp Unix em milissegundos
    dt_str = f"{data_coleta} {entrada['hora']}"
    dt_obj = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    timestamp_ms = int(dt_obj.timestamp() * 1000)
    
    # Estruturação exigida: Measurement, Tags e Fields
    p = (
        Point("schedules_r1_r6")
        .tag("zona", entrada["zona"])
        .field("met", float(entrada["met"]))
        .field("clo", float(entrada["clo"]))
        .field("ocupacao", int(entrada["ocupacao"]))
        # Inicializando campos ambientais vazios para o Grupo 2 preencher depois
        .field("temperatura", 0.0)
        .field("umidade", 0.0)
        .field("epmv", 0.0)
        .time(timestamp_ms, write_precision=influxdb_client.WritePrecision.MS)
    )
    
    write_api.write(bucket=BUCKET, org=ORG, record=p)

print("Schedules injetados com sucesso via API no InfluxDB!")