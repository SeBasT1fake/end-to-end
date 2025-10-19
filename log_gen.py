import json
import random
import time
from datetime import datetime
import boto3
import os

# Configuración de AWS
s3_client = boto3.client('s3')
BUCKET_NAME = 'ecommerce-logs-bucket-st1630'

# Datos de muestra para generar logs realistas
productos = [
    {"id": "P001", "nombre": "Laptop Dell XPS 13", "precio": 1299.99, "categoria": "Electronica"},
    {"id": "P002", "nombre": "iPhone 14 Pro", "precio": 999.99, "categoria": "Electronica"},
    {"id": "P003", "nombre": "Zapatillas Nike Air", "precio": 129.99, "categoria": "Deportes"},
    {"id": "P004", "nombre": "Cafetera Nespresso", "precio": 199.99, "categoria": "Hogar"},
    {"id": "P005", "nombre": "Libro Python Avanzado", "precio": 49.99, "categoria": "Libros"},
    {"id": "P006", "nombre": "Auriculares Sony WH-1000XM4", "precio": 349.99, "categoria": "Electronica"},
    {"id": "P007", "nombre": "Smart Watch Apple", "precio": 399.99, "categoria": "Electronica"},
    {"id": "P008", "nombre": "Mochila North Face", "precio": 89.99, "categoria": "Deportes"}
]

eventos = ["BUSQUEDA", "AGREGAR_CARRITO", "COMPRA", "VISTA_PRODUCTO", "PAGO_COMPLETADO", "PAGO_FALLIDO"]
regiones = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
metodos_pago = ["tarjeta_credito", "paypal", "transferencia", "efectivo"]

def generar_log_evento():
    """Genera un evento de log aleatorio para el e-commerce"""
    evento = random.choice(eventos)
    producto = random.choice(productos)
    
    log = {
        "timestamp": f"2025-10-14T{str(datetime.now().hour)}:{str(datetime.now().minute)}:{str(datetime.now().second)}Z",
        "evento": evento,
        "usuario_id": f"USER{random.randint(1000, 9999)}",
        "sesion_id": f"SES{random.randint(100000, 999999)}",
        "producto_id": producto["id"],
        "producto_nombre": producto["nombre"],
        "producto_precio": producto["precio"],
        "categoria": producto["categoria"],
        "region": random.choice(regiones),
        "ip_address": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    }
    
    if evento in ["COMPRA", "PAGO_COMPLETADO"]:
        log["cantidad"] = random.randint(1, 5)
        log["total"] = round(log["cantidad"] * producto["precio"], 2)
        log["metodo_pago"] = random.choice(metodos_pago)
        log["estado_envio"] = "pendiente"
    
    if evento == "PAGO_FALLIDO":
        log["razon_fallo"] = random.choice(["fondos_insuficientes", "tarjeta_rechazada", "timeout"])
        log["metodo_pago"] = random.choice(metodos_pago)

    return log

def guardar_y_subir_log(log):
    """Guarda un log localmente y lo sube a S3"""
    archivo = "log_evento.json"
    with open(archivo, 'w', encoding='utf-8') as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")

    timestamp = f"20251014_{str(datetime.now().hour)}{str(datetime.now().minute)}{str(datetime.now().second)}"
    s3_key = f"logs/{timestamp}_log_evento.json"
    
    try:
        s3_client.upload_file(archivo, BUCKET_NAME, s3_key)
        print(f"[{timestamp}] Evento '{log['evento']}' subido a s3://{BUCKET_NAME}/{s3_key}")
    except Exception as e:
        print(f"Error al subir el log a S3: {e}")

def main():
    """Genera logs de evento cada 5 a 10 segundos y los sube a S3"""
    print("=== Generador de Logs de E-Commerce (Tiempo Real) ===")
    while True:
        log = generar_log_evento()
        guardar_y_subir_log(log)
        intervalo = random.randint(5, 10)
        print(f"Esperando {intervalo} segundos antes del siguiente evento...\n")
        time.sleep(intervalo)

if __name__ == "__main__":
    main()