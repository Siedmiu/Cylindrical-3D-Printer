import sys
import math
import re
import struct
from typing import List, Tuple, Optional

# Configuration
DRUM_DIAMETER = 57
DRUM_RADIUS = DRUM_DIAMETER * 0.5

# Subdivision parameters
MAX_SEGMENT_LENGTH = 2.0  # maximum segment length before subdivision
MAX_ANGULAR_SEGMENT = 5.0  # maximum angular change before subdivision

CUT_ANGLE_DEGREES = 180.0  #Cut/seam location, degrees - 0° is at +Z axis, 180° is at -Z axis

def parse_stl_vertex(line: str) -> Optional[Tuple[float, float, float]]:
    """Parse a vertex line from STL file."""
    line_stripped = line.strip()
    
    patterns = [
        # Standard format: vertex 1.234 5.678 9.012
        r'vertex\s+([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s+([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s+([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)',
        # Relaxed format: vertex followed by any 3 numbers
        r'vertex\s+([-+]?\d+\.?\d*(?:[eE][-+]?\d+)?)\s+([-+]?\d+\.?\d*(?:[eE][-+]?\d+)?)\s+([-+]?\d+\.?\d*(?:[eE][-+]?\d+)?)',
        # Very relaxed: split by whitespace
        None
    ]
    
    for pattern in patterns:
        if pattern is None:
            parts = line_stripped.lower().replace('vertex', '').strip().split()
            if len(parts) >= 3:
                try:
                    return (float(parts[0]), float(parts[1]), float(parts[2]))
                except ValueError:
                    continue
        else:
            match = re.search(pattern, line_stripped, re.IGNORECASE)
            if match:
                try:
                    return (float(match.group(1)), float(match.group(2)), float(match.group(3)))
                except ValueError:
                    continue
    
    return None

def cylindrical_to_cartesian_transform(x: float, y: float, z: float, drum_radius: float, cut_angle: float = CUT_ANGLE_DEGREES) -> Tuple[float, float, float]:
    radius_from_center = math.sqrt(y**2 + z**2)
    angle_radians = math.atan2(y, z)

    # Convert to degrees and adjust for cut position
    angle_degrees = math.degrees(angle_radians)
    angle_degrees -= cut_angle

    while angle_degrees < 0:
        angle_degrees += 360
    while angle_degrees >= 360:
        angle_degrees -= 360

    height_above_drum = radius_from_center - drum_radius

    x_cart = x
    y_cart = angle_degrees  # Angle in degrees
    z_cart = height_above_drum  # Radius becomes height

    return (x_cart, y_cart, z_cart)

def subdivide_triangle(v1: Tuple[float, float, float], 
                       v2: Tuple[float, float, float], 
                       v3: Tuple[float, float, float],
                       drum_radius: float,
                       max_segment_length: float,
                       max_angular_segment: float,
                       depth: int = 0,
                       max_depth: int = 10) -> List[Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]]:

    if depth >= max_depth:
        return [(v1, v2, v3)]
    
    def edge_needs_subdivision(va: Tuple[float, float, float], vb: Tuple[float, float, float]) -> bool:
        dx = vb[0] - va[0]

        if abs(dx) > max_segment_length:
            return True

        angle_a = math.atan2(va[1], va[2])
        angle_b = math.atan2(vb[1], vb[2])
        angle_diff = abs(angle_b - angle_a)

        if angle_diff > math.pi:
            angle_diff = 2 * math.pi - angle_diff

        angle_diff_degrees = math.degrees(angle_diff)
        if angle_diff_degrees > max_angular_segment:
            return True

        radius_a = math.sqrt(va[1]**2 + va[2]**2)
        radius_b = math.sqrt(vb[1]**2 + vb[2]**2)
        radial_dist = abs(radius_b - radius_a)

        if radial_dist > max_segment_length:
            return True

        return False

    edge1_len = math.sqrt((v2[0]-v1[0])**2 + (v2[1]-v1[1])**2 + (v2[2]-v1[2])**2)
    edge2_len = math.sqrt((v3[0]-v2[0])**2 + (v3[1]-v2[1])**2 + (v3[2]-v2[2])**2)
    edge3_len = math.sqrt((v1[0]-v3[0])**2 + (v1[1]-v3[1])**2 + (v1[2]-v3[2])**2)

    if max(edge1_len, edge2_len, edge3_len) < 0.001:  # Less than 0.001mm
        return [(v1, v2, v3)]
    
    needs_subdiv = (edge_needs_subdivision(v1, v2) or 
                   edge_needs_subdivision(v2, v3) or 
                   edge_needs_subdivision(v3, v1))
    
    if not needs_subdiv:
        return [(v1, v2, v3)]

    m1 = ((v1[0] + v2[0]) / 2, (v1[1] + v2[1]) / 2, (v1[2] + v2[2]) / 2)
    m2 = ((v2[0] + v3[0]) / 2, (v2[1] + v3[1]) / 2, (v2[2] + v3[2]) / 2)
    m3 = ((v3[0] + v1[0]) / 2, (v3[1] + v1[1]) / 2, (v3[2] + v1[2]) / 2)
    
    # Create 4 smaller triangles and recursively subdivide with depth tracking
    triangles = []
    for tri in [(v1, m1, m3), (m1, v2, m2), (m3, m2, v3), (m1, m2, m3)]:
        triangles.extend(subdivide_triangle(tri[0], tri[1], tri[2], drum_radius, max_segment_length, max_angular_segment, depth + 1, max_depth))
    
    return triangles

