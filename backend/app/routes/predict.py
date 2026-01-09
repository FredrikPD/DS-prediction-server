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
    # Use default model if none specified
    model_id = body.model_id or reg.manifest["default_model"]

    if model_id not in reg.models:
        raise HTTPException(status_code=400, detail=f"Unknown model_id: {model_id}")

    cols = reg.manifest["feature_columns"]
    
    if hasattr(reg, 'full_pipeline') and reg.full_pipeline:
         # Use full pipeline if available (likely handles raw features)
         X = pd.DataFrame([body.features])
    else:
        # Legacy fallback: strict feature column adherence with default imputation
        full_features = {}
        for c in cols:
            val = body.features.get(c)
            if val is None:
                val = 0
            full_features[c] = val
        X = pd.DataFrame([full_features], columns=cols)

    if hasattr(reg, 'full_pipeline') and reg.full_pipeline:
         # Clean X and transform using the full pipeline
         X = X.drop(columns=[reg.manifest["target_column"]], errors='ignore')
         Xt = reg.full_pipeline.transform(X)
    else:
         Xt = reg.pipeline.transform(X)
    pred = reg.models[model_id].model.predict(Xt)[0]

    return {"model_id": model_id, "prediction": str(pred)}