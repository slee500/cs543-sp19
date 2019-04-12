from PIL import Image, ImageDraw
import numpy as np
import matplotlib.pyplot as plt
import os

DEBUG = False
STEP = 1

def search_horizontal(imageGrey, tolerance, y):
    sizeX = imageGrey.size[0]
    x = 0
    stop = 0
    while x < sizeX and stop <= tolerance:
        pix = imageGrey.getpixel((x, y))
        if pix < 250:
            stop += 1
        x += 1
    return (x, stop)

def horizontal_cut(imageGrey, tolerance, diago, angle=200):
    sizeX, sizeY = imageGrey.size
    panels = []
    startSquare = False
    inclinaison = 0
    lastY = 0

    for y in range(0, sizeY, STEP):
        if not startSquare: #search for begin of a panel
            if inclinaison:
                if search_diagonale((0, y), (sizeX - 1, min((y + inclinaison), sizeY - 1)), imageGrey, tolerance)[0] < sizeX: #find diagonal panel
                    lastY = y + inclinaison
                    square = [(0, y), (sizeX, lastY)]
                    startSquare = True
                    if DEBUG:
                        print("Découpage diagonal débute à y0={} et y1={}".format(y, lastY))
            else:
                if search_horizontal(imageGrey, tolerance, y)[0] < sizeX: #find horizontal panel
                    lastY = y
                    square = [(0, lastY), (sizeX, lastY)]
                    startSquare = True
                    if DEBUG:
                        print("Square top corners: {0}".format(square))

        else: #search for end of a panel
            if y > lastY and search_horizontal(imageGrey, tolerance, y)[0] == sizeX: #find blanck line
                square.append((sizeX, y))
                square.append((0, y))
                panels.append(square)
                startSquare = False
                inclinaison = 0
                lastY = y
                if DEBUG:
                    print("Square bottom corners: {0}".format(square[2:]))
            elif diago:
                yUp = max(y - angle, lastY)
                yDown = min(y + angle, sizeY - 1)
                yUp = search_multi_diago(y, yUp, yDown, imageGrey, tolerance)
                if yUp:
                    startSquare = False
                    inclinaison = yUp - y
                    square.append((sizeX, yUp))
                    square.append((0, y))
                    panels.append(square)
                    lastY = yUp
                    if DEBUG:
                        print("Découpage diagonal finit à y0={} et y1={}".format(y, yUp))

    if startSquare: # end of page
        square.append((sizeX, sizeY))
        square.append((0, sizeY))
        panels.append(square)
        if DEBUG:
            print("Square bottom corners: {0}".format(square[2:]))
            print("Reached end of page at y={0}".format(sizeY))

    if DEBUG and len(panels) == 0:
        print("Horizontal cutting impossible")

    return panels

def vertical_split(imGrey, sq):
    x_min = sq[0][0]
    y_min = sq[0][1]
    x_max = sq[2][0]
    y_max = sq[2][1]

    imGrey_np = np.asarray(imGrey, dtype=np.int)
    im_crop = imGrey_np[y_min:y_max, x_min:x_max]

    stat_median = np.median(im_crop, axis=0)
    stat_stddev = np.std(im_crop, axis=0)
    bounds = []

    startSquare = False
    foundColorStrip = False
    for x in range(0, im_crop.shape[1], 2):
        if not startSquare:
            # Finding start of panel split
            if stat_median[x] > 250:
                # We have found a starting point
                leftX = x
                startSquare = True
                foundColorStrip = False
                if leftX > 50 and len(bounds) == 0:
                    # We missed a strip? 
                    bounds.append([x_min, leftX])
        else:
            if not foundColorStrip:
                if stat_median[x] < 250:
                    foundColorStrip = True
            else: # Find end of panel
                if stat_median[x] > 250:
                    startSquare = False
                    if x - leftX < 50 or stat_stddev[x] > 25:
                        startSquare = True
                        foundColorStrip = False
                    else:
                        bounds.append([leftX, x])

    if startSquare: # End of page
        if x - leftX < 50:
            lastBound = bounds[-1]
            leftX = lastBound[0]
            bounds[-1] = [leftX, x]
        else:
            bounds.append([leftX, x])

    # Return list of coordinates in the format that the main code uses
    # [(top left x,y), (bottom left x,y), (bottom right x,y), (top right x,y)]
    ret_bounds = []
    for b in bounds:
        ret_bounds.append([(b[0], y_min), (b[0], y_max), (b[1], y_max), (b[1], y_min)])

    # Save images (temp step -- will be removed when integrating code)
    # for idx,b in enumerate(bounds):
    #     print(b, stat_stddev[b[0]], stat_stddev[b[1]])
    #     im_to_save = im_crop[:, b[0]:b[1]]
    #     plt.imsave('test_splitter_out/{0}_row{1}_im{2}.jpg'.format(fname, n_row, idx), im_to_save, cmap='gray')
    if len(ret_bounds) == 0:
        ret_bounds = [sq]

    return ret_bounds


files = os.listdir('samples')
for file in files:
    print(os.path.splitext(file))
    fname = os.path.splitext(file)[0].lower()
    ext = os.path.splitext(file)[1].lower()

    fname = 'chap100_color_part10' # TODO: Remove this

    input_file = 'samples/{0}{1}'.format(fname, ext)
    imGrey = Image.open(input_file).convert("L")
    sq_list = horizontal_cut(imGrey, tolerance=20, diago=False)
    print(sq_list)
    print('------')
    for idx, sq in enumerate(sq_list):
        print(vertical_split(imGrey, sq))
    break # TODO: remove this