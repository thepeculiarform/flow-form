import Rhino as rh
import Rhino.Geometry as rg
import scriptcontext as sc




""" BAFFLE CENTERLINE CLASS """
class BaffleCenterline:
    """
    Represents a centerline path for generating a series of baffle elements
    with appropriate spacing, connections, and geometric properties
    """
    instances = []
    def __init__(self, name: str, 
                 centerline: rh.DocObjects.ObjectType.Curve, 
                 max_baffle_length=2800, 
                 extend=54, 
                 break_gap=20, 
                 depth=None,
                 thickness=12):
        
        # Initialize baffle centerline with geometry and parameters
        self.name = name
        self.centerline = centerline
        self.max_baffle_length = max_baffle_length  # Maximum length for a single baffle segment
        self.depth = depth                          # Depth of the baffle
        self.extend = extend                        # Extension length at connections
        self.break_gap = break_gap                  # Gap between baffle segments
        self.thickness = thickness                  # Thickness of the baffle
        self._baffle_cache = None 

        # Register instance
        BaffleCenterline.instances.append(self)

    def get_offset(self, offset):   
        # Generate parallel offset curves on both sides of centerline
        return [
            self.centerline.Geometry.Offset(rg.Plane.WorldXY, num * (offset/2), 0.001, rg.CurveOffsetCornerStyle.NONE)[0] 
            for num in (-1, 1)
        ]

    def get_arcs(self):
        # Extract all arc segments from centerline
        return [crv for crv in self.centerline.Geometry.GetSubCurves() if type(crv) == rg.ArcCurve]

    def get_lines(self):
        # Extract all line segments from centerline
        return [crv.Line for crv in self.centerline.Geometry.GetSubCurves() if type(crv) == rg.LineCurve]

    @classmethod
    def get_all(cls):
        # Class method to access all instances
        return cls.instances
    
    @classmethod
    def get_one(cls, name):
        # Find an instance by name
        for instance in cls.instances:
            if instance.name == name:
                return instance
        return None
    
    @property
    def hanging_points(self):
        # Calculate midpoints of connection lines for hanging points
        hanging_points = []
        for line in self.get_connection_lines():
            hanging_points.append(line.PointAtMid)
        return hanging_points


    @property
    def baffles(self):
        # Use cache if available
        if self._baffle_cache is not None:
            return self._baffle_cache

        # Generate Baffle objects from inset lines
        baffle_listing = []

        # Filter valid baffle curves
        baffle_curves = self.get_inset_lines()  # Avoid recursion by not calling self.baffles here

        # Create Baffle objects
        for i, baffle_curve in enumerate(baffle_curves):
            print(self.centerline.Attributes.GetUserString("depth"))
            baffle = Baffle(f"{self.name} - Baffle {i}", self, baffle_curve)
            baffle_listing.append(baffle)

        # Store in cache
        self._baffle_cache = baffle_listing
        return baffle_listing


    def get_connection_lines(self):
        # Creates lines connecting adjacent baffles with wrap-around for closed centerlines
        lines = []
        num_baffles = len(self.baffles)
        is_closed = self.centerline.Geometry.IsClosed

        for i, baffle in enumerate(self.baffles):
            if i == num_baffles - 1 and not is_closed:
                break  # Skip last connection for open centerlines

            ptA = baffle.baffle_curve.ToNurbsCurve().PointAtEnd

            # Modulo handles wrap-around for closed centerlines
            next_index = (i + 1) % num_baffles
            ptB = self.baffles[next_index].baffle_curve.ToNurbsCurve().PointAtStart

            lines.append(rg.Line(ptA, ptB).ToNurbsCurve())
        return lines

    def get_inset_lines(self):
        # Creates inset lines along the centerline with appropriate gaps and handling for different curve types
        curve_list = []
        sub_curves = self.centerline.Geometry.GetSubCurves()
        is_closed = self.centerline.Geometry.IsClosed

        for i, crv in enumerate(sub_curves):
            if isinstance(crv, rg.LineCurve):
                # Calculate start/end points with appropriate insets
                if is_closed:
                    ptA = crv.PointAtLength(self.extend + self.break_gap)
                    ptB = crv.PointAtLength(crv.GetLength() - self.extend - self.break_gap)
                else:
                    if i == 0:  # First segment
                        ptA, ptB = crv.PointAtStart, crv.PointAtLength(crv.GetLength() - self.extend - self.break_gap)
                    elif i == len(sub_curves) - 1:  # Last segment
                        ptA, ptB = crv.PointAtLength(self.extend + self.break_gap), crv.PointAtEnd
                    else:  # Middle segments
                        ptA = crv.PointAtLength(self.extend + self.break_gap)
                        ptB = crv.PointAtLength(crv.GetLength() - self.extend - self.break_gap)

                inset_line = rg.Line(ptA, ptB).ToNurbsCurve()

                # Subdivide long lines into multiple baffles
                if inset_line.GetLength() > self.max_baffle_length:
                    baffle_count = max(int(inset_line.GetLength() / self.max_baffle_length), 2)
                    a_length = round(inset_line.GetLength() / baffle_count, 0)

                    for j in range(baffle_count):
                        start = inset_line.PointAtLength(j * a_length + (self.break_gap / 2))
                        end = inset_line.PointAtEnd if j == baffle_count - 1 else inset_line.PointAtLength((j + 1) * a_length - (self.break_gap / 2))
                        curve_list.append(rg.Line(start, end).ToNurbsCurve())
                else:
                    curve_list.append(inset_line)

            elif isinstance(crv, rg.ArcCurve):
                # For arc segments, extend with lines to adjacent segments
                ptA, ptB = crv.PointAtStart, crv.PointAtEnd

                # Find extension points on adjacent curves
                if is_closed:
                    ptC = sub_curves[i - 1].PointAtLength(sub_curves[i - 1].GetLength() - self.extend) if i > 0 else sub_curves[-1].PointAtLength(sub_curves[-1].GetLength() - self.extend)
                    ptD = sub_curves[i + 1].PointAtLength(self.extend) if i < len(sub_curves) - 1 else sub_curves[0].PointAtLength(self.extend)
                else:
                    ptC = sub_curves[i - 1].PointAtLength(sub_curves[i - 1].GetLength() - self.extend) if i > 0 else None
                    ptD = sub_curves[i + 1].PointAtLength(self.extend) if i < len(sub_curves) - 1 else None

                # Create extension lines and join with arc
                crvA = rg.Line(ptA, ptC).ToNurbsCurve() if ptC else None
                crvB = rg.Line(ptB, ptD).ToNurbsCurve() if ptD else None

                curve_list.append(rg.Curve.JoinCurves([crvA, crv, crvB])[0] if crvA and crvB else rg.Curve.JoinCurves([crv, crvA or crvB])[0])

        return curve_list


