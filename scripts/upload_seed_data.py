from pathlib import Path
import boto3

def ssm_get(name: str) -> str:
    return boto3.client("ssm").get_parameter(Name=name)["Parameter"]["Value"]

def main() -> None:
    raw_uri = ssm_get("/wsl-mlops/raw_bucket_uri").rstrip("/")
    bucket = raw_uri.replace("s3://", "")

    repo_root = Path(__file__).resolve().parents[1]
    seed = repo_root / "data" / "seed" / "wsldata.csv"
    fixtures = repo_root / "data" / "seed" / "upcoming_fixtures_example.csv"

    if not seed.exists():
        raise SystemExit(f"Missing seed file: {seed}")

    s3 = boto3.client("s3")
    s3.upload_file(str(seed), bucket, "raw/wsldata.csv")
    s3.upload_file(str(fixtures), bucket, "fixtures/upcoming_fixtures.csv")
    print(f"Uploaded: s3://{bucket}/raw/wsldata.csv")
    print(f"Uploaded: s3://{bucket}/fixtures/upcoming_fixtures.csv")

if __name__ == "__main__":
    main()
