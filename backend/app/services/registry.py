import json
from dataclasses import dataclass
from pathlib import Path
import joblib

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
        # ✅ resolve relative to manifest folder
        return (self.manifest_path.parent / path).resolve()

    def load(self):
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")

        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))

        # ---- Load pipeline ----
        pipeline_path = self._resolve(self.manifest["pipeline"]["path"])
        if not pipeline_path.exists():
            raise FileNotFoundError(f"Pipeline not found: {pipeline_path}")
        self.pipeline = joblib.load(pipeline_path)

        # ---- Load models ----
        self.models = {}
        for m in self.manifest["models"]:
            model_path = self._resolve(m["path"])
            if not model_path.exists():
                raise FileNotFoundError(f"Model not found: {model_path}")
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

        if self.manifest["default_model"] not in self.models:
            raise ValueError("default_model not found among loaded models")