# Manga Colorization
### comics_splitter.py
1. Syntax: `python3 comics_splitter.py -i <input_dir> -o <output_dir>`.
2. Can try adding `-d` for diagonal split, `-v` for vertical split and `--draw` to draw cut area. 

### TODO List
- [ ] Use an even more robust algorithm for vertical splitting
- [-] See what happens when we combine vertical, horizontal and diagonal splitting
- [-] Fix red boxes to include all pixels (no clipping - easier for reconstruction) 
- [-] Add code to check for aspect ratios and drop badly-sized panels
