"""Render the hourly density map as a GIF for the README.

Plotly animations only live in a browser, so each hour is exported as a still
PNG and the stills are stitched together.
"""

import io

import pandas as pd
import plotly.express as px
from PIL import Image

RIYADH = {"lat": 24.6967, "lon": 46.7119}

rsrp = pd.read_parquet("rsrp_clean.parquet",
                       columns=["Timestamp", "LocationLatitude", "LocationLongitude"])
rsrp["Hour"] = rsrp["Timestamp"].dt.hour

grid = (rsrp
        .assign(lat=rsrp["LocationLatitude"].round(3),
                lon=rsrp["LocationLongitude"].round(3))
        .groupby(["Hour", "lat", "lon"])
        .size()
        .reset_index(name="Samples"))

# one shared colour range, otherwise each frame rescales and the animation flickers
cmax = grid["Samples"].quantile(0.99)

frames = []
for hour, g in grid.groupby("Hour"):
    fig = px.density_map(g, lat="lat", lon="lon", z="Samples",
                         radius=6, zoom=9.5, center=RIYADH,
                         range_color=[0, cmax],
                         map_style="carto-positron", width=900, height=600,
                         title=f"User density in Riyadh - {hour:02d}:00 local")
    frames.append(Image.open(io.BytesIO(fig.to_image(format="png"))).convert("P",
                                                                             palette=Image.ADAPTIVE))
    print(hour, end=" ", flush=True)

frames[0].save("timelapse.gif", save_all=True, append_images=frames[1:],
               duration=500, loop=0, optimize=True)
print("\ntimelapse.gif")
