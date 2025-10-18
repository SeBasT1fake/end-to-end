# Especificación del Caso de Estudio — ST1630 (Opción 1)

## 1. Nombre del proyecto
**NYC Taxi Anomaly Streaming — Kappa + MLOps en AWS**

## 2. Integrantes
- Juan Sebastian Aguilar Carballo — jsaguilarc@eafit.edu.co
- Jeronimo Cardona Osorio — jcardonao2@eafit.edu.co
- Daniel Melguizo Roldan — dmelguizor@eafit.edu.co

## 3. Descripción del caso
- **Negocio**: Detección temprana de viajes con tarifa anómala para alertar operaciones y auditoría.
- **Pregunta analítica**: ¿La tarifa observada es consistente con una tarifa esperada según contexto del viaje?
- **Hipótesis**: El error absoluto > THRESHOLD sugiere potencial anomalía (fraude, error de captura, ruta atípica).

## 4. Descripción tecnológica (reto Big Data)
- *Adquisición*: Productor Python → Kinesis (stream). Histórico batch en S3 (NYC TLC).
- *Ingesta y almacenamiento*: S3 (bronze/silver/gold) + Glue + Athena.
- *Procesamiento*: Lambda para inferencias en tiempo real (opcional Flink).
- *MLOps*: SageMaker (XGBoost), endpoint, Registry (versionado).
- *Distribución y visualización*: Firehose a S3/OpenSearch; Dashboards en vivo, consultas en Athena.

## 5. Metodología analítica (CRISP‑DM)
1. **Comprensión del negocio**: definición de KPIs (MAE, tasa de outliers), umbrales, SLA de latencia.
2. **Comprensión de datos**: exploración de NYC TLC; validación de esquemas y *data quality*.
3. **Preparación de datos**: *feature engineering* (hora, zonas, distancia).
4. **Modelado**: XGBoost (regresión). *Hyperparams* básicos.
5. **Evaluación**: MAE/Mediana, *drift* de errores.
6. **Despliegue**: Endpoint, Lambda + Kinesis + Firehose/OpenSearch.
7. **Mantenimiento**: *pipelines* de re‑entrenamiento y *monitoring* (CloudWatch).

## 6. Arquitectura de referencia (AWS)
Kinesis → Lambda (SageMaker Endpoint) → Firehose → S3/OpenSearch  
Batch en S3/Glue/Athena para entrenamiento y análisis.

## 7. Implementación por etapas
Ver `README.md` y carpetas `producer/`, `lambda/`, `sagemaker/`, `viz/`.

## 8. Evidencias y demo
- Capturas de: Kinesis, Lambda, CloudWatch logs, SageMaker endpoint, OpenSearch Dashboard, Athena consultas.
- Video corto mostrando flujo E2E.

## 9. Roles
- Ingesta/Streaming: …
- MLOps/Modelo: …
- Visualización/Exploratorio: …

## 10. Costos/seguridad
- Apagar endpoint fuera de demo. IAM *least privilege*. Logs y *metrics* en CloudWatch.
