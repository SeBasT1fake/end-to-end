import argparse, csv, json, random, time, os
import boto3

def as_event(row):
    return {
        "tpep_pickup_datetime": row.get("tpep_pickup_datetime"),
        "tpep_dropoff_datetime": row.get("tpep_dropoff_datetime"),
        "passenger_count": int(float(row.get("passenger_count", 1) or 1)),
        "trip_distance": float(row.get("trip_distance", 1.0) or 1.0),
        "PULocationID": int(float(row.get("PULocationID", 1) or 1)),
        "DOLocationID": int(float(row.get("DOLocationID", 1) or 1)),
        "fare_amount": float(row.get("fare_amount", 10.0) or 10.0),
        "tip_amount": float(row.get("tip_amount", 0.0) or 0.0),
        "total_amount": float(row.get("total_amount", 10.0) or 10.0),
        "payment_type": int(float(row.get("payment_type", 1) or 1))
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True)
    parser.add_argument("--stream", default=os.getenv("KINESIS_STREAM_NAME", "taxi-trips-stream"))
    parser.add_argument("--csv", help="Path to CSV sample")
    parser.add_argument("--rate", type=int, default=5, help="events per second")
    args = parser.parse_args()

    kinesis = boto3.client("kinesis", region_name=args.region)

    if args.csv:
        f = open(args.csv, newline="", encoding="utf-8")
        reader = csv.DictReader(f)
        rows = list(reader)
    else:
        rows = []

    i = 0
    while True:
        if rows:
            row = rows[i % len(rows)]
            event = as_event(row)
        else:
            event = {
                "tpep_pickup_datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tpep_dropoff_datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
                "passenger_count": random.randint(1, 4),
                "trip_distance": round(random.uniform(0.5, 12.0), 2),
                "PULocationID": random.randint(1, 200),
                "DOLocationID": random.randint(1, 200),
                "fare_amount": round(random.uniform(5, 80), 2),
                "tip_amount": round(random.uniform(0, 15), 2),
                "total_amount": 0.0,
                "payment_type": random.randint(1, 4)
            }
            event["total_amount"] = round(event["fare_amount"] + event["tip_amount"], 2)

        kinesis.put_record(
            StreamName=args.stream,
            Data=json.dumps(event).encode("utf-8"),
            PartitionKey=str(event["PULocationID"])
        )
        i += 1
        time.sleep(1.0 / max(1, args.rate))

if __name__ == "__main__":
    main()
