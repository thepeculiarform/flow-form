# FlowForm

A Python-based architectural design tool for generating and managing baffle systems in Rhino using parametric design principles.

## Project Overview

FlowForm is a specialized tool for creating architectural baffle systems with the following key features:

- Parametric baffle generation along centerlines
- Automated handling of baffle connections and spacing
- Web-based visualization interface using Streamlit
- Real-time data monitoring and analysis

## Structure

```
flow_form/
├── code/
│   ├── flow_form/           # Core Python package
│   │   ├── __init__.py
│   │   ├── Project.py      # Main project classes
│   │   └── Utils.py        # Utility functions
│   ├── interface/          # Web interface components
│   │   ├── streamlit_app.py # Streamlit application
│   │   └── requirements.txt
│   └── data.json          # Project data storage
├── resources/             # Material textures and resources
└── topo.py               # Topological operations
```

## Features

### Baffle System Generation
- Dynamic baffle creation along centerlines
- Automatic length constraints and segmentation
- Parametric control of:
  - Maximum baffle length (default: 2800mm)
  - Connection extensions (54mm)
  - Break gaps (20mm)
  - Material thickness (12mm)

### Visualization Interface
- Real-time data monitoring through Streamlit
- Interactive data visualizations
- Multiple view options:
  - Table view
  - List view
  - Graph visualization

## Installation

1. Install required dependencies:
```bash
cd code/interface
pip install -r requirements.txt
```

2. Launch the Streamlit interface:
```bash
streamlit run streamlit_app.py
```

## Usage

The system can be used through:
1. Rhino/Grasshopper components
2. Python API
3. Streamlit web interface

### Web Interface
Access the visualization dashboard using Streamlit's local development server

## Development Status

Current version: v0.2.6

See [CHANGELOG.md](CHANGELOG.md) for detailed version history and planned features.

## Requirements

- Python 3.x
- Rhino 3D
- Streamlit
- Pandas
- Numpy

## License

[License information pending]