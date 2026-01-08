# Inference Pipeline Description

This document details the **Inference Pipeline** (`preparation_pipeline.joblib`), which transforms new, raw flight data into the exact format required by the trained models for prediction.

## 1. Pipeline Overview
The inference pipeline is a stateless transformer that applies pre-computed mappings to raw input data. It ensures that new data (e.g., from a web form) is encoded and scaled exactly as the training data was.

**Scope**: Feature Generation -> Mapping Application (Encoding + Scaling).

## 2. Step-by-Step Description

### Step 1: Feature Generation
*Derives necessary features from raw inputs.*
*   **Route**: Concatenation of `Origin` + "_" + `Dest`.
*   **Hub_Airline**: Concatenation of `Airline` + "_" + `Origin`.
*   **Time Features**: Extracts `Month` and `DayofMonth` from `FlightDate` (if present).
*   **Cyclical Features**:
    *   `Month_cos`: Mapped from `Month`.
    *   `DayofMonth_cos`: Mapped from `DayofMonth`.
*   **Is_Winter**: Binary flag derived from `Month` (0 or 1).
*   **Hub_x_Dest**: Interaction term derived from `Hub_Airline` and `Dest`.

### Step 2: Mapping Application (Encoding & Scaling)
*Applies pre-computed `String -> Scaled Float` mappings to all categorical and cyclical features.*

*   **Technique**: Direct mapping.
    *   Original strings (e.g., "United Air Lines Inc.", "JFK") are looked up in `encoding_mappings.json`.
    *   The values in this JSON are the final **Standard Scaled** values recovered from the training pipeline.
    *   **Unknown Values**: Mapped to `0.0` (Dataset Mean/Default).

*   **Features Processed**:
    *   `Airline`
    *   `Origin`
    *   `Dest`
    *   `Route`
    *   `Hub_Airline`
    *   `Month_cos` (Mapped from integer Month)
    *   `DayofMonth_cos` (Mapped from integer Day)
    *   `Is_Winter`
    *   `Hub_x_Dest`

## 3. Parametrization Summary
*Since this is an inference pipeline, "parameters" are the stored mappings themselves.*

| Feature | Transformation Logic | Fallback (Unknowns) |
| :--- | :--- | :--- |
| **Categoricals** | Lookup in `encoding_mappings.json` | `0.0` |
| **Cyclical** | Lookup Month/Day Int -> Scaled Cosine Float | `0.0` |
| **Hub_x_Dest** | Lookup (Airline_Origin + Dest) -> Scaled Interaction Float | `0.0` |

*Note: Steps like Outlier Removal, Feature Selection, and Balancing are **Training-Only** steps and are NOT applied during inference, as the model expects to make predictions on valid, real-world data distributions.*
