import json
import plotly.graph_objects as go
import numpy as np
from pathlib import Path

def render_debug_paths_3d(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)

    speaker = data['speaker']
    mic = data['mic']
    mic_radius = data['mic_radius']
    rays = data['rays']

    fig= go.Figure()
    #Draw Ray paths
    for i, ray in enumerate(rays):
        xs, ys, zs = zip(*ray)
        # Golden Angle
        ray_colour = f'hsl({(i*137.5) % 360}, 80%, 60%)'
        fig.add_trace(go.Scatter3d(
            x=xs,
            y=ys,
            z=zs,
            mode='lines',
            line=dict(width=2, color=ray_colour),
            opacity=0.5,
            name="Ray {i}".format(i=i),
            showlegend=False
        ))

    #Draw Mic
    fig.add_trace(go.Scatter3d(
        x=[mic[0]],
        y=[mic[1]],
        z=[mic[2]],
        mode='markers',
        marker=dict(size=5, color='darkblue'),
        name='Mic Center'
    ))
    #Draw Speakers
    fig.add_trace(go.Scatter3d(
        x=[speaker[0]],
        y=[speaker[1]],
        z=[speaker[2]],
        mode='markers',
        marker=dict(size=8, color='darkblue',symbol='cross'),
        name='Speaker'
    ))
    fig.add_trace(go.Scatter3d(

    ))

    #ax.set_aspect('equal')
    #+ax.set_title(f"3d Acoustic Ray Tracing Debugger ({len(rays)}) Rays")


    #create 3D mesh
    u = np.linspace(0, 2*np.pi, 20)
    v = np.linspace(0, np.pi, 20)
    x = mic[0] + mic_radius * np.outer(np.cos(u), np.sin(v))
    y = mic[1] + mic_radius * np.outer(np.sin(u), np.sin(v))
    z = mic[2] + mic_radius * np.outer(np.ones(np.size(u)), np.cos(v))

    fig.add_trace(go.Surface(
        x=x,
        y=y,
        z=z,
        colorscale='Reds',
        showscale=False,
        name='Mic Radius'
    ))
    fig.update_layout(
        title="3D Acoustic Ray Tracing Debugger({}) Rays".format(len(rays)),
        scene=dict(
            xaxis_title="X (Meters)",
            yaxis_title="Y (Meters)",
            zaxis_title="Z (Meters)",
            aspectmode='data',
        ),
        margin=dict(t=30, b=0, l=0, r=0),
    )
    print("Launching Plotly Visualizer")
    fig.show()



if __name__ == "__main__":
    script_dir = Path(__file__).parent
    target_file = script_dir.parent / "rust_service" / "visualisation_data.json"
    render_debug_paths_3d(target_file)