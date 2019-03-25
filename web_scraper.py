import requests
import shutil
import os, csv, sys
import concurrent.futures
from bs4 import BeautifulSoup

def get_img_save_dir(chap_n):
    img_save_dir = os.path.join(os.getcwd(), 'images', 'chap{0}'.format(chap_n))
    if not os.path.exists(img_save_dir):
        os.makedirs(img_save_dir)
    return img_save_dir

def read_img_list_file(img_list_file):
    img_list = []
    with open(img_list_file, 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            img_list.append(tuple(row))
    return img_list

def write_img_list_file(img_list_file, data):
    with open(img_list_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['chapter','image','mode','url'])
        writer.writerows(data)

def get_chapter(chap_n):
    img_list_file = os.path.join(get_img_save_dir(chap_n), 'chap{0}links.csv'.format(chap_n))
    if os.path.exists(img_list_file):
        return read_img_list_file(img_list_file)
    
    list_bw = get_bw_images(chap_n)
    list_color = get_color_images(chap_n)
    
    out_list = list_bw + list_color
    write_img_list_file(img_list_file, out_list)

def get_bw_images(chap_n):
    # BW URL: https://manganelo.com/chapter/read_one_piece_manga_online_free4/chapter_1
    r_bw = requests.get('https://manganelo.com/chapter/read_one_piece_manga_online_free4/chapter_{0}'.format(chap_n), timeout=60)
    if r_bw.status_code == 200:
        soup_bw = BeautifulSoup(r_bw.text, 'html.parser')
        imgs_bw = map(lambda X : X['src'], soup_bw.find('div', class_='vung-doc', id='vungdoc').find_all('img'))
        list_bw = [(chap_n,idx,'bw',url) for idx,url in enumerate(list(imgs_bw))]
        print('Chapter {0}: {1}'.format(chap_n, 'bw'))
        return list_bw
    else: return None

def get_color_images(chap_n):
    # Color URL: https://holymanga.page/one-piece-digital-colored-comics-chap-1/ 
    r_color = requests.get('https://holymanga.page/one-piece-digital-colored-comics-chap-{0}/'.format(chap_n), timeout=60)
    if r_color.status_code == 200:
        soup_color = BeautifulSoup(r_color.text, 'html.parser')
        imgs_color = map(lambda X : X['src'], soup_color.find('center').find_all('img'))
        list_color = [(chap_n,idx,'color',url) for idx,url in enumerate(list(imgs_color))]
        print('Chapter {0}: {1}'.format(chap_n, 'color'))
        return list_color
    else: return None

def save_imgs(tuple_args):
    (chap_n, image_n, mode, img_url) = tuple_args
    img_ext = 'jpeg' if mode == 'bw' else 'png'
    file_path = os.path.join(get_img_save_dir(chap_n), 'chap{0}_{1}_part{2}.{3}'.format(chap_n, mode, image_n, img_ext))
    if os.path.exists(file_path):
        # Image already exists, no need to download
        return None

    # Source: https://stackoverflow.com/questions/13137817/how-to-download-image-using-requests
    r = requests.get(img_url, stream=True)
    if r.status_code == 200:
        with open(file_path, 'wb') as out_file:
            shutil.copyfileobj(r.raw, out_file)
        del r

def run_with_threads(fn, data_list):
    # Source: https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor-example
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Start the load operations and mark each future with its URL
        future_to_url = {executor.submit(fn, n): n for n in data_list}
        for future in concurrent.futures.as_completed(future_to_url):
            future_url = future_to_url[future]
            try:
                data = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (future_url, exc))
            
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Usage: python3 {0} [starting chapter] [ending chapter]'.format(sys.argv[0]))
        sys.exit()

    chap_start = int(sys.argv[1])
    chap_end = int(sys.argv[2])
    chapter_list = [i for i in range(chap_start,chap_end+1)] # chapter range here
    run_with_threads(get_chapter, chapter_list)
    
    for c in chapter_list:
        print('Writing chapter {0} images'.format(c))
        run_with_threads(save_imgs, get_chapter(c))