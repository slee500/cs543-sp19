import pdb
import numpy as np
import matplotlib.pyplot as plt
import cv2
import argparse
from collections import defaultdict
import os

'''
Usage: python3 restitch.py <ground_truth_dir> <fake_colorized_dir>
'''

FAKE_REG_FILTER = "fake_reg.png"
FINAL_IMG_FOLDER = "final_imgs"
FINAL_IMG_PARTS = os.path.join(FINAL_IMG_FOLDER, "parts") # the different panels that make up a page
FINAL_IMG_PAGE = os.path.join(FINAL_IMG_FOLDER, "whole") # to rebuild an entire page

# Create dirs if they don't yet exist
if not os.path.exists(FINAL_IMG_FOLDER):
    os.mkdir(FINAL_IMG_FOLDER)
if not os.path.exists(FINAL_IMG_PARTS):
    os.mkdir(FINAL_IMG_PARTS)
if not os.path.exists(FINAL_IMG_PAGE):
    os.mkdir(FINAL_IMG_PAGE)

parser = argparse.ArgumentParser(description='Restitch images from ground truth and colorized')
parser.add_argument('input_path', type=str)
parser.add_argument('output_path', type=str)
args = parser.parse_args()

input_img_paths = sorted([os.path.join(args.input_path, fp) for fp in
    os.listdir(args.input_path) if not fp.startswith(".")])
input_imgs_flist = [fp for fp in input_img_paths]

def read_image(file_path):
    img = cv2.imread(file_path, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2Lab)
    return img

def get_final_page_name(input_fname, hint_id):
    # Get the final page name
    final_page_name = os.path.split(input_fname)[1]
    left_part = final_page_name.split('_', 3)[:-1]
    right_part = final_page_name.split('_', 3)[-1].split('.', 1)
    file_end = str(hint_id) + '.' + right_part[-1]
    out_str = '_'.join(left_part) + '_' + file_end
    return out_str
        
page_ptr = {}

def rec_dd(): return defaultdict(rec_dd)
output_imgs = rec_dd()
for file_name in os.listdir(args.output_path):
    file_path = os.path.join(args.output_path, file_name)
    img_id, hint_id, _ = file_name.split('_', 2)
    if FAKE_REG_FILTER in file_path:
        output_imgs[int(img_id)][hint_id] = file_path

assert(len(input_imgs_flist) == len(output_imgs.keys()))

for i, input_fname in enumerate(input_imgs_flist):
    for hint_id, output_fname in output_imgs[i].items():
        final_img_name = "{}.png".format('_'.join([str(i), hint_id]))
        final_img_path = os.path.join(FINAL_IMG_PARTS, final_img_name)
        # if os.path.exists(final_img_path):
        #     continue

        input_img = read_image(input_fname)
        output_img = read_image(output_fname)

        h, w, channels = input_img.shape
        output_img = cv2.resize(output_img, (w, h))
        final_img = np.zeros((h, w, channels), dtype=np.uint8)
        final_img[:,:,0] = input_img[:,:,0]
        final_img[:,:,1] = output_img[:,:,1]
        final_img[:,:,2] = output_img[:,:,2]
        final_img = cv2.cvtColor(final_img, cv2.COLOR_Lab2RGB)
        cv2.imwrite(final_img_path, final_img)
        print("Finished writing image {} with hint {}".format(i, hint_id))

        #### Recreate the comic pages using the fake colored images ####
        final_page_name = get_final_page_name(input_fname, hint_id)
        final_page_path = os.path.join(FINAL_IMG_PAGE, final_page_name)
        if not os.path.exists(final_page_path):
            # Create page image file
            # Sizes are hardcoded here for my convenience
            final_shape = (1200,1520,3) if 'part15' in input_fname else (1200,760,3)
            final_img_page = 255*np.ones(final_shape, dtype=np.uint8)
        else:
            final_img_page = cv2.imread(final_page_path, cv2.IMREAD_COLOR)
        
        curr_x, curr_y, curr_height = page_ptr[final_page_path] if final_page_path in page_ptr else (0, 0, final_img.shape[0])
        
        if curr_height != final_img.shape[0]:
            # Go to next line
            curr_x = 0
            curr_y = curr_y + curr_height

        final_img_page[curr_y : curr_y + final_img.shape[0],\
                       curr_x : curr_x + final_img.shape[1], :] = final_img
        page_ptr[final_page_path] = (curr_x + final_img.shape[1], curr_y, final_img.shape[0])
            
        cv2.imwrite(final_page_path, final_img_page)
