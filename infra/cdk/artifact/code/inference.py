
import os, joblib, numpy as np

def model_fn(model_dir):
    return joblib.load(os.path.join(model_dir, "model.joblib"))

def input_fn(body, content_type):
    if content_type == "text/csv":
        vals = [float(x) for x in body.strip().split(",")]
        return np.array([vals])
    raise ValueError(f"Unsupported content type: {content_type}")

def predict_fn(data, model):
    return model.predict(data)

def output_fn(pred, accept):
    if accept in ("text/csv","text/plain"):
        return ",".join(map(str, pred.tolist())), "text/csv"
    return str(pred.tolist()), "application/json"
