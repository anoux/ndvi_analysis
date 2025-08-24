from datetime import datetime
import rasterio
from rasterio.mask import mask
from pyproj import Transformer
from shapely.geometry import Polygon, mapping, box
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec


# ----------------------------
# File paths
# ----------------------------
red_paths = [
    "./S2A_MSIL2A_20241019T110051_N0511_R094_T30TXM_20241019T152252.SAFE/GRANULE/L2A_T30TXM_A048711_20241019T110445/IMG_DATA/R10m/T30TXM_20241019T110051_B04_10m.jp2",
    "./S2A_MSIL2A_20250117T110401_N0511_R094_T30TXM_20250117T164152.SAFE/GRANULE/L2A_T30TXM_A049998_20250117T110552/IMG_DATA/R10m/T30TXM_20250117T110401_B04_10m.jp2",
    "./S2A_MSIL2A_20250416T105041_N0511_R051_T30TXM_20250416T184711.SAFE/GRANULE/L2A_T30TXM_A051271_20250416T105932/IMG_DATA/R10m/T30TXM_20250416T105041_B04_10m.jp2",
    "./S2A_MSIL2A_20250725T105051_N0511_R051_T30TXM_20250725T143858.SAFE/GRANULE/L2A_T30TXM_A052701_20250725T105728/IMG_DATA/R10m/T30TXM_20250725T105051_B04_10m.jp2"
]

nir_paths = [
    "./S2A_MSIL2A_20241019T110051_N0511_R094_T30TXM_20241019T152252.SAFE/GRANULE/L2A_T30TXM_A048711_20241019T110445/IMG_DATA/R10m/T30TXM_20241019T110051_B08_10m.jp2",
    "./S2A_MSIL2A_20250117T110401_N0511_R094_T30TXM_20250117T164152.SAFE/GRANULE/L2A_T30TXM_A049998_20250117T110552/IMG_DATA/R10m/T30TXM_20250117T110401_B08_10m.jp2",
    "./S2A_MSIL2A_20250416T105041_N0511_R051_T30TXM_20250416T184711.SAFE/GRANULE/L2A_T30TXM_A051271_20250416T105932/IMG_DATA/R10m/T30TXM_20250416T105041_B08_10m.jp2",
    "./S2A_MSIL2A_20250725T105051_N0511_R051_T30TXM_20250725T143858.SAFE/GRANULE/L2A_T30TXM_A052701_20250725T105728/IMG_DATA/R10m/T30TXM_20250725T105051_B08_10m.jp2"
]

dates = [
    "2024-10-19",
    "2025-01-17",
    "2025-04-16",
    "2025-07-25"
]
date_objs = [datetime.strptime(d, "%Y-%m-%d") for d in dates]

# ----------------------------
# AOI polygon selection (lon, lat WGS84)
# ----------------------------

# AOI circa 300,000.00 m²)
coords = [[
    [-0.604012, 41.542947],
    [-0.599549, 41.540803],
    [-0.600879, 41.537904],
    [-0.608486, 41.537703],
    [-0.610213, 41.540819],
    [-0.604012, 41.542947]
]]

# ----------------------------
# Reproject AOI to raster CRS
# ----------------------------
with rasterio.open(red_paths[0]) as src:
    raster_bounds = src.bounds
    raster_crs = src.crs

transformer = Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True)
projected_coords = [[transformer.transform(x, y) for x, y in coords[0]]]
reprojected_aoi = Polygon(projected_coords[0])
geojson_geom = [mapping(reprojected_aoi)]

# ----------------------------
# AOI location check
# ----------------------------
raster_polygon = box(*raster_bounds)
if raster_polygon.contains(reprojected_aoi):
    print("✅ AOI is fully within the raster bounds.")
elif raster_polygon.intersects(reprojected_aoi):
    print("⚠️ AOI intersects the raster, but is not fully inside.")
else:
    print("❌ AOI is outside the raster bounds.")

# AOI size
polygon_area_m2 = reprojected_aoi.area
print(f"AOI size: {polygon_area_m2:.2f} m²")

# ----------------------------
# NDVI color ranges definition
# ----------------------------
ndvi_colors = [
    (-1.0, "tomato"),       # NDVI <= 0
    (0.0, "sandybrown"),    # 0.0–0.2
    (0.2, "greenyellow"),   # 0.2–0.4
    (0.4, "limegreen"),     # 0.4–0.6
    (0.6, "green")          # >0.6
]
bounds = [-1.0, 0.0, 0.2, 0.4, 0.6, 1.0]
colors = [c[1] for c in ndvi_colors]
cmap = mcolors.ListedColormap(colors)
norm = mcolors.BoundaryNorm(bounds, cmap.N)

# ----------------------------
# NDVI calculation & plotting
# ----------------------------
ndvi_means = []
ndvi_arrays = []

for red_path, nir_path, date in zip(red_paths, nir_paths, date_objs):
    with rasterio.open(red_path) as red_src:
        red_clip, _ = mask(red_src, geojson_geom, crop=True)
        red = red_clip[0].astype("float32")

    with rasterio.open(nir_path) as nir_src:
        nir_clip, _ = mask(nir_src, geojson_geom, crop=True)
        nir = nir_clip[0].astype("float32")

    # NDVI calculation
    ndvi_denominator = nir + red
    ndvi_denominator[ndvi_denominator == 0] = np.nan
    ndvi = (nir - red) / ndvi_denominator
    ndvi = np.clip(ndvi, -1, 1)

    # Store results
    mean_ndvi = np.nanmean(ndvi)
    ndvi_means.append(mean_ndvi)
    ndvi_arrays.append(ndvi)

# ----------------------------
# NDVI maps plotting
# ----------------------------

fig = plt.figure(figsize=(8, 8))
gs = gridspec.GridSpec(3, 2, height_ratios=[0.15, 1, 1])

# NDVI maps in rows 1 and 2
axes = [fig.add_subplot(gs[i, j]) for i in range(1, 3) for j in range(2)]

for idx, ax in enumerate(axes):
    im = ax.imshow(ndvi_arrays[idx], cmap=cmap, norm=norm)
    ax.set_title(f"NDVI on {date_objs[idx].strftime('%Y-%m-%d')}", fontsize=9)
    ax.axis("off")

# NDVI colorbar setting
cax = fig.add_subplot(gs[0, :])
cbar = fig.colorbar(im, cax=cax, orientation='horizontal')
cbar.set_ticks(bounds)
cbar.set_label("NDVI")
cbar.ax.tick_params(labelsize=8)

plt.tight_layout()
plt.show()

# ----------------------------
# Mean NDVI over time
# ----------------------------
plt.figure(figsize=(10, 6))
plt.plot(date_objs, ndvi_means, marker='o', linestyle='-', linewidth=2)
plt.title('Mean NDVI Evolution Over Time in AOI')
plt.xlabel('Date')
plt.ylabel('Mean NDVI')
plt.grid(True)
plt.ylim(-0.2, 1.0)
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()