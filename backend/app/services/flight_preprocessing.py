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
        
    def fit(self, X, y=None):
        return self
        
    def transform(self, X):
        X_in = X.copy()
        X_out = pd.DataFrame(index=X_in.index)
        
        for c in ['Origin', 'Dest', 'Airline']:
            if c in X_in.columns:
                # Ensure categorical features are treated as strings
                X_in[c] = X_in[c].astype(str)
                
        if 'Origin' in X_in.columns and 'Dest' in X_in.columns:
            # Create Route feature by combining Origin and Dest
            X_in['Route'] = X_in['Origin'] + "_" + X_in['Dest']
            
        if 'Airline' in X_in.columns and 'Origin' in X_in.columns:
            X_in['Hub_Airline'] = X_in['Airline'] + "_" + X_in['Origin']
            
        if 'FlightDate' in X_in.columns and ('Month' not in X_in.columns or 'DayofMonth' not in X_in.columns):
            # Extract temporal features from FlightDate if not already present
            dt = pd.to_datetime(X_in['FlightDate'])
            X_in['Month'] = dt.dt.month
            X_in['DayofMonth'] = dt.dt.day
            
        def get_map(col): return self.mappings.get(col, {})
        def apply(col_name, source_col, default=0.0):
            # Apply learned mapping to column, filling unknowns with default risk value
            m = get_map(col_name)
            return X_in[source_col].astype(str).map(m).fillna(default)

        X_out['Airline'] = apply('Airline', 'Airline')
        X_out['Origin'] = apply('Origin', 'Origin')
        X_out['Dest'] = apply('Dest', 'Dest')
        X_out['Route'] = apply('Route', 'Route')
        X_out['Hub_Airline'] = apply('Hub_Airline', 'Hub_Airline')
        
        X_out['Month_cos'] = apply('Month_cos', 'Month')
        if 'Month' in self.mappings:
             X_out['Month_cos'] = apply('Month', 'Month')
             
        X_out['DayofMonth_cos'] = apply('DayofMonth_cos', 'DayofMonth')
        if 'DayofMonth' in self.mappings:
             X_out['DayofMonth_cos'] = apply('DayofMonth', 'DayofMonth')
        
        w_key = 'Is_Winter' if 'Is_Winter' in self.mappings else 'Is_Winter_from_Month'
        X_out['Is_Winter'] = apply(w_key, 'Month')
        
        if 'Hub_x_Dest' in self.mappings:
             X_out['Hub_x_Dest'] = self.transform_hub_dest(X_in)
        
        if 'Cancelled' in X_in.columns:
            X_out['Cancelled'] = apply('Cancelled', 'Cancelled', default=0.0)
            
        X_out['Set'] = 'Test'
        
        req_cols = [c for c in self.feature_order if c in X_out.columns]
        return X_out[req_cols]



    def preprocess_interaction_map(self):
        if 'Hub_x_Dest' in self.mappings:
            data = self.mappings['Hub_x_Dest']
            if isinstance(data, list):
                # Convert list-based storage to efficient dictionary lookup
                new_map = {}
                for item in data:
                    if len(item) == 3:
                        h, d, v = item
                        key = str(h) + "_" + str(d)
                        new_map[key] = v
                self.mappings['Hub_x_Dest'] = new_map

    def transform_hub_dest(self, X_in):
        if 'Hub_x_Dest' not in self.mappings: return None
        
        keys = X_in['Hub_Airline'].astype(str) + "_" + X_in['Dest'].astype(str)
        return keys.map(self.mappings['Hub_x_Dest']).fillna(0.0)

