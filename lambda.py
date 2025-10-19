import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

# Inicializar clientes AWS
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
kinesis_client = boto3.client('kinesis')
cloudwatch = boto3.client('cloudwatch')

# Variables de entorno
DYNAMODB_TABLE = 'EcommerceLogs'
KINESIS_STREAM = 'ecommerce-stream'

# Obtener referencia a la tabla DynamoDB
table = dynamodb.Table(DYNAMODB_TABLE)

def lambda_handler(event, context): 
    print(f"Evento recibido: {json.dumps(event)}")
    
    # Contadores para métricas
    total_eventos = 0
    eventos_por_tipo = {}
    ventas_totales = 0
    
    try:
        # Procesar cada registro del evento S3
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            print(f"Procesando archivo: s3://{bucket}/{key}")
        
            response = s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            
            for line in content.strip().split('\n'):
                if line:
                    log_entry = json.loads(line)
                    
                    process_log(log_entry)
                    
                    total_eventos += 1
                    evento_tipo = log_entry.get('evento', 'DESCONOCIDO')
                    eventos_por_tipo[evento_tipo] = eventos_por_tipo.get(evento_tipo, 0) + 1
                    
                    # Sumar ventas si es una compra
                    if evento_tipo in ['COMPRA', 'PAGO_COMPLETADO']:
                        ventas_totales += log_entry.get('total', 0)
        
        # Enviar métricas a CloudWatch
        enviar_metricas_cloudwatch(total_eventos, eventos_por_tipo, ventas_totales)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Logs procesados exitosamente',
                'total_eventos': total_eventos,
                'eventos_por_tipo': eventos_por_tipo,
                'ventas_totales': round(ventas_totales, 2)
            })
        }
        
    except Exception as e:
        print(f"Error procesando logs: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def process_log(log_entry):

    try:
        item = convert_floats_to_decimal(log_entry)
        
        item['log_id'] = f"{item['timestamp']}_{item['usuario_id']}_{item['sesion_id']}"
        
        table.put_item(Item=item)
        print(f"Log guardado en DynamoDB: {item['log_id']}")
        
    except Exception as e:
        print(f"Error guardando en DynamoDB: {str(e)}")

    try:
        kinesis_client.put_record(
            StreamName=KINESIS_STREAM,
            Data=json.dumps(log_entry),
            PartitionKey=log_entry.get('usuario_id', 'default')
        )
        print(f"Log enviado a Kinesis: {log_entry.get('evento')}")
        
    except Exception as e:
        print(f"Error enviando a Kinesis: {str(e)}")

def convert_floats_to_decimal(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    return obj

def enviar_metricas_cloudwatch(total_eventos, eventos_por_tipo, ventas_totales):
    
    try:
        metric_data = []
        
        # Métrica: Total de eventos procesados
        metric_data.append({
            'MetricName': 'TotalEventos',
            'Value': total_eventos,
            'Unit': 'Count',
            'Timestamp': datetime.utcnow()
        })
        
        # Métrica: Ventas totales
        metric_data.append({
            'MetricName': 'VentasTotales',
            'Value': ventas_totales,
            'Unit': 'None',
            'Timestamp': datetime.utcnow()
        })
        
        # Métricas por tipo de evento
        for evento_tipo, count in eventos_por_tipo.items():
            metric_data.append({
                'MetricName': f'Eventos_{evento_tipo}',
                'Value': count,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            })
        
        # Enviar todas las métricas a CloudWatch
        cloudwatch.put_metric_data(
            Namespace='EcommerceLogs',
            MetricData=metric_data
        )
        
        print(f"Métricas enviadas a CloudWatch: {len(metric_data)} métricas")
        
    except Exception as e:
        print(f"Error enviando métricas a CloudWatch: {str(e)}")