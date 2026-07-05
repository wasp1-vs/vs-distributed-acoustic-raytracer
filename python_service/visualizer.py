import json
import plotly.graph_objects as go
import numpy as np
from pathlib import Path


def _draw_room_walls(fig: go.Figure, geometry_path: Path) -> None:
    """Zeichnet die Raumwände aus room_geometry.json als Drahtgitter."""
    if not geometry_path.exists():
        return
    data = json.loads(geometry_path.read_text())
    for tri in data["triangles"]:
        v0, v1, v2 = tri["v0"], tri["v1"], tri["v2"]
        xs = [v0[0], v1[0], v2[0], v0[0]]
        ys = [v0[1], v1[1], v2[1], v0[1]]
        zs = [v0[2], v1[2], v2[2], v0[2]]
        fig.add_trace(go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode='lines',
            line=dict(width=1, color='rgba(100,130,200,0.35)'),
            showlegend=False,
            hoverinfo='skip',
        ))


def render_debug_paths_3d(file_path):
    script_dir = Path(file_path).resolve().parent
    geometry_path = script_dir / "room_geometry.json"

    with open(file_path, 'r') as file:
        data = json.load(file)

    speaker = data['speaker']
    mic = data['mic']
    mic_radius = data['mic_radius']
    rays = data['rays']

    fig = go.Figure()

    # Raumwände (aus room_geometry.json, falls vorhanden)
    _draw_room_walls(fig, geometry_path)

    # Ray-Pfade
    for i, ray in enumerate(rays):
        xs, ys, zs = zip(*ray)
        ray_colour = f'hsl({(i * 137.5) % 360}, 80%, 60%)'
        fig.add_trace(go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode='lines',
            line=dict(width=2, color=ray_colour),
            opacity=0.5,
            name=f"Ray {i}",
            showlegend=False,
        ))

    # Mikrofon-Mittelpunkt
    fig.add_trace(go.Scatter3d(
        x=[mic[0]], y=[mic[1]], z=[mic[2]],
        mode='markers',
        marker=dict(size=5, color='darkblue'),
        name='Mic Center',
    ))

    # Lautsprecher
    fig.add_trace(go.Scatter3d(
        x=[speaker[0]], y=[speaker[1]], z=[speaker[2]],
        mode='markers',
        marker=dict(size=8, color='darkblue', symbol='cross'),
        name='Speaker',
    ))

    # Mikrofon-Radius als Kugeloberfläche
    u = np.linspace(0, 2 * np.pi, 20)
    v = np.linspace(0, np.pi, 20)
    x = mic[0] + mic_radius * np.outer(np.cos(u), np.sin(v))
    y = mic[1] + mic_radius * np.outer(np.sin(u), np.sin(v))
    z = mic[2] + mic_radius * np.outer(np.ones(np.size(u)), np.cos(v))
    fig.add_trace(go.Surface(
        x=x, y=y, z=z,
        colorscale='Reds',
        showscale=False,
        name='Mic Radius',
        opacity=0.4,
    ))

    fig.update_layout(
        title=f"3D Acoustic Ray Tracing Debugger — {len(rays)} Ray(s)",
        scene=dict(
            xaxis_title="X (Meters)",
            yaxis_title="Y (Meters)",
            zaxis_title="Z (Meters)",
            aspectmode='data',
        ),
        margin=dict(t=40, b=0, l=0, r=0),
    )
    print("Launching Plotly Visualizer")
    fig.show()


if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    target_file = script_dir.parent / "rust_service" / "visualisation_data.json"
    render_debug_paths_3d(target_file)