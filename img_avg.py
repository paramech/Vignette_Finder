import os
import numpy as np
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from PIL import Image


os.chdir('Example')
allfiles = os.listdir(os.getcwd())
img_list = [filename for filename in allfiles if filename.startswith('img0_')]

img_width = 1440
img_height = 1080

avg = np.zeros((img_height, img_width, 3), float)
print(len(img_list))
print(img_list)

for fn in img_list:
    img_arr = np.array(Image.open(fn).convert('RGB'), dtype=float)
    avg = avg + img_arr/len(img_list)

avg = np.array(np.round(avg), dtype=np.uint8)
output = Image.fromarray(avg, mode='RGB')
output.save('avg.tif')
