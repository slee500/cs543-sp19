# coding: utf-8
import pdb
import sys, getopt
import os, re
from math import ceil
from PIL import Image, ImageDraw
import time
import my_fn
import concurrent.futures

DEBUG = False
STEP = 5

def print_help():
    print('Usage : comics_splitter.py -i <inputDir> -o <outputDir> <Options>')
    print("""Options:
    -r, --rotate : enable rotation to always have a portrait page (very usefull on E-reader)
    -d, --diago : enable diagonal split (longer processing)
    -s, --sort : smart sort on files name (Windows sort)
    -v, --vert : vertical split
    -h, --help : print help
    --draw : only draw cut area
    """)
    exit(1)

def search_diagonale(start, end, imageGrey, tolerance):
    """Bresenham's Line Algorithm
    Produces a list of tuples from start and end
    """
    # Setup initial conditions
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1

    # Calculate error
    error = int(dx / 2.0)
    ystep = 1 if y1 < y2 else -1

    # Iterate over bounding box generating points between start and end
    stop = 0
    while x1 <= x2  and stop <= tolerance:
        coord = (x1, y1)
        if imageGrey.getpixel(coord) < 250:
            stop += 1

        error -= abs(dy)
        if error < 0:
            y1 += ystep
            error += dx
        x1 += 1

    return x1, stop

def cut_panels(imageColor, polygons, rotate=False):
    sizeX, sizeY = imageColor.size
    part = []
    imagesOut = []

    if len(polygons) == 0:
        if rotate and sizeX > sizeY:
            image = imageColor.rotate(270, expand=True)
            if DEBUG:
                print("Rotation !")
        imagesOut.append(image)
    else:
        for polygon in polygons:
            x0, y0 = polygon[0]
            x1, y1 = polygon[1]
            x2, y2 = polygon[2]
            x3, y3 = polygon[3]

            diago = False
            if y0 == y1:
                yUp = y0
            elif y0 > y1:
                yUp = y1
                diago = True
            else:
                yUp = y0
                diago = True

            if y2 == y3:
                yDown = y2
            elif y2 > y3:
                yDown = y2
                diago = True
            else:
                yDown = y3
                diago = True

            box = (x0, yUp, x1, yDown)
            # print("Polygon: {0}".format(polygon))
            # print("Box: {0}, diago: {1}".format(box, diago))

            if diago:
                copy = imageColor.copy()
                imageDraw = ImageDraw.Draw(copy)
                imageDraw.polygon([(0, 0), (sizeX, 0), (sizeX, y1 - 1), (0, y0 - 1)], outline="white", fill="white")
                imageDraw.polygon([(0, y3 + 1), (sizeX, y2 + 1), (sizeX, sizeY), (0, sizeY)], outline="white",
                                  fill="white")
                temp = copy.crop(box)
                del imageDraw
            else:
                temp = imageColor.crop(box)

            if rotate:
                if x1 - x0 > yDown - yUp:
                    temp = temp.rotate(270, expand=True)
                    if DEBUG:
                        print("Rotation !")
            imagesOut.append(temp)

    return imagesOut

def search_left_right_borders(imageGrey, tolerance):
    sizeX, sizeY = imageGrey.size
    x_left = 0
    x_right = sizeX
    stop = 0

    while x_left < (sizeX / 3) and stop <= tolerance:
        y = 0
        stop = 0
        while y < sizeY and stop <= tolerance:
            if imageGrey.getpixel((x_left, y)) < 250:
                stop += 1
            y += STEP
        if stop <= tolerance:
            x_left += 1

    stop = 0
    while x_right - 1 >= (sizeX / 3) * 2 and stop <= tolerance:
        y = 0
        stop = 0
        while y < sizeY and stop <= tolerance:
            if imageGrey.getpixel((x_right - 1, y)) < 250:
                stop += 1
            y += STEP
        if stop <= tolerance:
            x_right -= 1

    return x_left, x_right

