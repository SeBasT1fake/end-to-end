# ST1630 — Opción 1: Analítica avanzada en *streaming* con MLOps (AWS)

Este repositorio guía un caso end‑to‑end usando **Kinesis → Lambda (inferencias con SageMaker) → Firehose → S3 / OpenSearch**; *batch* en S3 + Glue/Athena; entrenamiento y *deployment* con **SageMaker** y visualización en **OpenSearch Dashboards**. Arquitectura tipo **Kappa** (stream-first) con *batch* para entrenamiento.

## Caso
**Detección en tiempo real de viajes con tarifa anómala (NYC Taxi)**.  
- **Batch**: histórico de viajes (NYC TLC) para entrenar un modelo que prediga la *tarifa esperada* dada la distancia, duración, zona, hora, etc.  
- **Streaming**: un productor re‑emite viajes en tiempo real hacia **Kinesis Data Streams**.  
- **Inferencia**: una **Lambda** consume de Kinesis, consulta un **endpoint de SageMaker** y marca outliers (|tarifa_real – tarifa_predicha| > umbral).  
- **Serving / Viz**: resultados a **S3** (datalake oro) y a **OpenSearch** para tablero en vivo.

## Componentes (AWS)
- **Ingesta**: Amazon Kinesis Data Streams (KDS), productor Python (boto3).  
- **Procesamiento en línea**: AWS Lambda (opcionalmente Kinesis Data Analytics/Flink).  
- **MLOps**: Amazon SageMaker (XGBoost built‑in), Model Registry, Endpoint.  
- **Datalake**: Amazon S3 (bronze/silver/gold) + AWS Glue Data Catalog + Amazon Athena.  
- **NoSQL**: Amazon DynamoDB (parámetros y umbrales).  
- **Visualización**: Amazon OpenSearch Service + Dashboards.  
- **Orquestación y CI/CD (opcional)**: CodePipeline/CodeBuild para *infra as code*.

## Prerrequisitos
- Cuenta AWS con permisos: S3, Kinesis, Lambda, SageMaker, DynamoDB, OpenSearch, Glue/Athena, IAM, CloudWatch.  
- AWS CLI v2 configurado (`aws configure`). Python 3.10+ y `virtualenv`.  
- Región sugerida: `us-east-1` (cambia si lo prefieres).

## Pasos (resumen)
1) **Crear buckets y catálogo**  
   - `RAW_BUCKET`, `PROCESSED_BUCKET`, `MODELS_BUCKET` con versionamiento.  
   - Glue Database `nyc_db` y tabla externa para histórico.  
2) **Muestrear histórico para entrenamiento** con **Athena** (*CTAS*) hacia `PROCESSED_BUCKET`.  
3) **Entrenar y desplegar** con `sagemaker/train_register_deploy.py` (XGBoost) → Model Registry → Endpoint.  
4) **Crear streaming**: Kinesis Stream `taxi-trips-stream` y Firehose `taxi-predictions-firehose` a S3 y/o OpenSearch.  
5) **Desplegar Lambda** (`lambda/lambda_function.py`) que lee Kinesis, llama SageMaker y envía resultados a Firehose.  
6) **Lanzar productor** (`producer/producer.py`) para emitir eventos.  
7) **Explorar con Athena** (particiones oro) y **visualizar** en OpenSearch Dashboards (índice `taxi-predictions-*`).  
8) **MLOps**: re‑entrenamiento programado (Pipeline) y *rollbacks* de endpoint vía Model Registry.

> **Nota**: Los scripts incluyen *placeholders* (`<TU-...>`). Reemplázalos con tus nombres de recurso.

---

## Paso a paso — Comandos mínimos

### 0) Variables locales (Linux/Mac/WSL)
```bash
export AWS_REGION=us-east-1
export RAW_BUCKET=<TU-PREFIJO>-nyc-raw
export PROCESSED_BUCKET=<TU-PREFIJO>-nyc-processed
export MODELS_BUCKET=<TU-PREFIJO>-nyc-models
export SAGEMAKER_EXECUTION_ROLE=<ARN-ROLE-SAGEMAKER>
```

### 1) Buckets y Glue/Athena
```bash
aws s3 mb s3://$RAW_BUCKET --region $AWS_REGION
aws s3 mb s3://$PROCESSED_BUCKET --region $AWS_REGION
aws s3 mb s3://$MODELS_BUCKET --region $AWS_REGION

aws s3api put-bucket-versioning --bucket $RAW_BUCKET --versioning-configuration Status=Enabled
aws s3api put-bucket-versioning --bucket $PROCESSED_BUCKET --versioning-configuration Status=Enabled
aws s3api put-bucket-versioning --bucket $MODELS_BUCKET --versioning-configuration Status=Enabled

# Glue DB
aws glue create-database --database-input Name=nyc_db

# (Opcional) Cargar muestra CSV provista en ./data a s3://$RAW_BUCKET/nyc_taxi/
aws s3 cp data/sample_nyc_taxi.csv s3://$RAW_BUCKET/nyc_taxi/year=2023/month=01/
```

