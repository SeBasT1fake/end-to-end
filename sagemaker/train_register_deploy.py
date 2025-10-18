import argparse, boto3, sagemaker
from sagemaker import Session
from sagemaker.inputs import TrainingInput
from sagemaker.xgboost.estimator import XGBoost

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--region', required=True)
    ap.add_argument('--role', required=True)
    ap.add_argument('--train_s3', required=True, help='s3://bucket/prefix/')
    ap.add_argument('--models_s3', required=True, help='s3://bucket/models/')
    ap.add_argument('--endpoint_name', required=True)
    args = ap.parse_args()

    sess = sagemaker.Session(boto3.session.Session(region_name=args.region))
    container = sagemaker.image_uris.retrieve("xgboost", args.region, version="1.7-1")

    xgb = XGBoost(
        entry_point=None,
        source_dir=None,
        image_uri=container,
        role=args.role,
        instance_count=1,
        instance_type="ml.m5.xlarge",
        output_path=args.models_s3,
        sagemaker_session=sess,
        hyperparameters={
            "max_depth": "6",
            "eta": "0.2",
            "subsample": "0.8",
            "objective": "reg:squarederror",
            "num_round": "100"
        }
    )

    xgb.fit({"train": TrainingInput(args.train_s3, content_type="x-parquet")})
    try:
        xgb.deploy(initial_instance_count=1, instance_type="ml.m5.large", endpoint_name=args.endpoint_name)
    except Exception as e:
        print("Endpoint may already exist:", e)

if __name__ == '__main__':
    main()
