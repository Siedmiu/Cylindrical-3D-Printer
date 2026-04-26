import re
import sys
import math
from typing import Optional, Tuple

# Configuration
DRUM_DIAMETER = 56  #mm
DRUM_RADIUS = DRUM_DIAMETER * 0.5

class GCodeState:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.e = 0.0
        self.in_print_section = False
        
    def get_current_radius(self) -> float:
        return DRUM_RADIUS + self.z

def parse_gcode_line(line: str) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Parse G-code line and extract X, Y, Z, E values."""
    x = y = z = e = None

    x_match = re.search(r'X([-+]?\d*\.?\d+)', line)
    if x_match:
        x = float(x_match.group(1))

    y_match = re.search(r'Y([-+]?\d*\.?\d+)', line)
    if y_match:
        y = float(y_match.group(1))

    z_match = re.search(r'Z([-+]?\d*\.?\d+)', line)
    if z_match:
        z = float(z_match.group(1))

    e_match = re.search(r'E([-+]?\d*\.?\d+)', line)
    if e_match:
        e = float(e_match.group(1))
    
    return x, y, z, e

def calculate_cylindrical_distance(x1: float, y1: float, z1: float, 
                                   x2: float, y2: float, z2: float,
                                   drum_radius: float) -> float:
    """
    Calculate actual 3D distance in cylindrical coordinates.
    """
    dx = x2 - x1
    dz = z2 - z1
    
    dy_deg = y2 - y1
    dy_rad = math.radians(dy_deg)
    
    r1 = drum_radius + z1
    r2 = drum_radius + z2
    avg_radius = (r1 + r2) / 2

    arc_length = abs(dy_rad * avg_radius)
    
    # Total 3D path length
    distance = math.sqrt(dx**2 + arc_length**2 + dz**2)
    
    return distance

def process_gcode(input_file: str, output_file: str, drum_radius: float):
    """Process G-code file and recalculate extrusion values."""
    state = GCodeState()
    
    with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
        for line in f_in:
            stripped = line.strip()

            if ';LAYER:0' in stripped:
                state.in_print_section = True
                f_out.write(line)
                continue

            if not stripped or stripped.startswith(';'):
                f_out.write(line)
                continue

            if not state.in_print_section:
                f_out.write(line)
                continue

            if stripped.startswith('G0') or stripped.startswith('G1'):
                x, y, z, e = parse_gcode_line(stripped)

                old_x, old_y, old_z = state.x, state.y, state.z

                new_x = x if x is not None else old_x
                new_y = y if y is not None else old_y
                new_z = z if z is not None else old_z

                has_movement = (x is not None or y is not None or z is not None)

                if x is not None:
                    state.x = x
                if y is not None:
                    state.y = y
                if z is not None:
                    state.z = z
                
                # Only recalculate for print moves
                if e is not None and e > 0.00001 and has_movement:
                    dx = new_x - old_x
                    dy_linear = new_y - old_y
                    dz = new_z - old_z
                    cartesian_distance = math.sqrt(dx**2 + dy_linear**2 + dz**2)

                    if cartesian_distance > 0:
                        cylindrical_distance = calculate_cylindrical_distance(
                            old_x, old_y, old_z,
                            new_x, new_y, new_z,
                            drum_radius
                        )
                        
                        extrusion_rate = e / cartesian_distance
                        corrected_e = extrusion_rate * cylindrical_distance

                        line_without_e = re.sub(r'E[-+]?\d*\.?\d+', '', stripped)
                        new_line = f"{line_without_e.rstrip()} E{corrected_e:.5f}\n"
                        f_out.write(new_line)
                    else:
                        f_out.write(line)
                else:
                    f_out.write(line)
            else:
                f_out.write(line)

def main():
    if len(sys.argv) < 2:
        print("Usage: python recalculate_extrusion.py <input_gcode> [output_gcode] [drum_radius]")
        sys.exit(1)
    
    input_file = sys.argv[1]

    if not input_file.lower().endswith('.gcode') and not input_file.lower().endswith('.gco') and not input_file.lower().endswith('.g'):
        print("ERROR: Input file must be a G-code file (.gcode, .gco, or .g extension)")
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        # Remove any existing _corrected suffixes before adding a new one
        base_name = re.sub(r'(_corrected)+', '', input_file)
        if base_name.endswith('.gcode'):
            output_file = base_name.replace('.gcode', '_corrected.gcode')
        elif base_name.endswith('.gco'):
            output_file = base_name.replace('.gco', '_corrected.gco')
        elif base_name.endswith('.g'):
            output_file = base_name.replace('.g', '_corrected.g')
        else:
            output_file = base_name + '_corrected'

    if not output_file.lower().endswith('.gcode') and not output_file.lower().endswith('.gco') and not output_file.lower().endswith('.g'):
        print("ERROR: Output file must be a G-code file (.gcode, .gco, or .g extension)")
        print(f"Provided output: {output_file}")
        sys.exit(1)

    drum_radius = DRUM_RADIUS
    if len(sys.argv) >= 4:
        drum_radius = float(sys.argv[3])
    
    print(f"Processing {input_file}...")
    print(f"Output file: {output_file}")
    
    process_gcode(input_file, output_file, drum_radius)
    

if __name__ == "__main__":
    main()
