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
    
    # Fill missing features with defaults
    full_features = {}
    for c in cols:
        val = body.features.get(c)
        if val is None:
            # Simple imputation: "0" for maybe-numeric, "" for text
            val = 0 # Default to number 0
        full_features[c] = val

    X = pd.DataFrame([full_features], columns=cols)

    Xt = reg.pipeline.transform(X)
    pred = reg.models[model_id].model.predict(Xt)[0]

    return {"model_id": model_id, "prediction": str(pred)}