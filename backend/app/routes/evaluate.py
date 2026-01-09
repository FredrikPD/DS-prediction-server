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

    # Process large files in chunks to maintain memory stability
    CHUNK_SIZE = 5000
    
    model_ids = [model_id] if model_id else list(reg.models.keys())
    
    for mid in model_ids:
        if mid not in reg.models:
            raise HTTPException(status_code=400, detail=f"Unknown model_id: {mid}")

    all_y_true = []
    all_y_probs = {mid: [] for mid in model_ids}
    
    processed_rows = 0

    try:
        for chunk in pd.read_csv(file.file, chunksize=CHUNK_SIZE):
            if target not in chunk.columns:
                 raise HTTPException(status_code=400, detail=f"Missing target column: {target}")
            
            y_chunk = chunk[target].astype(int).values
            all_y_true.append(y_chunk)
            
            X = chunk.drop(columns=[target], errors='ignore')

            if hasattr(reg, 'full_pipeline') and reg.full_pipeline:
                 Xt = reg.full_pipeline.transform(X)
            else:
                 Xt = reg.pipeline.transform(X)

            for mid in model_ids:
                m = reg.models[mid].model
                
                if hasattr(m, "predict_proba"):
                    try:
                        probs = m.predict_proba(Xt)
                        if probs.shape[1] == 2:
                            pos_probs = probs[:, 1]
                        else:
                            # Fallback if probability shape is unexpected
                            pos_probs = m.predict(Xt).astype(float)
                    except Exception:
                         pos_probs = m.predict(Xt).astype(float)
                else:
                    # Model does not support probabilities, use hard predictions
                    pos_probs = m.predict(Xt).astype(float)
                
                all_y_probs[mid].append(pos_probs)
            
            processed_rows += len(chunk)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

    if processed_rows == 0:
         raise HTTPException(status_code=400, detail="CSV file is empty")
    
    # Aggregate all chunks for final metric calculation
    y_true_all = np.concatenate(all_y_true)
    
    results = []
    
    for mid in model_ids:
        y_prob_all = np.concatenate(all_y_probs[mid])
        
        y_pred_std = (y_prob_all >= 0.5).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true_all, y_pred_std, labels=[0, 1]).ravel()
        
        # Helper for safe division to avoid division by zero errors
        def safe_div(n, d): return n / d if d > 0 else 0.0
        std_metrics = {
            "accuracy": safe_div(tp + tn, tp + tn + fp + fn),
            "precision": safe_div(tp, tp + fp),
            "recall": safe_div(tp, tp + fn),
            "f1": safe_div(2 * tp, 2 * tp + fp + fn)
        }
        
        best_th = 0.5
        best_f1 = std_metrics["f1"]
        best_metrics = std_metrics.copy()
        
        # Optimize classification threshold to maximize F1 score
        thresholds = np.linspace(0.05, 0.95, 19)
        
        for th in thresholds:
            y_p = (y_prob_all >= th).astype(int)
            tp_op = ((y_p == 1) & (y_true_all == 1)).sum()
            fp_op = ((y_p == 1) & (y_true_all == 0)).sum()
            fn_op = ((y_p == 0) & (y_true_all == 1)).sum()
            
            prec_op = safe_div(tp_op, tp_op + fp_op)
            rec_op = safe_div(tp_op, tp_op + fn_op)
            f1_op = safe_div(2 * prec_op * rec_op, prec_op + rec_op)
            
            if f1_op > best_f1:
                best_f1 = f1_op
                best_th = th
                best_metrics = {
                    "accuracy": safe_div(tp_op + (len(y_true_all) - tp_op - fp_op - fn_op), len(y_true_all)),
                    "precision": prec_op,
                    "recall": rec_op,
                    "f1": f1_op
                }

        results.append({
            "model_id": mid,
            "technique": reg.models[mid].technique,
            "metrics": best_metrics,
            "standard_metrics": std_metrics,
            "optimal_threshold": float(best_th)
        })

    return {"results": results}