""" BAFFLE CLASS """
class Baffle:
    """
    Represents a baffle element with geometry and structural properties
    for creating architectural baffle systems with supporting struts
    """
    def __init__(self, name: str, baffle_centerline, baffle_curve, strut_count=3, depth=-100):
        # Initialize baffle with name, centerline, curve, and strut count
        self.name = name
        self.baffle_centerline = baffle_centerline
        self.baffle_curve = baffle_curve
        self.strut_count = strut_count
        self.depth = depth

    def surface(self, depth=-100):
        # Create extruded surface from baffle curve with specified depth
        vec = rg.Vector3d(0,0,depth)
        extrusion = rg.Extrusion.CreateExtrusion(self.baffle_curve.ToNurbsCurve(), vec)
        return extrusion

    # def solid(self, thickness=12):
    #     # Generate solid geometry with specified thickness and depth
    #     offset = rg.Brep.CreateOffsetBrep(self.surface(depth=self.depth).ToBrep(), -thickness/2, False, True, 0.01)[0][0]
    #     solid = rg.Brep.CreateOffsetBrep(offset, thickness, True, True, 0.01)[0][0]
    #     return solid

    def strut_frames(self, offset=30):
        # Handle different curve types
        is_poly = isinstance(self.baffle_curve, rg.PolyCurve)
        offset = 0 if is_poly else offset
        baf_crv = self.baffle_curve.SegmentCurve(1) if is_poly else self.baffle_curve

        # Calculate spacing between frames
        length = baf_crv.GetLength() if is_poly else baf_crv.GetLength() - (2*offset)
        distance = length/self.strut_count

        # Generate perpendicular planes along curve
        planes = [baf_crv.ToNurbsCurve().PerpendicularFrameAt(
            offset if i == 0 else ((distance*i) + offset)
        ) for i in range(self.strut_count+1)]

        return planes
