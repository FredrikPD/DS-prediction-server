from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Form
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

router = APIRouter()

@router.post("/evaluate-models")
async def evaluate_models(
    request: Request,
    file: UploadFile = File(...),
    model_id: str | None = Form(None)
):
    reg = request.app.state.registry
    target = reg.manifest["target_column"]
    cols = reg.manifest["feature_columns"]

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")

    df = pd.read_csv(file.file)

    if target not in df.columns:
        raise HTTPException(status_code=400, detail=f"Missing target column: {target}")

    for c in cols:
        if c not in df.columns:
            raise HTTPException(status_code=400, detail=f"Missing feature column: {c}")

    y_true = df[target]
    X = df[cols]

    Xt = reg.pipeline.transform(X)

    model_ids = [model_id] if model_id else list(reg.models.keys())
    for mid in model_ids:
        if mid not in reg.models:
            raise HTTPException(status_code=400, detail=f"Unknown model_id: {mid}")

    results = []
    for mid in model_ids:
        m = reg.models[mid].model
        y_pred = m.predict(Xt)

        results.append({
            "model_id": mid,
            "technique": reg.models[mid].technique,
            "metrics": {
                "accuracy": float(accuracy_score(y_true, y_pred)),
                "precision": float(precision_score(y_true, y_pred, zero_division=0)),
                "recall": float(recall_score(y_true, y_pred, zero_division=0)),
                "f1": float(f1_score(y_true, y_pred, zero_division=0)),
            }
        })

    return {"results": results}