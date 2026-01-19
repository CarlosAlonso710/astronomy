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
# 1) Initialize ALMA query
# -------------------------------
alma = Alma()

# -------------------------------
# 2) Search for W Hydrae
# -------------------------------
coord = SkyCoord.from_name("W Hya")
results = alma.query_region(coord, radius=0.1*u.deg)
print(f"Total datasets found: {len(results)}")

if len(results) == 0:
    raise RuntimeError("No ALMA datasets found for W Hya.")

# -------------------------------
# 3) List available datasets
# -------------------------------
print("\nAvailable datasets (latest first):")
for i, uid in enumerate(results["member_ous_uid"]):
    title = results["obs_title"][i] if "obs_title" in results.colnames else "No title"
    date = results["lastModified"][i]
    print(f"{i}: UID={uid}, Title={title}, Last Modified={date}")

# -------------------------------
# 4) Pick a dataset
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
# 5) List available FITS/tarball files in the dataset
# -------------------------------
info_table = alma.get_data_info(selected_uid, expand_tarfiles=True)

fits_urls = [url for url in info_table["access_url"] if url.lower().endswith(".fits")]
if len(fits_urls) == 0:
    fits_urls = [url for url in info_table["access_url"] if url.lower().endswith(".tar.gz")]

if len(fits_urls) == 0:
    raise RuntimeError("No FITS or tarball files found in this dataset.")

print("\nAvailable FITS/tarball files:")
for i, url in enumerate(fits_urls):
    print(f"{i}: {url}")

# -------------------------------
# 6) Pick a file
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
# 7) Download selected file
# -------------------------------
download_dir = "."  # current directory
downloaded = alma.download_files([first_file_url], savedir=download_dir, cache=True)
downloaded_file = downloaded[0]

# -------------------------------
# 8) Extract if tar.gz
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
# 9) Open and plot the FITS image
# -------------------------------
hdul = fits.open(fits_file)
data = hdul[0].data

# Squeeze singleton dimensions
data_2d = np.squeeze(data)

# -------------------------------
# 10) Plot with log normalization and contrast scaling
# -------------------------------
plt.figure(figsize=(8, 6))
# Clip extreme values for better contrast
vmin = np.percentile(data_2d, 1)
vmax = np.percentile(data_2d, 99)
plt.imshow(data_2d, origin='lower', cmap='inferno', norm=LogNorm(vmin=max(vmin, 1e-10), vmax=vmax))
plt.colorbar(label='Flux')
plt.title(f"W Hya - {os.path.basename(fits_file)}")
plt.xlabel("X Pixel")
plt.ylabel("Y Pixel")
plt.show()
