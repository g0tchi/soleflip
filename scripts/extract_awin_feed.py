import gzip
import shutil

# Extract gzip compressed Awin feed
with gzip.open("C:/nth_dev/soleflip/context/integrations/awin_feed_sample.csv.gz", "rb") as f_in:
    with open("C:/nth_dev/soleflip/context/integrations/awin_feed_sample.csv", "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

print("Extracted successfully")
