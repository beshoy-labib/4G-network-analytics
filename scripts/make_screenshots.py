import math, pandas as pd, plotly.express as px, h3

RIYADH = {'lat': 24.6967, 'lon': 46.7119}
OUT = 'docs/'

rsrp = pd.read_parquet('rsrp_clean.parquet',
                       columns=['LocationLatitude','LocationLongitude','RadioOperatorName','RSRP'])

cover = (rsrp.assign(lat=rsrp['LocationLatitude'].round(3),
                     lon=rsrp['LocationLongitude'].round(3))
             .groupby(['RadioOperatorName','lat','lon'])['RSRP']
             .agg(['mean','size']).reset_index())
cover = cover[cover['size'] >= 3]

def coverage_map(op):
    d = cover[cover['RadioOperatorName']==op]
    return px.scatter_map(d, lat='lat', lon='lon', color='mean',
        color_continuous_scale='RdYlGn', range_color=[-105,-70],
        zoom=9.5, center=RIYADH, opacity=0.7, map_style='carto-positron',
        height=650, labels={'mean':'RSRP (dBm)','size':'Samples'},
        title=f'Mean RSRP by location - {op}')

for op, tag in [('Operator A','a'), ('Operator C','c')]:
    coverage_map(op).write_image(f'{OUT}chart2_coverage_{tag}.png', width=1400, height=800, scale=2)
    print('ok', op, flush=True)

traffic = pd.read_parquet('traffic_clean.parquet',
    columns=['LocationLatitude','LocationLongitude','RadioOperatorName','TrafficDirection','TrafficVolume'])
downlink = traffic[traffic['TrafficDirection']=='Downlink']

hexes = {}
for res in (7, 9):
    cell = [h3.latlng_to_cell(la, lo, res)
            for la, lo in zip(downlink['LocationLatitude'], downlink['LocationLongitude'])]
    g = (downlink.assign(Hex=cell).groupby(['RadioOperatorName','Hex'])['TrafficVolume']
                 .sum().reset_index())
    g[['lat','lon']] = pd.DataFrame([h3.cell_to_latlng(c) for c in g['Hex']], index=g.index)
    hexes[res] = g

def traffic_bubbles(res):
    g = hexes[res].copy()
    g['Downlink (GB)'] = g['TrafficVolume']/1024
    ops = sorted(g['RadioOperatorName'].unique())
    radius_km = math.sqrt(h3.average_hexagon_area(res, unit='km^2')/math.pi)
    offset = 0.35*radius_km/111.0
    angle = {o: 2*math.pi*i/len(ops) for i,o in enumerate(ops)}
    a = g['RadioOperatorName'].map(angle)
    g['plot_lat'] = g['lat'] + offset*a.map(math.sin)
    g['plot_lon'] = g['lon'] + offset*a.map(math.cos)/math.cos(math.radians(RIYADH['lat']))
    return px.scatter_map(g, lat='plot_lat', lon='plot_lon', size='Downlink (GB)',
        color='RadioOperatorName', size_max=45, zoom=9.5, center=RIYADH, opacity=0.6,
        map_style='carto-positron', height=650, hover_name='Hex',
        labels={'RadioOperatorName':'Operator'},
        title=f'Downlink traffic per operator - H3 resolution {res} '
              f'({h3.average_hexagon_area(res, unit="km^2"):.2f} km2 per hexagon)')

for res in (7, 9):
    traffic_bubbles(res).write_image(f'{OUT}chart3_traffic_res{res}.png', width=1400, height=800, scale=2)
    print('ok res', res, flush=True)

dev = pd.read_parquet('rsrp_clean.parquet', columns=['RadioOperatorName','DeviceManufacturer','RSRP'])
dev['DeviceManufacturer'] = dev['DeviceManufacturer'].str.title()
stats = (dev.groupby(['DeviceManufacturer','RadioOperatorName'])['RSRP']
            .agg(Average='mean', Minimum='min', Maximum='max',
                 **{'90th percentile': lambda s: s.quantile(0.9)}, Samples='size')
            .round(1).reset_index())

def device_bars(metric, min_samples):
    d = stats[stats['Samples']>=min_samples]
    order = d.groupby('DeviceManufacturer')[metric].mean().sort_values(ascending=False).index
    fig = px.bar(d, x='DeviceManufacturer', y=metric, color='RadioOperatorName',
        barmode='group', height=550, category_orders={'DeviceManufacturer':list(order)},
        labels={'DeviceManufacturer':'Manufacturer','RadioOperatorName':'Operator',
                metric:f'RSRP - {metric} (dBm)'},
        title=f'RSRP {metric} by manufacturer (at least {min_samples:,} samples per operator)')
    lo, hi = d[metric].min(), d[metric].max()
    pad = max(2.0, 0.05*(hi-lo))
    fig.update_yaxes(range=[lo-pad, hi+pad])
    return fig

device_bars('Average', 1000).write_image(f'{OUT}chart4_device_avg.png', width=1400, height=700, scale=2)
device_bars('90th percentile', 1000).write_image(f'{OUT}chart4_device_p90.png', width=1400, height=700, scale=2)
print('done')
