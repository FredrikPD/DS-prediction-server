from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/models")
def list_models(request: Request):
    reg = request.app.state.registry
    return {
        "default_model": reg.manifest["default_model"],
        "target_column": reg.manifest["target_column"],
        "target_column": reg.manifest["target_column"],
        # Only expose 5 features for testing ease
        "feature_columns": ["Airline", "Origin", "Dest", "DepDelay", "Distance"],
        "models": [
            {
                "id": mi.id,
                "technique": mi.technique,
                "hyperparams": mi.hyperparams
            }
            for mi in reg.models.values()
        ],
    }