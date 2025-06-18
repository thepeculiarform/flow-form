# FlowForm System Patterns

## Architecture
Modular, class-based with separation: geometric processing, data management, user interface.

## Core Components
- **Models** (`BaffleCenterline`, `Baffle`): RhinoCommon geometry with instance registration & caching
- **Data Exchange**: File-based IPC via JSON with timestamp detection
- **Interfaces**: Streamlit (user) + FastAPI (programmatic) with PID management

## Key Patterns
- **Composition**: BaffleCenterline contains Baffles
- **Factory**: Curve-type-specific geometry generation
- **Strategy**: Different algorithms for Line/Arc/Closed curves
- **Observer**: File modification monitoring for UI updates

## Critical Paths
1. **Generation**: Centerline → Analysis → Segmentation → Baffles → Connections
2. **Sync**: Rhino → JSON → UI → Edits → JSON → Rhino
3. **Control**: Interface → Edit → Detection → Update → Refresh

## Performance
- **Caching**: `_baffle_cache` for expensive operations
- **File I/O**: Timestamp-based change detection
- **UI**: Session state management, incremental loading