def parse_binary_stl(file_path: str) -> List[Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]]:
    triangles = []
    
    with open(file_path, 'rb') as f:
        header = f.read(80)
        num_triangles = struct.unpack('<I', f.read(4))[0]
        
        for i in range(num_triangles):
            normal = struct.unpack('<fff', f.read(12))
            v1 = struct.unpack('<fff', f.read(12))
            v2 = struct.unpack('<fff', f.read(12))
            v3 = struct.unpack('<fff', f.read(12))
            attr = struct.unpack('<H', f.read(2))[0] 

            triangles.append((v1, v2, v3))
    
    return triangles

def parse_ascii_stl(file_path: str) -> List[Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()

    lines = content.splitlines()
    first_line = lines[0].strip() if lines else ""
    
    if not first_line.lower().startswith('solid'):
        raise ValueError("File does not appear to be a valid ASCII STL")
    
    triangles = []
    current_triangle = []
    in_facet = False
    facet_count = 0
    vertex_count = 0
    
    for line_no, line in enumerate(lines):
        line_stripped = line.strip()
        line_lower = line_stripped.lower()
        
        if line_lower.startswith('facet'):
            in_facet = True
            facet_count += 1
            current_triangle = []
            
        elif line_lower.startswith('vertex') and in_facet:
            vertex = parse_stl_vertex(line_stripped)
            if vertex:
                current_triangle.append(vertex)
                vertex_count += 1
            else:
                #Debug
                if facet_count <= 3:
                    print(f"Warning: Could not parse vertex at line {line_no + 1}: '{line_stripped}'")
                    
        elif line_lower.startswith('endfacet'):
            if len(current_triangle) == 3:
                triangles.append(tuple(current_triangle))
            elif len(current_triangle) > 0:
                if len(triangles) == 0:
                    print(f"Warning: Incomplete facet {facet_count} with {len(current_triangle)} vertices (expected 3)")
                    print(f"  Vertices found: {current_triangle}")
            in_facet = False
    
    print(f"Facets encountered: {facet_count}")
    print(f"Vertices parsed: {vertex_count}")
    print(f"Complete triangles: {len(triangles)}")
    
    return triangles

def is_binary_stl(file_path: str) -> bool:
    with open(file_path, 'rb') as f:
        header_data = f.read(84)
        
        if len(header_data) < 84:
            return False
        
        triangle_count = struct.unpack('<I', header_data[80:84])[0]
        expected_size = 84 + (triangle_count * 50)
        f.seek(0, 2)
        actual_size = f.tell()
        
        if actual_size == expected_size:
            return True
        
        f.seek(0)
        first_line = f.readline(100).decode('utf-8', errors='ignore').strip().lower()
        
        if first_line.startswith('solid'):
            return False
        
        return True

def process_stl(input_file: str, output_file: str, drum_radius: float, cut_angle: float = CUT_ANGLE_DEGREES):
    print(f"Reading {input_file}...")

    is_binary = is_binary_stl(input_file)

    if is_binary:
        print("Detected binary STL format")
        triangles = parse_binary_stl(input_file)
    else:
        print("Detected ASCII STL format")
        triangles = parse_ascii_stl(input_file)

    print(f"Parsed {len(triangles)} triangles")

    if len(triangles) == 0:
        print("\nERROR: No triangles were parsed from the STL file!")
        raise ValueError("No triangles found in STL file")
    
    print("Subdividing triangles...")
    subdivided_triangles = []
    skipped_count = 0
    
    for i, tri in enumerate(triangles):
        if i % 1000 == 0 and i > 0:
            progress = (i / len(triangles)) * 100
            print(f"  Progress: {i}/{len(triangles)} ({progress:.1f}%) - {len(subdivided_triangles)} output triangles so far")
        
        try:
            sub_tris = subdivide_triangle(tri[0], tri[1], tri[2], drum_radius, MAX_SEGMENT_LENGTH, MAX_ANGULAR_SEGMENT)
            subdivided_triangles.extend(sub_tris)
        except RecursionError:
            # Skip triangles that cause infinite recursion
            skipped_count += 1
            if skipped_count <= 5:
                print(f"  Warning: Skipped degenerate triangle at index {i}")
            continue

    print(f"After subdivision: {len(subdivided_triangles)} triangles")

    print("Transforming coordinates...")

    transformed_triangles = []
    for tri in subdivided_triangles:
        transformed_tri = tuple(cylindrical_to_cartesian_transform(v[0], v[1], v[2], drum_radius, cut_angle) for v in tri)
        transformed_triangles.append(transformed_tri)

    print(f"Writing {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("solid transformed_model\n")
        
        for tri in transformed_triangles:
            # Calculate normal (simple approach - not recalculated, just use 0,0,1)
            f.write("  facet normal 0 0 1\n")
            f.write("    outer loop\n")
            for v in tri:
                f.write(f"      vertex {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        
        f.write("endsolid transformed_model\n")
    
    print(f"\nTransformation summary:")
    print(f"  Input triangles: {len(triangles)}")
    print(f"  Output triangles: {len(transformed_triangles)}")
    if len(triangles) > 0:
        print(f"  Subdivision factor: {len(transformed_triangles) / len(triangles):.2f}x")

def main():
    if len(sys.argv) < 2:
        print("Usage: python cylindrical_to_cartesian.py <input_stl> [output_stl] [drum_radius] [cut_angle]")
        print("\nParameters:")
        print(f"  drum_radius: Radius of the drum (default: {DRUM_RADIUS} mm)")
        print(f"  cut_angle: Where to 'cut' the cylinder in degrees (default: {CUT_ANGLE_DEGREES}°)")
        print("             0° = cut at +Z axis, 90° = +Y axis, 180° = -Z axis, 270° = -Y axis")
        sys.exit(1)
    
    input_file = sys.argv[1]

    if not input_file.lower().endswith('.stl'):
        print("ERROR: Input file must be an STL file (.stl extension)")
        sys.exit(1)

    import os
    if not os.path.exists(input_file):
        print(f"ERROR: Input file does not exist: {input_file}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        output_file = input_file.replace('.stl', '_flattened.stl')

    if not output_file.lower().endswith('.stl'):
        print("ERROR: Output file must be an STL file (.stl extension)")
        print(f"Provided output: {output_file}")
        sys.exit(1)

    drum_radius = DRUM_RADIUS
    if len(sys.argv) >= 4:
        drum_radius = float(sys.argv[3])

    cut_angle = CUT_ANGLE_DEGREES
    if len(sys.argv) >= 5:
        cut_angle = float(sys.argv[4])
    
    print("=" * 60)
    print("Cylindrical to Cartesian STL Transformer")
    print("=" * 60)
    print(f"Drum diameter: {drum_radius * 2} mm")
    print(f"Drum radius: {drum_radius} mm")
    print(f"Cut angle: {cut_angle}°")
    print(f"Max segment length: {MAX_SEGMENT_LENGTH} mm")
    print(f"Max angular segment: {MAX_ANGULAR_SEGMENT}°")
    print()
    
    try:
        process_stl(input_file, output_file, drum_radius, cut_angle)
    
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR occurred during processing:")
        print(f"{'='*60}")
        print(f"{type(e).__name__}: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
