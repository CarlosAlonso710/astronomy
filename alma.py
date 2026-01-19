import os
import tarfile
from astroquery.alma import Alma
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.io import fits
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm

# -------------------------------
# 1) Ask user for target name and search radius
# -------------------------------
target_name = input("Enter the target name (e.g., W Hya, Betelgeuse, NGC 253): ").strip()

while True:
    radius_input = input("Enter search radius in degrees (e.g., 0.1): ").strip()
    try:
        radius = float(radius_input)
        if radius > 0:
            break
        else:
            print("Radius must be positive.")
    except ValueError:
        print("Invalid input. Enter a number.")

# -------------------------------
# 2) Initialize ALMA query
# -------------------------------
alma = Alma()
coord = SkyCoord.from_name(target_name)
print(f"Coordinates of {target_name}: RA={coord.ra.deg:.5f}, Dec={coord.dec.deg:.5f}")

# -------------------------------
# 3) Search ALMA datasets around target
# -------------------------------
results = alma.query_region(coord, radius=radius*u.deg)
print(f"Total datasets found: {len(results)}")

if len(results) == 0:
    raise RuntimeError(f"No ALMA datasets found for {target_name} within {radius} deg.")

# -------------------------------
# 4) List available datasets with summary info
# -------------------------------
print("\nAvailable datasets (latest first):")
for i, uid in enumerate(results["member_ous_uid"]):
    title = results["obs_title"][i] if "obs_title" in results.colnames else "No title"
    bands = results["band_list"][i] if "band_list" in results.colnames else "N/A"
    instr = results["instrument_name"][i] if "instrument_name" in results.colnames else "N/A"
    freq = results["frequency"][i] if "frequency" in results.colnames else "N/A"
    date = results["lastModified"][i]
    print(f"{i}: UID={uid}, Title={title}, Bands={bands}, Instrument={instr}, Frequency={freq}, Last Modified={date}")

# -------------------------------
# 5) Pick a dataset
# -------------------------------
while True:
    ds_index = input(f"\nEnter the index of the dataset to use (0-{len(results)-1}): ")
    try:
        ds_index = int(ds_index)
        if 0 <= ds_index < len(results):
            break
        else:
            print("Index out of range, try again.")
    except ValueError:
        print("Invalid input, enter a number.")

selected_uid = results["member_ous_uid"][ds_index]

# -------------------------------
# 6) List available FITS/tarball files with summary info
# -------------------------------
info_table = alma.get_data_info(selected_uid, expand_tarfiles=True)

fits_urls = [url for url in info_table["access_url"] if url.lower().endswith(".fits")]
if len(fits_urls) == 0:
    fits_urls = [url for url in info_table["access_url"] if url.lower().endswith(".tar.gz")]

if len(fits_urls) == 0:
    raise RuntimeError("No FITS or tarball files found in this dataset.")

print("\nAvailable files in dataset:")
for i, url in enumerate(fits_urls):
    # get the filename and format
    fname = os.path.basename(url)
    fmt = info_table["access_format"][i] if "access_format" in info_table.colnames else "N/A"
    size = info_table["access_estsize"][i] if "access_estsize" in info_table.colnames else "N/A"
    print(f"{i}: File={fname}, Format={fmt}, Size={size} bytes")

# -------------------------------
# 7) Pick a file
# -------------------------------
while True:
    file_index = input(f"\nEnter the index of the file to download (0-{len(fits_urls)-1}): ")
    try:
        file_index = int(file_index)
        if 0 <= file_index < len(fits_urls):
            break
        else:
            print("Index out of range, try again.")
    except ValueError:
        print("Invalid input, enter a number.")

first_file_url = fits_urls[file_index]

# -------------------------------
# 8) Download the selected file
# -------------------------------
download_dir = "."  # current directory
downloaded = alma.download_files([first_file_url], savedir=download_dir, cache=True)
downloaded_file = downloaded[0]

# -------------------------------
# 9) Extract if tar.gz
# -------------------------------
fits_file = None
if downloaded_file.endswith(".tar.gz") or downloaded_file.endswith(".tar"):
    with tarfile.open(downloaded_file, "r:*") as tar:
        tar.extractall(path=download_dir)
    # pick the first FITS inside
    for name in os.listdir(download_dir):
        if name.lower().endswith(".fits"):
            fits_file = os.path.join(download_dir, name)
            break
else:
    fits_file = downloaded_file

print(f"\nDownloaded FITS file: {fits_file}")

# -------------------------------
# 10) Open and plot the FITS image
# -------------------------------
hdul = fits.open(fits_file)
data = hdul[0].data

# Squeeze singleton dimensions (works for cubes)
data_2d = np.squeeze(data)

# Log normalization with contrast scaling
plt.figure(figsize=(8, 6))
vmin = np.percentile(data_2d, 1)
vmax = np.percentile(data_2d, 99)
plt.imshow(data_2d, origin='lower', cmap='inferno', norm=LogNorm(vmin=max(vmin, 1e-10), vmax=vmax))
plt.colorbar(label='Flux')
plt.title(f"{target_name} - {os.path.basename(fits_file)}")
plt.xlabel("X Pixel")
plt.ylabel("Y Pixel")
plt.show()
