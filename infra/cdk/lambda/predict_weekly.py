import csv
import io
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import boto3

rt = boto3.client("sagemaker-runtime")
sm = boto3.client("sagemaker")
s3 = boto3.client("s3")
cw = boto3.client("cloudwatch")

def _parse_s3_uri(uri: str) -> Tuple[str, str]:
    p = urlparse(uri)
    if p.scheme != "s3" or not p.netloc or not p.path:
        raise ValueError(f"Invalid S3 URI: {uri}")
    return p.netloc, p.path.lstrip("/")

def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Invoke endpoint for fixtures CSV and write predictions CSV.

    Expected event:
      - endpoint_name
      - fixtures_s3_uri
      - gameweek
      - lifecycle (optional; overrides ENDPOINT_LIFECYCLE)
    """
    endpoint_name = event["endpoint_name"]
    fixtures_s3_uri = event["fixtures_s3_uri"]
    gameweek = event["gameweek"]
    lifecycle = (event.get("lifecycle") or os.environ.get("ENDPOINT_LIFECYCLE") or "ephemeral").lower()

    out_bucket = os.environ["PRED_BUCKET"]

    f_bucket, f_key = _parse_s3_uri(fixtures_s3_uri)
    data = s3.get_object(Bucket=f_bucket, Key=f_key)["Body"].read().decode("utf-8")
    fixtures = list(csv.DictReader(io.StringIO(data)))

    out_rows: List[Dict[str, Any]] = []
    for fx in fixtures:
        home = fx["home"]
        away = fx["away"]
        payload = json.dumps({"home_team": home, "away_team": away})
        resp = rt.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType="application/json",
            Accept="application/json",
            Body=payload,
        )
        pred = json.loads(resp["Body"].read().decode("utf-8"))
        out_rows.append(
            {
                "gameweek": fx.get("gameweek", gameweek),
                "date": fx["date"],
                "home": home,
                "away": away,
                "p_home_win": pred["p_home_win"],
                "p_draw": pred["p_draw"],
                "p_away_win": pred["p_away_win"],
                "r_home": pred["r_home"],
                "r_away": pred["r_away"],
            }
        )

    out_key = f"predictions/{gameweek}/wsl_predictions.csv"
    buf = io.StringIO()
    fieldnames = list(out_rows[0].keys()) if out_rows else ["gameweek","date","home","away","p_home_win","p_draw","p_away_win","r_home","r_away"]
    wri = csv.DictWriter(buf, fieldnames=fieldnames)
    wri.writeheader()
    for r in out_rows:
        wri.writerow(r)

    s3.put_object(Bucket=out_bucket, Key=out_key, Body=buf.getvalue().encode("utf-8"), ContentType="text/csv")

    # Metrics
    if out_rows:
        avg_home = sum(float(r["p_home_win"]) for r in out_rows) / len(out_rows)
    else:
        avg_home = 0.0

    cw.put_metric_data(
        Namespace="WSLAnalytics",
        MetricData=[
            {"MetricName": "PredictionsGenerated", "Value": len(out_rows), "Unit": "Count", "Timestamp": datetime.utcnow()},
            {"MetricName": "AverageHomeWinProbability", "Value": avg_home, "Unit": "None", "Timestamp": datetime.utcnow()},
        ],
    )

    if lifecycle == "ephemeral":
        sm.delete_endpoint(EndpointName=endpoint_name)

    return {"output_s3_uri": f"s3://{out_bucket}/{out_key}", "rows": len(out_rows), "gameweek": gameweek}