def draw_search_horizontal(imageGrey, imageColor, name, tolerance=10, ext="png", angle=200):
    sizeX, sizeY = imageGrey.size
    cutY = []
    px = imageColor.load()
    for y in range(sizeY):
        x = 0
        stop = 0
        while x < sizeX and stop <= tolerance:
            pix = imageGrey.getpixel((x, y))
            if pix < 250:
                stop += 1

            px[x, y] = (255-(stop*stop), 0, (stop*stop))

            if stop > tolerance and x > tolerance+1:
                if y >= angle:
                    yUp = y - angle
                else:
                    yUp = y
                if y < sizeY - angle:
                    yDown = y + angle
                else:
                    yDown = y

                for yy in range(yUp, yDown):
                    get_line((0, y), (sizeX - 1, yy), imageGrey, px, tolerance)

                    """i = 0
                    stop2 = 0
                    while i < len(droite) and stop2 <= tolerance:
                        if imageGrey.getpixel(droite[i]) < 250:
                            stop2 += 1
                        px[droite[i][0], droite[i][1]] = (255-(stop2*stop2), 0, (stop2*stop2))
                        i += 1"""

            x += 1

        if stop <= tolerance:
            print("Découpage horizontal à y={}".format(y))
            cutY.append(y)

    imageColor.save("D:\out/debug_{}.{}".format(name, ext))

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

def search_multi_diago(y, yUp, yDown, imageGrey, tolerance):
    sizeX, sizeY = imageGrey.size
    while yUp < yDown:
        x1, y1 = 0, y
        x2, y2 = sizeX - 1, yUp
        dx = x2 - x1
        dy = y2 - y1

        error = int(dx / 2.0)
        ystep = 1 if y1 < y2 else -1

        stop = 0
        while x1 <= x2 and stop <= tolerance:
            coord = (x1, y1)
            if imageGrey.getpixel(coord) < 250:
                stop += 1

            if stop <= tolerance:
                error -= abs(dy)
                if error < 0:
                    y1 += ystep
                    error += dx
                x1 += 1

        if stop > tolerance: #inutile de continuer la diagonale, on calcule la prochaine hauteur max (dy)
            # dy = (y * dx + int(dx/2)) / x
            yy = y1 - y + 1
            ddy = ceil((dx * abs(yy) - int(dx/2)) / x1)
            yyUp = y - ddy if yy < 0 else y + ddy
            yUp = yyUp if yyUp > yUp else yUp + 1
        else:
            return yUp
    return False

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
                        print("Horizontal cutting begins at y={}".format(lastY))

        else: #search for end of a panel
            if y > lastY and search_horizontal(imageGrey, tolerance, y)[0] == sizeX: #find blanck line
                square.append((sizeX, y))
                square.append((0, y))
                panels.append(square)
                startSquare = False
                inclinaison = 0
                lastY = y
                if DEBUG:
                    print("Horizontal cutting finish at y={}".format(y))
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

    if startSquare: #fin de page
        if DEBUG:
            print("Horizontal cutting finish at y={}".format(sizeY))
        square.append((sizeX, sizeY))
        square.append((0, sizeY))
        panels.append(square)

    if DEBUG and len(panels) == 0:
        print("Horizontal cutting impossible!")

    return panels

def search_split(imageGrey, diago=False, verticalSplit=False, tolerance=10):
    case2split = []
    sizeX, sizeY = imageGrey.size

    # x_left, x_right = search_left_right_borders(imageGrey, tolerance)
    if DEBUG:
        print("x_left = {}, x_right = {}".format(x_left, x_right))

    # box = (x_left, 0, x_right, sizeY)
    # imageGrey = imageGrey.crop(box)
    x_left = 0
    x_right = sizeX
    horiSplit = horizontal_cut(imageGrey, tolerance, diago)

    if DEBUG:
        print(horiSplit)

    if len(horiSplit) == 0:
        case2split.append([(x_left, 0), (x_right, 0), (x_right, sizeY), (x_left, sizeY)])
    else:
        for square in my_fn.keep_white_space(horiSplit):
            x0, y0 = square[0]
            x1, y1 = square[1]
            x2, y2 = square[2]
            x3, y3 = square[3]

            if verticalSplit:
                more_panels = my_fn.vertical_split(imageGrey, square)
                if len(more_panels) > 0:
                    case2split += more_panels
            else:
                case2split.append([(x_left, y0), (x_right, y1), (x_right, y2), (x_left, y3)])

    return case2split

