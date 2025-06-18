# FlowForm Technical Context

## Stack
- **Core**: Python 3.x + RhinoCommon
- **Platform**: Rhino 3D + Grasshopper
- **Interface**: Streamlit + FastAPI
- **Data**: Polars + JSON
- **Environment**: Windows 11, VS Code

## Structure
```
flow_form/
├── code/flow_form/models/    # BaffleCenterline, Baffle classes
├── code/interface/           # app.py (Streamlit), api_app.py (FastAPI)
├── code/data/               # JSON IPC files
└── memory-bank/             # Documentation
```

## Constraints
- **RhinoCommon Only**: All geometry operations must use Rhino API
- **File-based IPC**: JSON communication between Rhino ↔ Streamlit
- **Windows Primary**: Development focused on Windows 11
- **Real-time Performance**: UI must respond quickly to parameter changes

## Data Exchange
```json
// Baffle data: {"centerline_guid": "str", "centerline_name": "str", "depth": "num"}
// Edits: {"guid": "str", "property": "str", "value": "any"}
```

## Key Patterns
```python
# Geometric processing
for crv in sub_curves:
    if isinstance(crv, rg.LineCurve): # Line processing
    elif isinstance(crv, rg.ArcCurve): # Arc processing

# Caching
@property
def baffles(self):
    if self._baffle_cache: return self._baffle_cache
    # Generate and cache...
```
