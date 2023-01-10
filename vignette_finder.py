# -*- coding: utf-8 -*-
"""
Vignette coefficent finder 
input: blurred grayscale image of neutral-colored equally irradiated planar surface 
output:  xc, yc - vignette center coordinates (in pixels)
 k[1]..k[6]  - polynomial coefficients, 1 + k[1] * x + k[2] * x**2 + ... + k[6] * x**6   
@author: n.prokofiev
"""

filepath = 'D:/AFMS/tags/202111/018/img4-avg.tif'
of_name = 'D:/AFMS/tags/202111/018/img4.txt'

import numpy as np
import matplotlib.image as mpimg
import matplotlib.pyplot as plt

img_width = 1440
img_height = 1080
blacklevel = 3840.0

img = np.array(mpimg.imread(filepath))
# x - width, y - height
img = img.T
img = img - blacklevel

from scipy.optimize import curve_fit
from scipy import ndimage

# Calculating vignette center position which is supposed to be the brightest point in the image
com = ndimage.measurements.center_of_mass(img)
xc = int(com[0])
yc = int(com[1])

#def poly6(x, b, c, d, e, f, g):
#    return 1 + b * x + c * x**2 + d * x**3 + e * x**4 + f * x**5 + g * x**6    

def poly6(x, b, c, e, g):
    return 1 + b * x + c * x**2 + e * x**4 + g * x**6 

# calculate "brightest pixel" value. All image will be normalized to that value. Averaging 11x11

Vref = 0.
Vref = img[xc-5:xc+6,yc-5:yc+6].mean()    
    
# following cycle computes each pixel to brighest pixel ratio, distance to vignetting center and dumps into txt file

Vx = np.empty(img_width)
fo = open(of_name, "w")
fo.write("r V \n")
i = 0
j = 0    
while i < img_width:
    while j < img_height:
        Vx[i] = img[i, j]/Vref
        if Vx[i] < 1.2:
          r = ((i - xc)**2 + (j - yc)**2)**(1/2)
          fo.write(str(r))
          fo.write(" ")
          fo.write(str(Vx[i]))
          fo.write("\n")    
        j = j + 1       
    j = 0
    i = i + 1
fo.close()

import pandas as pd
df0 = pd.read_csv(of_name, sep=' ')
df0.plot.scatter(x='r', y='V')

popt, pcov = curve_fit(poly6, df0['r'], df0['V'])
print('xc = ', xc, ', yc = ', yc)
print(popt)

v0 = poly6(df0['r'], *popt)
plt.plot(df0['r'], v0, color='red')