def draw_case(boxList, imageColor, borderWidth=3):
    imageDraw = ImageDraw.Draw(imageColor)
    for square in boxList:
        x0, y0 = square[0]
        x1, y1 = square[1]
        x2, y2 = square[2]
        x3, y3 = square[3]
        for i in range(borderWidth):
            imageDraw.polygon([(x0 - i, y0 - i), (x1 + i, y1 - i), (x2 + i, y2 + i), (x3 - i, y3 + i)], outline="red")
            #imageDraw.rectangle([(x0 - i, y0 - i), (x1 + i, y1 + i)], outline="red")
    del imageDraw
    return imageColor

def process_image(file, tuple_args):
    inputDir, outputDir, vert, diago, rotate, draw = tuple_args
    fname = os.path.splitext(file)[0].lower()
    ext = os.path.splitext(file)[1].lower()
    if ext in [".jpg", ".png", ".jpeg"]:
        im = Image.open("{}/{}".format(inputDir, file))
        imGrey = im.convert("L")

        case2split = search_split(imGrey, diago=diago, tolerance=20, verticalSplit=vert)

        # If we did not have any splits (there is only one panel), skip
        # this file.
        if len(case2split) == 1:
            print("Skipped {0} due to lack of splits".format(file))
            return
        
        print("Processed {0}".format(file))
        # Filter our panels with a threshold for aspect ratio
        case2split = my_fn.filter_panels(case2split)

        if draw:
            im2sav = [draw_case(case2split, im)]
        else:
            im2sav = cut_panels(im, case2split, rotate)

        for num, i2s in enumerate(im2sav):
            i2s.save("{}/{}_slice{:02}{}".format(outputDir, fname, num, ext))

def process_image_w_threads(fn, data_list, tuple_args):
    # Source: https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor-example
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Start the load operations and mark each future with its URL
        future_to_url = {executor.submit(fn, d, tuple_args): d for d in data_list}
        for future in concurrent.futures.as_completed(future_to_url):
            future_url = future_to_url[future]
            try:
                data = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (future_url, exc))

def main(argv):
    inputDir = ''
    outputDir = ''
    sort = False
    diago = False
    rotate = False
    draw = False
    vert = False
    try:
        opts, args = getopt.getopt(argv,"hi:o:sdrwv",["help", "idir=", "odir=", "sort", "diago", "rotate", "draw", "vert"])
        print(opts)
    except getopt.GetoptError:
        print_help()

    for opt, arg in opts:
        if opt in ("-i", "--idir"):
            inputDir = arg
        elif opt in ("-o", "--odir"):
            outputDir = arg
        elif opt in ("-s", "--sort"):
            sort = True
        elif opt in ("-d", "--diago"):
            diago = True
        elif opt in ("-r", "--rotate"):
            rotate = True
        elif opt == "--draw":
            draw = True
        elif opt in ("-v", "--vertical"):
            vert = True
        else:
            print_help()

    if len(inputDir) == 0 or len(outputDir) == 0:
        print_help()
        exit()

    if not os.path.isdir(inputDir):
        print("{} not found".format(inputDir))
        exit()
    if not os.path.isdir(outputDir):
        print("{} not found".format(outputDir))
        exit()

    files = os.listdir(inputDir)
    if sort:
        convert = lambda text: int(text) if text.isdigit() else text
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
        files = sorted(files, key=lambda x: alphanum_key(x))
 
    tuple_args = (inputDir, outputDir, vert, diago, rotate, draw)
    process_image_w_threads(process_image, files, tuple_args)

if __name__ == "__main__":
   main(sys.argv[1:])


