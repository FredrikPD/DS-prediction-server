from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import pandas as pd

router = APIRouter()

class PredictSingleBody(BaseModel):
    model_id: str | None = None
    features: dict

@router.post("/predict-single")
def predict_single(body: PredictSingleBody, request: Request):
    reg = request.app.state.registry
    model_id = body.model_id or reg.manifest["default_model"]

    if model_id not in reg.models:
        raise HTTPException(status_code=400, detail=f"Unknown model_id: {model_id}")

    cols = reg.manifest["feature_columns"]
    
    # Determine if we have raw features or processed features
    # Heuristic: If we have "Airline", "Origin", "Dest" (raw keys) then use full_pipeline
    # Otherwise use strict feature_columns (processed) features logic.
    
    # We essentially trust the input dict to be raw if full_pipeline is available.
    if hasattr(reg, 'full_pipeline') and reg.full_pipeline:
         X = pd.DataFrame([body.features])
    else:
        # Legacy behavior: strict adherence to processed feature columns
        # Fill missing features with defaults
        full_features = {}
        for c in cols:
            val = body.features.get(c)
            if val is None:
                # Simple imputation: "0" for maybe-numeric, "" for text
                val = 0 # Default to number 0
            full_features[c] = val
        X = pd.DataFrame([full_features], columns=cols)

    if hasattr(reg, 'full_pipeline') and reg.full_pipeline:
         # Drop target if present (unlikely in predict mode but safe)
         X = X.drop(columns=[reg.manifest["target_column"]], errors='ignore')
         Xt = reg.full_pipeline.transform(X)
    else:
         Xt = reg.pipeline.transform(X)
    pred = reg.models[model_id].model.predict(Xt)[0]

    return {"model_id": model_id, "prediction": str(pred)}