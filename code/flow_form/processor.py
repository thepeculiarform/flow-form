from dataclasses import dataclass
import Rhino as rh
import Rhino.Geometry as rg
import scriptcontext as sc
import numpy as np
import json
import os
import polars as pl
from System import Guid

import flow_form as pjct


import sys
sys.path.append(project_library_path)

import flow_form as pjct



@dataclass
class BaffleConfig:
    """Configuration for baffle processing"""
    area_layer: str
    centerline_layer: str
    baffle_depth: float
    max_baffle_length: float
    thickness: float
    project_root: str = r"E:/Projects/tpf/rhino/flow_form/code"
    
    @property
    def data_file_out(self) -> str:
        return os.path.join(self.project_root, "data", "baffle_data_out.json")
        
    @property
    def edits_file_in(self) -> str:
        return os.path.join(self.project_root, "data", "baffle_edits_in.json")

class BaffleManager:
    """Manages baffle processing and Rhino interactions"""
    def __init__(self, config: BaffleConfig):
        self.config = config
        self.clear_storage()
        
    def clear_storage(self) -> None:
        """Reset all storage containers"""
        self.hanging_points = []
        self.surfaces = []
        self.solids = []
        self.planes = []
        self.frames = []
        self.baffle_data = []
        self.needs_recompute = False
        
    def process_all(self):
        """Execute main processing pipeline"""
        if self.process_edits():
            self.needs_recompute = True
        
        # Generate geometry first
        self.generate_baffles()
        
        # Collect data for Streamlit interface
        self._collect_polars_data()
        
        # Write data file
        self.write_output_data()
        
        # Return only the 5 expected values for Grasshopper
        return (
            self.hanging_points,
            self.surfaces,
            self.solids,
            [frame[1] for frame in self.frames],
            self.needs_recompute
        )
    
    def _collect_polars_data(self):
        """Collect data for polars DataFrame - separate from geometry generation"""
        # Since data is already collected in _process_single_baffle via _collect_baffle_data,
        # we don't need to do anything here
        pass

    def _read_edits(self) -> list:
        """Read and clear edits file"""
        if not os.path.exists(self.config.edits_file_in):
            return []
            
        try:
            with open(self.config.edits_file_in, 'r') as f:
                content = f.read()
                edits = json.loads(content) if content.strip() else []
            
            # Clear file after reading
            with open(self.config.edits_file_in, 'w') as f:
                f.write("[]")
            return edits
        except Exception as e:
            print(f"Error reading edits: {e}")
            return []

    def process_edits(self) -> bool:
        """Apply edits to Rhino objects"""
        edits = self._read_edits()
        if not edits:
            return False
            
        edits_applied = 0
        original_doc = sc.doc
        try:
            sc.doc = rh.RhinoDoc.ActiveDoc
            for edit in edits:
                if self._apply_single_edit(edit):
                    edits_applied += 1
        finally:
            sc.doc = original_doc
            
        return edits_applied > 0
        
    def _apply_single_edit(self, edit: dict) -> bool:
        """Apply a single edit to a Rhino object"""
        try:
            guid_str = edit.get('centerline_guid')
            updates = edit.get('update', {})
            depth = updates.get('depth')
            
            if not all([guid_str, depth is not None]):
                return False
                
            obj = sc.doc.Objects.FindId(Guid(guid_str))
            if not (obj and obj.IsValid):
                return False
                
            obj.Attributes.SetUserString('depth', str(depth))
            return obj.CommitChanges()
        except Exception as e:
            print(f"Error applying edit: {e}")
            return False
        
    def generate_baffles(self) -> None:
        """Generate baffle geometry and collect data from centerline curves"""
        curve_layer = sc.doc.Layers.Find(self.config.centerline_layer, True)
        if not curve_layer:
            print(f"Warning: Layer '{self.config.centerline_layer}' not found")
            return
            
        layer_objects = sc.doc.Objects.FindByLayer(sc.doc.Layers.FindIndex(curve_layer))
        
        # Filter for valid curve objects only
        centerlines = [
            obj for obj in layer_objects 
            if isinstance(obj, rh.DocObjects.CurveObject) and obj.IsValid
        ]
        
        if not centerlines:
            print(f"No valid curves found on layer '{self.config.centerline_layer}'")
            return
            
        for i, obj in enumerate(centerlines):
            self._process_single_baffle(obj, i)
            
        self._create_gripper_group()
        self._create_baffle_group()

    def _process_single_baffle(self, obj: rh.DocObjects.RhinoObject, index: int) -> None:
        """Process individual baffle centerline with its UserText properties"""
        # Get depth with better error handling
        try:
            depth_str = obj.Attributes.GetUserString("depth")
            depth = float(depth_str) if depth_str else self.config.baffle_depth
        except (ValueError, TypeError):
            depth = self.config.baffle_depth
            print(f"Warning: Invalid depth value for {obj.Id}, using default: {depth}")
        
        centerline = pjct.Project.BaffleCenterline(
            name=f"Centerline {pjct.Utils.alpha[index].upper()}",
            centerline=obj,
            max_baffle_length=self.config.max_baffle_length,
            depth=depth,
            thickness=self.config.thickness
        )
        
        # Process geometry
        if centerline.baffles:  # Only process if baffles were generated
            self.hanging_points.extend(centerline.hanging_points)
            self._add_connection_planes(centerline)
            self._add_baffle_geometry(centerline)
            self._collect_baffle_data(obj, centerline)
        else:
            print(f"Warning: No baffles generated for centerline {centerline.name}")

    def _add_connection_planes(self, centerline):
        """Generate connection planes for grippers"""
        for curve in centerline.get_connection_lines():
            offset = curve.Offset(rg.Plane.WorldXY, 1, 0.01, rg.CurveOffsetCornerStyle.Sharp)[0]
            plane = rg.Plane(
                curve.PointAtMid, 
                offset.PointAtMid - curve.PointAtMid,
                curve.PointAtEnd - curve.PointAtMid
            )
            self.planes.append(plane)

    def _add_baffle_geometry(self, centerline) -> None:
        """Generate baffle surfaces and solids"""
        for baffle in centerline.baffles:
            b_srf = baffle.surface(depth=-centerline.depth)
            self.surfaces.append(b_srf)

            offset = rg.Brep.CreateOffsetBrep(
                b_srf.ToBrep(), 
                -self.config.thickness/2, 
                False, True, 0.01
            )[0][0]
            solid = rg.Brep.CreateOffsetBrep(
                offset, 
                self.config.thickness, 
                True, True, 0.01
            )[0][0]
            self.solids.append(solid)
            self.frames.extend(baffle.strut_frames())

    def _collect_baffle_data(self, obj: rh.DocObjects.RhinoObject, centerline) -> None:
        """Collect baffle data for JSON output"""
        for baffle in centerline.baffles:
            self.baffle_data.append({
                "baffle_id": baffle.name,
                "centerline_guid": str(obj.Id),
                "centerline_name": centerline.name,
                "length": round(baffle.baffle_curve.ToNurbsCurve().GetLength(), 2),
                "depth": centerline.depth,
                "type": type(baffle.baffle_curve).__name__
            })

    def _create_gripper_group(self) -> None:
        """Create gripper group in Rhino"""
        group_name = "plate_withGrippers"
        gripper_group = sc.doc.Groups.FindName(group_name)
        if (gripper_group):
            pjct.Utils.delete_group_items(group_name)
            sc.doc.Groups.Delete(gripper_group)

        gripper_group = sc.doc.Groups.Add(group_name)
        world = rg.Plane.WorldXY
        normal_vec = rg.Vector3d(0, 0, 1)
        block = sc.doc.InstanceDefinitions.Find(group_name)

        for plane in self.planes:
            if plane.ZAxis * normal_vec < 0:
                plane.Flip()
            plane.Rotate(np.radians(90), normal_vec)
            xform = rg.Transform.PlaneToPlane(world, plane)
            instance_id = sc.doc.Objects.AddInstanceObject(block.Index, xform)
            sc.doc.Groups.AddToGroup(gripper_group, instance_id)

    def _create_baffle_group(self) -> None:
        """Create baffle group in Rhino"""
        group_name = "baffles"
        baffle_group = sc.doc.Groups.FindName(group_name)
        
        if baffle_group:
            pjct.Utils.delete_group_items(group_name)
            sc.doc.Groups.Delete(baffle_group)
            
        baffle_group = sc.doc.Groups.Add(group_name)
        
        for baffle in self.solids:
            instance_id = sc.doc.Objects.Add(baffle)
            instance_object = sc.doc.Objects.Find(instance_id)
            sc.doc.Groups.AddToGroup(baffle_group, instance_object.Id)

    def write_output_data(self) -> None:
        """Write collected data to JSON file"""
        if not self.baffle_data:
            self._write_empty_json()
            return
            
        try:
            df = pl.DataFrame(self.baffle_data)
            os.makedirs(os.path.dirname(self.config.data_file_out), exist_ok=True)
            df.write_json(self.config.data_file_out, row_oriented=True)
        except Exception as e:
            print(f"Error writing data: {e}")
            self._write_empty_json()

    def _write_empty_json(self) -> None:
        """Write empty JSON array when no data exists"""
        try:
            os.makedirs(os.path.dirname(self.config.data_file_out), exist_ok=True)
            with open(self.config.data_file_out, 'w') as f:
                json.dump([], f)
        except Exception as e:
            print(f"Error writing empty JSON: {e}")