En Athena (consulta de ejemplo):
```sql
CREATE EXTERNAL TABLE IF NOT EXISTS nyc_db.taxi_raw(
  tpep_pickup_datetime string,
  tpep_dropoff_datetime string,
  passenger_count int,
  trip_distance double,
  PULocationID int,
  DOLocationID int,
  fare_amount double,
  tip_amount double,
  total_amount double,
  payment_type int
)
PARTITIONED BY (year string, month string)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe'
WITH SERDEPROPERTIES ('separatorChar' = ',')
LOCATION 's3://<RAW_BUCKET>/nyc_taxi/';
```

Materializar conjunto de entrenamiento (*CTAS*):
```sql
CREATE TABLE nyc_db.taxi_train
WITH (
  external_location = 's3://<PROCESSED_BUCKET>/train/',
  format = 'PARQUET'
) AS
SELECT
  trip_distance, passenger_count, PULocationID, DOLocationID,
  year, month,
  fare_amount AS label
FROM nyc_db.taxi_raw
WHERE fare_amount BETWEEN 3 AND 200
  AND trip_distance BETWEEN 0.1 AND 50;
```

### 2) Entrenar y desplegar (SageMaker)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r sagemaker/requirements.txt

python sagemaker/train_register_deploy.py   --region $AWS_REGION   --role $SAGEMAKER_EXECUTION_ROLE   --train_s3 s3://$PROCESSED_BUCKET/train/   --models_s3 s3://$MODELS_BUCKET/   --endpoint_name taxi-fare-xgb-endpoint
```

### 3) Streaming y Firehose/OpenSearch
```bash
# Kinesis Data Streams
aws kinesis create-stream --stream-name taxi-trips-stream --shard-count 1

# Firehose a S3 (simplificado)
aws firehose create-delivery-stream   --delivery-stream-name taxi-predictions-firehose   --delivery-stream-type DirectPut   --s3-destination-configuration RoleARN=<ARN-ROLE-FIREHOSE>,BucketARN=arn:aws:s3:::${PROCESSED_BUCKET},Prefix=predictions/
```

### 4) Desplegar Lambda (inferencia online)
```bash
cd lambda
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
zip -r9 ../lambda.zip .
cd ..

aws iam create-role --role-name taxi-lambda-role --assume-role-policy-document file://infra/trust-lambda.json
aws iam attach-role-policy --role-name taxi-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaKinesisExecutionRole
aws iam attach-role-policy --role-name taxi-lambda-role --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
aws iam attach-role-policy --role-name taxi-lambda-role --policy-arn arn:aws:iam::aws:policy/AmazonKinesisFullAccess
aws iam attach-role-policy --role-name taxi-lambda-role --policy-arn arn:aws:iam::aws:policy/AmazonKinesisFirehoseFullAccess

aws lambda create-function   --function-name taxi-kinesis-infer   --runtime python3.10   --role arn:aws:iam::<TU-CUENTA>:role/taxi-lambda-role   --handler lambda_function.lambda_handler   --zip-file fileb://lambda.zip   --environment "Variables={{SAGEMAKER_ENDPOINT=taxi-fare-xgb-endpoint,FIREHOSE_STREAM=taxi-predictions-firehose,THRESHOLD=10}}"

aws lambda create-event-source-mapping   --function-name taxi-kinesis-infer   --event-source-arn arn:aws:kinesis:<REGION>:<CUENTA>:stream/taxi-trips-stream   --starting-position LATEST
```

### 5) Lanzar el productor (eventos en vivo)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r producer/requirements.txt

export KINESIS_STREAM_NAME=taxi-trips-stream
python producer/producer.py --region $AWS_REGION --stream $KINESIS_STREAM_NAME --csv data/sample_nyc_taxi.csv --rate 10
```

### 6) Visualizar
- **OpenSearch**: crear dominio, un índice `taxi-predictions-*` y un *Index Pattern*; crear visualizaciones (línea de total_amount vs predicción, tasa de outliers por ventana).  
- **Athena**: consultar `s3://$PROCESSED_BUCKET/predictions/` para análisis histórico.

---

## Estructura
```
producer/producer.py
lambda/lambda_function.py
sagemaker/train_register_deploy.py
infra/ (políticas IAM mínimas + trust-policy)
viz/opensearch_index_mapping.json
data/sample_nyc_taxi.csv
docs/spec_template.md
```

## Costos y *cleanup*
- Apaga el **endpoint de SageMaker** si no lo usas: `aws sagemaker delete-endpoint --endpoint-name ...`  
- Borra el **dominio OpenSearch** al finalizar.  
- Elimina **Kinesis**, **Firehose** y buckets si no los necesitas.

---

## Créditos y licencia
Plantilla educativa con fines académicos (EAFIT — ST1630). Ajusta recursos/roles según tu organización.
