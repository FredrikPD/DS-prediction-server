from sklearn.base import BaseEstimator, TransformerMixin
import numpy as np
import pandas as pd

class FlightPreProcessor(BaseEstimator, TransformerMixin):
    """
    Preprocessing pipeline for Flight Data.
    Applies Feature Generation and Encoding/Scaling using pre-computed mappings.
    """
    def __init__(self, mappings=None):
        self.mappings = mappings if mappings is not None else {}
        self.feature_order = [
            'Airline', 'Origin', 'Dest', 'Route', 'Hub_Airline', 
            'Month_cos', 'DayofMonth_cos', 'Is_Winter', 'Hub_x_Dest', 
            'Cancelled'
        ]
        # 'Set' is likely not needed for inference but kept for schema consistency if model expects it.
        # Actually models usually don't use 'Set'. 
        # But 'Combined_Flights_2022_Full_Prepared.csv' has it.
        # I'll include it if present, else default to 'Test'.
        
    def fit(self, X, y=None):
        # Stateless transformation based on pre-computed mappings
        return self
        
    def transform(self, X):
        X_out = X.copy()
        
        # --- 1. Feature Generation ---
        # Ensure string types
        for c in ['Origin', 'Dest', 'Airline']:
            if c in X_out.columns:
                X_out[c] = X_out[c].astype(str)
                
        # Derived
        if 'Origin' in X_out.columns and 'Dest' in X_out.columns:
            X_out['Route'] = X_out['Origin'] + "_" + X_out['Dest']
            
        if 'Airline' in X_out.columns and 'Origin' in X_out.columns:
            X_out['Hub_Airline'] = X_out['Airline'] + "_" + X_out['Origin']
            
        # Time
        # Assume Month/DayofMonth exist or derive from FlightDate
        if 'FlightDate' in X_out.columns and ('Month' not in X_out.columns or 'DayofMonth' not in X_out.columns):
            dt = pd.to_datetime(X_out['FlightDate'])
            X_out['Month'] = dt.dt.month
            X_out['DayofMonth'] = dt.dt.day
            
        # Cyclical
        # Mappings for Month_cos/DayofMonth_cos are in JSON, 
        # BUT they are math formulas. 
        # The JSON 'Month_cos' keys are the Month INTEGERS (as strings). 
        # So we can map Month -> Validated Scaled Value.
        # This is safer than re-calculating cos and scaling, ensuring exact match.
        
        # Hub_x_Dest
        # This is tricky. In JSON we have 'Hub_x_Dest' as list of [Hub, Dest, Val].
        # Or 'Hub_x_Dest_Sample' if too large.
        # My recovery script put the FULL list in 'Hub_x_Dest' if <50k. 
        # I should check if it was full list or sample. 
        # Output said "Warning: Diff unique...".
        # I should handle the lookup efficiently.
        # A dictionary keyed by (Hub, Dest) is best.
        
        # --- 2. Application of Mappings ---
        
        # Helper to apply map with default 0.0
        def apply_map(series, mapping_dict):
            # mapping_dict keys are strings
            return series.astype(str).map(mapping_dict).fillna(0.0)

        # A. Standard Categoricals
        for col in ['Airline', 'Origin', 'Dest', 'Route', 'Hub_Airline']:
            if col in self.mappings:
                X_out[col] = apply_map(X_out[col], self.mappings[col])
                
        # B. Cyclical (Map from Integer ID)
        if 'Month' in X_out.columns and 'Month_cos' in self.mappings:
            X_out['Month_cos'] = apply_map(X_out['Month'], self.mappings['Month_cos'])
            
        if 'DayofMonth' in X_out.columns and 'DayofMonth_cos' in self.mappings:
            X_out['DayofMonth_cos'] = apply_map(X_out['DayofMonth'], self.mappings['DayofMonth_cos'])
            
        # C. Is_Winter
        if 'Month' in X_out.columns:
            # Check for mapping key (Is_Winter or Is_Winter_from_Month)
            key = 'Is_Winter' if 'Is_Winter' in self.mappings else 'Is_Winter_from_Month'
            if key in self.mappings:
                X_out['Is_Winter'] = apply_map(X_out['Month'], self.mappings[key])
                
        # D. Hub_x_Dest
        # Construct lookup key if input has clean Hub/Dest
        # However, the mapping might be stored as list.
        # I will convert list to dict in __init__ if needed, but easier if done before.
        # Let's assume self.mappings['Hub_x_Dest'] is a dict or we convert it here.
        
        if 'Hub_x_Dest' in self.mappings:
            # We need to construct the interactions
            # Use the generated Hub_Airline and existing Dest
            hubs = X_out['Hub_Airline'] # This is currently replaced by floats in step A!
            # WAIT! 
            # I replaced X_out['Hub_Airline'] with floats above.
            # I cannot form Hub_x_Dest using the *mapped* values easily if the key is string.
            # I must form the keys BEFORE mapping the components.
            pass # See revised logic below
            
        # E. Cancelled
        if 'Cancelled' in X_out.columns and 'Cancelled' in self.mappings:
            X_out['Cancelled'] = apply_map(X_out['Cancelled'], self.mappings['Cancelled'])
            
        # --- REVISED LOGIC flow ---
        # 1. Generate Strings
        # 2. Generate Interaction String Keys
        # 3. Map everything
        
        # We need to keep strings to form interactions. 
        # So we shouldn't overwrite inplace until end.
        
        return X_out

    def transform_revised(self, X):
        X_in = X.copy()
        X_out = pd.DataFrame(index=X_in.index)
        
        # 1. Feature Gen (Strings/Ints)
        # Ensure string types
        for c in ['Origin', 'Dest', 'Airline']:
            if c in X_in.columns:
                X_in[c] = X_in[c].astype(str)
                
        # Derived
        if 'Origin' in X_in.columns and 'Dest' in X_in.columns:
            X_in['Route'] = X_in['Origin'] + "_" + X_in['Dest']
            
        if 'Airline' in X_in.columns and 'Origin' in X_in.columns:
            X_in['Hub_Airline'] = X_in['Airline'] + "_" + X_in['Origin']
            
        # Time
        if 'FlightDate' in X_in.columns and ('Month' not in X_in.columns or 'DayofMonth' not in X_in.columns):
            dt = pd.to_datetime(X_in['FlightDate'])
            X_in['Month'] = dt.dt.month
            X_in['DayofMonth'] = dt.dt.day
            
        # 2. Applying Mappings
        def get_map(col): return self.mappings.get(col, {})
        def apply(col_name, source_col, default=0.0):
            m = get_map(col_name)
            return X_in[source_col].astype(str).map(m).fillna(default)

        # Standard
        X_out['Airline'] = apply('Airline', 'Airline')
        X_out['Origin'] = apply('Origin', 'Origin')
        X_out['Dest'] = apply('Dest', 'Dest')
        X_out['Route'] = apply('Route', 'Route')
        X_out['Hub_Airline'] = apply('Hub_Airline', 'Hub_Airline')
        
        # Cyclical
        X_out['Month_cos'] = apply('Month_cos', 'Month')
        if 'Month' in self.mappings:
             X_out['Month_cos'] = apply('Month', 'Month')
             
        X_out['DayofMonth_cos'] = apply('DayofMonth_cos', 'DayofMonth')
        if 'DayofMonth' in self.mappings:
             X_out['DayofMonth_cos'] = apply('DayofMonth', 'DayofMonth')
        
        # Is_Winter
        w_key = 'Is_Winter' if 'Is_Winter' in self.mappings else 'Is_Winter_from_Month'
        X_out['Is_Winter'] = apply(w_key, 'Month')
        
        # Hub_x_Dest
        # We assume preprocess_interaction_map was called on init/load
        if 'Hub_x_Dest' in self.mappings:
             X_out['Hub_x_Dest'] = self.transform_hub_dest(X_in)
        
        # Cancelled
        if 'Cancelled' in X_in.columns:
            X_out['Cancelled'] = apply('Cancelled', 'Cancelled', default=0.0)
            
        # Set
        X_out['Set'] = 'Test' # Default for inference
        
        # Final selection
        req_cols = [c for c in self.feature_order if c in X_out.columns]
        return X_out[req_cols]

    # Use the revised logic
    transform = transform_revised

    def preprocess_interaction_map(self):
        # Convert Hub_x_Dest list to dict if needed
        # Expected format in JSON: [[Hub, Dest, Val], ...]
        if 'Hub_x_Dest' in self.mappings:
            data = self.mappings['Hub_x_Dest']
            if isinstance(data, list):
                new_map = {}
                for item in data:
                    if len(item) == 3:
                        h, d, v = item
                        key = f"{h}_{d}" # Match generation logic?
                        # Wait, in get_mappings_by_frequency I used "Hub | Dest" as Key.
                        # But here I am reconstructing.
                        # Let's match the Hub_Airline string and Dest string.
                        # Hub_Airline is "Airline_Origin".
                        # So Key = "Airline_Origin" + "_" + "Dest" ?
                        # No, simpler. Using the "Hub_Airline" column and "Dest" column.
                        # Key = str(Hub) + "_" + str(Dest) (arbitrary, as long as consistent)
                        key = str(h) + "_" + str(d)
                        new_map[key] = v
                self.mappings['Hub_x_Dest'] = new_map

    def transform_hub_dest(self, X_in):
        # Helper to map Hub_x_Dest
        if 'Hub_x_Dest' not in self.mappings: return None
        
        # Keys
        keys = X_in['Hub_Airline'].astype(str) + "_" + X_in['Dest'].astype(str)
        return keys.map(self.mappings['Hub_x_Dest']).fillna(0.0)

