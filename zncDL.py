import requests, os, shutil
from bs4 import BeautifulSoup
from natsort import natsorted
import cairosvg

try:
    os.mkdir('pages')
    os.mkdir('pdfs')
except:
    pass

with open('cookies.txt', 'r') as f: cookie = f.readline()
COOKIE = {'Cookie': cookie}
BASE_URL = input('[+] Enter book URL (search toc.xml): \n')

def progress_bar(progress, total):
    percent = 100 * (progress / float(total))
    bar = '█' * int(percent) + '-' * (100 - int(percent))
    print(f'\r[+] Downloading book... |{bar}| {percent:.2f}%', end='\r')

toc_req = requests.get(f'{BASE_URL}/content.opf', headers=COOKIE)
soup = BeautifulSoup(toc_req.content, 'xml')
npages = int(soup.select('itemref')[-1]['idref'].removeprefix('page'))
book_title = soup.find('dc:title').text
book_desc = soup.find('dc:description').text
book_author = soup.find('dc:author').text
book_isbn = soup.find('dc:identifier').text.split(':')[2]

def download_and_create():
    progress_bar(0, npages)
    for n in range(1, npages):
        page_data = requests.get(f'{BASE_URL}/images/page{n:04d}.svgz', cookies=COOKIE).content
        with open(f'pages/page{n:04d}.svg', 'wb') as f:
            f.write(page_data)
        cairosvg.svg2pdf(url=f'pages/page{n:04d}.svg', write_to=f'pdfs/page{n:04d}.pdf')
        progress_bar(n+1, npages)

def merge_pdfs():
    from PyPDF2 import PdfMerger
    merger = PdfMerger()
    pdfs = os.listdir('pdfs')
    pdfs = natsorted(pdfs)
    for pdf in pdfs:
        merger.append(open(f'pdfs/{pdf}', 'rb'))
    with open(f'{book_title}.pdf', 'wb') as book_pdf:
        merger.write(book_pdf)

print(f'''
[+] Book Found:
    - title: {book_title}
    - description: {book_desc}
    - author: {book_author}
    - isbn: {book_isbn}
    - pages: {npages}
''')

download_and_create()
merge_pdfs()
shutil.rmtree('pages')
shutil.rmtree('pdfs')
print('\nDone :)')
