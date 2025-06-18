# FlowForm Active Context

## Current Focus
v0.2.8 development - Streamlit integration with dual interface (Streamlit + FastAPI) operational.

## Recent Work
- Real-time baffle data editing through Streamlit interface
- JSON-based IPC working between Rhino/Grasshopper and web
- Process management with PID tracking implemented
- Enhanced geometric models (`BaffleCenterline`, `Baffle`)

## Immediate Next Steps
1. UI polish and responsiveness improvements
2. Strengthen error handling in data exchange
3. Performance optimization for larger datasets
4. Comprehensive testing of Rhino ↔ Streamlit integration

## Key Decisions
- **File-based IPC**: Simple, reliable JSON communication (consider WebSocket later)
- **Dual Interface**: Streamlit (user) + FastAPI (programmatic) for flexibility
- **RhinoCommon Only**: Ensures Rhino compatibility, requires performance awareness

## Development Insights
- Composition pattern (BaffleCenterline → Baffle) works well
- Property-based caching essential for performance
- Timestamp checking crucial for reliable file sync
- Test geometric operations in Grasshopper first

## Current Issues
- Concurrent JSON file access conflicts
- Some geometric edge cases need handling
- UI refresh timing optimization needed
- Cross-platform testing required

## Active Files
- `code/interface/app.py`: Streamlit interface
- `code/interface/api_app.py`: FastAPI backend
- `code/flow_form/models/baffles.py`: Core geometry
- `code/data/baffle_data_edits.json`: IPC data
