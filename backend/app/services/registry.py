import json
from dataclasses import dataclass
from pathlib import Path
import joblib
from app.services.flight_preprocessing import FlightPreProcessor

@dataclass
class ModelInfo:
    id: str
    technique: str
    model: object
    hyperparams: dict

class Registry:
    def __init__(self, manifest_path: str):
        self.manifest_path = Path(manifest_path)
        self.manifest = None
        self.pipeline = None
        self.models: dict[str, ModelInfo] = {}

    def _resolve(self, p: str | None) -> Path | None:
        if not p:
            return None
        path = Path(p)
        if path.is_absolute():
            return path
        # Relative paths are resolved against the manifest's location
        return (self.manifest_path.parent / path).resolve()

    def load(self):
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")

        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))

        try:
            # Inject flight_preprocessing into sys.modules to support unpickling legacy objects
            import sys
            import app.services.flight_preprocessing
            sys.modules['flight_preprocessing'] = app.services.flight_preprocessing

            pipeline_path = self._resolve(self.manifest["pipeline"]["path"])
            if pipeline_path and pipeline_path.exists():
                self.pipeline = joblib.load(pipeline_path)
                
                try:
                    obj = self.pipeline
                    if hasattr(obj, 'steps'):
                         for name, step in obj.steps:
                             if hasattr(step, 'feature_order'):
                                 step.feature_order = [c for c in step.feature_order if c not in ['Set', 'Cancelled']]
                    elif hasattr(obj, 'feature_order'):
                         # Remove training-specific columns to ensure compatibility with inference data
                         obj.feature_order = [c for c in obj.feature_order if c not in ['Set', 'Cancelled']]
                except Exception as patch_e:
                    print(f"Warning: Failed to patch pipeline: {patch_e}")
                
                self.full_pipeline = self.pipeline
            else:
                if not pipeline_path:
                     raise ValueError("Pipeline path is empty or invalid in manifest.")
                raise FileNotFoundError(f"Pipeline not found: {pipeline_path}")
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to load main pipeline: {e}")
            raise e

        self.models = {}
        for m in self.manifest["models"]:
            try:
                model_path = self._resolve(m["path"])
                if not model_path.exists():
                    raise FileNotFoundError(f"Model not found: {model_path}")
                # Load the model artifact using joblib
                model_obj = joblib.load(model_path)

                hp = {}
                hp_path = self._resolve(m.get("hyperparams_path"))
                if hp_path and hp_path.exists():
                    hp = json.loads(hp_path.read_text(encoding="utf-8"))

                self.models[m["id"]] = ModelInfo(
                    id=m["id"],
                    technique=m.get("technique", m["id"]),
                    model=model_obj,
                    hyperparams=hp,
                )
            except Exception as e:
                print(f"CRITICAL ERROR: Failed to load model '{m['id']}': {e}")
                raise e

        if self.manifest["default_model"] not in self.models:
            raise ValueError("default_model not found among loaded models")