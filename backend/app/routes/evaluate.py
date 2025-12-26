from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Form
import pandas as pd
from sklearn.metrics import confusion_matrix
import numpy as np

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

    # Use a chunk size that fits comfortably in memory (e.g., 5000 rows)
    CHUNK_SIZE = 5000
    
    # Initialize accumulators for confusion matrix (tn, fp, fn, tp)
    # We assume binary classification (0, 1) or compatible logic.
    # Structure: {model_id: np.array([[tn, fp], [fn, tp]])}
    model_ids = [model_id] if model_id else list(reg.models.keys())
    
    # Validate model IDs first
    for mid in model_ids:
        if mid not in reg.models:
            raise HTTPException(status_code=400, detail=f"Unknown model_id: {mid}")

    accumulated_cms = {mid: np.zeros((2, 2), dtype=int) for mid in model_ids}
    
    processed_rows = 0

    try:
        # Read file in chunks
        for chunk in pd.read_csv(file.file, chunksize=CHUNK_SIZE):
            if target not in chunk.columns:
                 raise HTTPException(status_code=400, detail=f"Missing target column: {target}")
            
            # Simple validation on first chunk only to save perf, or check all if critical.
            # Here checking strict column presence for features
            missing_cols = [c for c in cols if c not in chunk.columns]
            if missing_cols:
                raise HTTPException(status_code=400, detail=f"Missing feature columns: {missing_cols[:5]}")

            y_true = chunk[target]
            X = chunk[cols]

            # Transform chunk
            Xt = reg.pipeline.transform(X)

            # Predict and accumulate for each model
            for mid in model_ids:
                m = reg.models[mid].model
                y_pred = m.predict(Xt)
                
                # Compute CM for this chunk
                # labels parameter ensures we get a 2x2 matrix even if some classes are missing in the chunk
                cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
                accumulated_cms[mid] += cm
            
            processed_rows += len(chunk)

    except Exception as e:
        # Handle parsing errors or other issues during chunk processing
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

    if processed_rows == 0:
         raise HTTPException(status_code=400, detail="CSV file is empty")

    results = []
    for mid, cm in accumulated_cms.items():
        tn, fp, fn, tp = cm.ravel()
        
        # Calculate metrics manually to avoid division by zero or re-invoking sklearn
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        results.append({
            "model_id": mid,
            "technique": reg.models[mid].technique,
            "metrics": {
                "accuracy": float(accuracy),
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
            }
        })

    return {"results": results}