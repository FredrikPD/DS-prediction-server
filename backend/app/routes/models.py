from fastapi import APIRouter, Request
import json
from pathlib import Path

router = APIRouter()

@router.get("/models")
def list_models(request: Request):
    # Retrieve available models from the global registry
    reg = request.app.state.registry
    return {
        "default_model": reg.manifest.get("default_model", ""),
        "target_column": reg.manifest.get("target_column", ""),
        "feature_columns": reg.manifest.get("feature_columns", []),
        "models": [
            {
                "id": mi.id,
                "technique": mi.technique,
                "hyperparams": mi.hyperparams
            }
            for mi in reg.models.values()
        ],
    }

@router.get("/mappings")
def get_mappings(request: Request):
    # Load categorical mappings from the artifact file
    artifact_path = Path(__file__).resolve().parents[2] / "artifacts" / "encoding_mappings.json"
    
    if not artifact_path.exists():
        return {}
        
    try:
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
        return data
    except Exception as e:
        print(f"Error loading mappings: {e}")
        return {}