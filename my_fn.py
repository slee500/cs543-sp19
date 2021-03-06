import pdb
import numpy as np

def filter_panels(panels, threshold=0.4):
    '''
    iterate through our panels and remove all of our panels that do not fall
    within our threshold of a 1:1 aspect ratio.
    '''
    # in the case that there were no splits, don't change anything
    if len(panels) == 1:
        return panels

    filtered_panels = []
    for panel in panels:
        x_min, y_min, x_max, y_max = convert_from_square(panel)

        w = x_max - x_min
        h = y_max - y_min

        # this gives us the ratio as a fraction <= 1
        ratio = float(min(w, h)) / max(w, h)
        # TODO: Drop panels that are too big to be resized

        if ratio >= threshold:
            filtered_panels.append(panel)
    return filtered_panels

def keep_white_space(horiSplit):
    '''
    The splitting algorithm tends to cut out the white space between panels horizontally.
    We want to retain this white space so that stitching the final comic together would be easier
    '''
    new_horiSplit = []
    y_mid = []
    for p1 in range(len(horiSplit)-1):
        p2 = p1 + 1
        x_min1, y_min1, x_max1, y_max1 = convert_from_square(horiSplit[p1])
        x_min2, y_min2, x_max2, y_max2 = convert_from_square(horiSplit[p2])
        y_mid.append(int((y_max1 + y_min2) / 2))

    for i,sq in enumerate(horiSplit):
        x_min, y_min, x_max, y_max = convert_from_square(sq)
        if i-1 >= 0 and np.abs(y_min - y_mid[i-1]) < 20:
            y_min = y_mid[i-1]
        if i < len(y_mid) and np.abs(y_max - y_mid[i]) < 20:
            y_max = y_mid[i]

        new_horiSplit.append(convert_to_square(x_min, y_min, x_max, y_max))

    return new_horiSplit

def vertical_split(imGrey, sq, stepsize=2):
    '''
    Attempt to perform vertical splitting.
    Using similar concept found in author's `horizontal_cut` function. 
    
    The idea: 
    - Move along the x-direction (horizontally) with a given stepsize (I found 2 works well)
    - For each x, move along the y-direction (vertically) to find a line that is a possible candidate for a split
    - A vertical line is a candidates if its median value is close to 255 and has low std dev. 
    '''
    x_min, y_min, x_max, y_max = convert_from_square(sq)

    if y_max - y_min < 10:
        return []

    imGrey_np = np.asarray(imGrey, dtype=np.int)
    im_crop = imGrey_np[y_min:y_max, x_min:x_max]

    # TODO: Use a more robust vertical splitting method (black line detection + local max)

    # black_thres = 0.7 * (y_max - y_min)
    # stat_black = np.sum(im_crop < 10, axis=0)

    # Sliding window to find local max
    # for i in range(1, im_crop.shape[0]-1):
    #     arr = stat_black[i-1:i+2]
    #     if arr[1] > arr[0] and arr[1] > arr[2] and np.std(arr) > 50:
    #         print("Local max at {0}: {1}, STD: {2}".format(i, arr, np.std(arr)))
    
    # print(stat_black, black_thres, np.sum(stat_black > black_thres))

    stat_median = np.median(im_crop, axis=0)
    stat_stddev = np.std(im_crop, axis=0)
    bounds = [] 

    startSquare = False
    foundColorStrip = False

    for x in range(0, im_crop.shape[1], stepsize):
        if not startSquare:
            # Finding start of panel split
            if stat_median[x] > 250 and stat_stddev[x] < 10:
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
                    if x - leftX < 50 or stat_stddev[x] > 10:
                        # Avoid small strips or false positives (ie. speech bubbles)
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
    # [(top left x,y), (top right x,y), (bottom right x,y), (bottom left x,y)]
    ret_bounds = []
    for b in bounds:
        ret_bounds.append(convert_to_square(b[0], y_min, b[1], y_max))

    # Save images (temp step -- will be removed when integrating code)
    # for idx,b in enumerate(bounds):
    #     print(b, stat_stddev[b[0]], stat_stddev[b[1]])
    #     im_to_save = im_crop[:, b[0]:b[1]]
    #     plt.imsave('test_splitter_out/{0}_row{1}_im{2}.jpg'.format(fname, n_row, idx), im_to_save, cmap='gray')
    if len(ret_bounds) == 0:
        ret_bounds = [sq]

    return ret_bounds

def convert_to_square(x_min, y_min, x_max, y_max):
    '''
    Takes in a pair of coordinates representing top-left (x_min, y_min) and 
       bottom-right (x_max, y_max) corners.
    Returns in the polygon form used by the main author's code.
    [(top left x,y), (top right x,y), (bottom right x,y), (bottom left x,y)]
    '''
    return [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]

def convert_from_square(sq):
    '''
    Opposite of convert_to_square function
    '''
    x_min = sq[0][0]
    y_min = sq[0][1]
    x_max = sq[2][0]
    y_max = sq[2][1]
    return x_min, y_min, x_max, y_max

def clip_x(sq_in, x_left, x_right):
    '''
    Clip the left-right x-bounds.
    Square inputs are as follows:
    [(top left x,y), (top right x,y), (bottom right x,y), (bottom left x,y)]
    '''
    sq_out = []
    for i,coord in enumerate(sq_in):
        curr_x, curr_y = coord
        if i == 0 or i == 3:
            new_x = curr_x if curr_x > x_left else x_left
            new_x = x_left if np.abs(new_x - x_left) < 50 else new_x
        elif i == 1 or i == 2:
            new_x = curr_x if curr_x < x_right else x_right
            new_x = x_right if np.abs(new_x - x_right) < 50 else new_x

        sq_out.append((new_x, curr_y))

    return sq_out
