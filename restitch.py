import pdb
import numpy as np
import matplotlib.pyplot as plt
import cv2
import argparse
from collections import defaultdict
import os

FAKE_REG_FILTER = "fake_reg.png"
FINAL_IMG_FOLDER = 'final_imgs/'

parser = argparse.ArgumentParser(description='Restitch images from groun truth and colorized')
parser.add_argument('input_path', type=str)
parser.add_argument('output_path', type=str)
args = parser.parse_args()

input_img_paths = sorted([os.path.join(args.input_path, fp) for fp in
    os.listdir(args.input_path) if not fp.startswith(".")])
input_imgs = [cv2.cvtColor(cv2.imread(fp, cv2.IMREAD_COLOR), cv2.COLOR_RGB2Lab)
        for fp in input_img_paths]

def rec_dd(): return defaultdict(rec_dd)
output_imgs = rec_dd()
for file_name in os.listdir(args.output_path):
    file_path = os.path.join(args.output_path, file_name)
    img_id, hint_id, _ = file_name.split('_', 2)
    img = cv2.imread(file_path, cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2Lab)
    if FAKE_REG_FILTER in file_path:
        output_imgs[int(img_id)][hint_id] = img

assert(len(input_imgs) == len(output_imgs.keys()))

for i, input_img in enumerate(input_imgs):
    for hint_id, output_img in output_imgs[i].items():
        h, w, channels = input_img.shape
        output_img = cv2.resize(output_img, (w, h))
        final_img = np.zeros((h, w, channels), dtype=np.uint8)
        final_img[:,:,0] = input_img[:,:,0]
        final_img[:,:,1] = output_img[:,:,1]
        final_img[:,:,2] = output_img[:,:,2]
        final_img = cv2.cvtColor(final_img, cv2.COLOR_Lab2RGB)
        final_img_name = "{}.png".format('_'.join([str(i), hint_id]))
        final_img_path = os.path.join(FINAL_IMG_FOLDER, final_img_name)
        cv2.imwrite(final_img_path, final_img)
        print("Finished writing image {} with hint {}".format(i, hint_id))
