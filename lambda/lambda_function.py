import os, json, base64, boto3, time

sagemaker_runtime = boto3.client("sagemaker-runtime")
firehose = boto3.client("firehose")

SAGEMAKER_ENDPOINT = os.getenv("SAGEMAKER_ENDPOINT")
FIREHOSE_STREAM = os.getenv("FIREHOSE_STREAM")
THRESHOLD = float(os.getenv("THRESHOLD", "10"))  # USD

def predict_fare(payload):
    features = [
        payload.get("trip_distance", 0.0),
        payload.get("passenger_count", 1),
        payload.get("PULocationID", 0),
        payload.get("DOLocationID", 0)
    ]
    body = ",".join(str(x) for x in features)
    resp = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType="text/csv",
        Body=body.encode("utf-8")
    )
    pred = float(resp["Body"].read())
    return pred

def lambda_handler(event, context):
    out = []
    for rec in event["Records"]:
        data = rec.get("kinesis", {}).get("data")
        if not data:
            continue
        payload = json.loads(base64.b64decode(data).decode("utf-8"))
        try:
            yhat = predict_fare(payload)
        except Exception as e:
            yhat = None

        fare = payload.get("fare_amount", 0.0)
        outlier = (yhat is not None) and (abs(fare - yhat) > THRESHOLD)

        enriched = {
            **payload,
            "predicted_fare": yhat,
            "abs_error": None if yhat is None else round(abs(fare - yhat), 3),
            "is_outlier": bool(outlier),
            "ts": int(time.time() * 1000)
        }
        out.append({"Data": (json.dumps(enriched) + "\n").encode("utf-8")})

    if out and FIREHOSE_STREAM:
        for i in range(0, len(out), 400):
            firehose.put_record_batch(
                DeliveryStreamName=FIREHOSE_STREAM,
                Records=out[i:i+400]
            )

    return {"ok": True, "n": len(out)}
