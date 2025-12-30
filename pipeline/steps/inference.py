import json
import pickle
from typing import Any, Dict, Tuple

def model_fn(model_dir: str) -> Any:
    with open(f"{model_dir}/model.pkl", "rb") as f:
        return pickle.load(f)

def input_fn(request_body: str, content_type: str) -> Any:
    if content_type != "application/json":
        raise ValueError(f"Unsupported content type: {content_type}")
    return json.loads(request_body)

def predict_fn(input_data: Any, model: Any) -> Any:
    if isinstance(input_data, list):
        return [model.predict(d["home_team"], d["away_team"]) for d in input_data]
    return model.predict(input_data["home_team"], input_data["away_team"])

def output_fn(prediction: Any, accept: str) -> Tuple[str, str]:
    if accept != "application/json":
        raise ValueError(f"Unsupported accept: {accept}")
    return json.dumps(prediction), accept
