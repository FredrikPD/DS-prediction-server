from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/models")
def list_models(request: Request):
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
    """
    Returns the valid mappings for categorical features.
    """
    import json
    from pathlib import Path
    
    # We assume 'encoding_mappings.json' is in artifacts alongside manifest
    # Registry has the manifest path, we can derive the artifact dir
    # manifest_path is stored in reg.
    # But Registry class might not expose the base path directly. 
    # Let's assume standard path: backend/artifacts/encoding_mappings.json
    
    # Better: get it from registry if we update registry to load it. 
    # For now, let's just read it directly from disk to save time, 
    # assuming standard location relative to this file.
    
    # predictions-server/backend/app/routes/models.py
    # -> ../../artifacts/encoding_mappings.json
    
    artifact_path = Path(__file__).resolve().parents[2] / "artifacts" / "encoding_mappings.json"
    
    if not artifact_path.exists():
        return {}
        
    try:
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
        return data
    except Exception as e:
        print(f"Error loading mappings: {e}")
        return {}