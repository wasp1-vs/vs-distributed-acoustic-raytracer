import json
from pathlib import Path

def load_obj_to_triangles(file_path: str) -> list:
    """
    Reads an .obj file and converts it into a list of 3D triangles.
    Each triangle consists of 3 points (X, Y, Z).
    """
    vertices = []
    triangles = []
    
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"The 3D file '{file_path}' was not found.")

    with path.open('r') as f:
        for line in f:
            # Remove leading and trailing whitespace
            line = line.strip()
            
            # Read vertices: 'v 1.0 2.0 -1.5'
            if line.startswith('v '):
                parts = line.split()
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                vertices.append([x, y, z])
                
            # Read faces: 'f 1/1/1 2/2/1 3/3/1'
            elif line.startswith('f '):
                parts = line.split()
                # OBJ indices start at 1, Python lists at 0. Hence the '- 1'
                # We split by '/' in case textures/normals are included in the OBJ
                v1_idx = int(parts[1].split('/')[0]) - 1
                v2_idx = int(parts[2].split('/')[0]) - 1
                v3_idx = int(parts[3].split('/')[0]) - 1
                
                # Assemble the final triangle with actual coordinates
                triangle = [
                    vertices[v1_idx],
                    vertices[v2_idx],
                    vertices[v3_idx]
                ]
                triangles.append(triangle)
                
    return triangles

if __name__ == "__main__":
    # Quick test when running the file directly.
    # Create a simple cube/room in Blender, export it as 'room.obj' 
    # to the python_service folder and test the script!
    
    test_file = "room.obj"
    
    # Check if the file exists so the test doesn't crash if you don't have one yet
    if not Path(test_file).exists():
        print(f"Please create a '{test_file}' using Blender to run a real test.")
    else:
        triangles = load_obj_to_triangles(test_file)
        print(f"Successfully loaded! The 3D space consists of {len(triangles)} triangles.")
        
        # Show the first triangle to verify
        print("First triangle (wall segment):", triangles[0])