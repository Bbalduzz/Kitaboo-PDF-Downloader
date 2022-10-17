import requests, os
from bs4 import BeautifulSoup
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from natsort import natsorted

try:
    os.mkdir('pages')
    os.mkdir('pdfs')
except:
    pass

with open('cookies.txt', 'r') as f: cookie = f.readline()
COOKIE = {'Cookie': cookie}
BASE_URL = input('Enter book URL (search toc.xml): \n')

def progress_bar(progress, total):
    percent = 100 * (progress / float(total))
    bar = '█' * int(percent) + '-' * (100 - int(percent))
    print(f'\r Downloading book... |{bar}| {percent:.2f}%', end='\r')

toc_req = requests.get(f'{BASE_URL}/toc.xml', headers=COOKIE)
soup = BeautifulSoup(toc_req.content, 'xml')
npages = int(soup.find('toc').find_all('node')[-1]['href'].removesuffix('.xhtml').removeprefix('page'))

def download_and_create():
    progress_bar(0, npages)
    for n in range(1, npages):
        page_data = requests.get(f'{BASE_URL}/images/page{n:04d}.svgz', cookies=COOKIE).content
        with open(f'pages/page{n:04d}.svg', 'wb') as f:
            f.write(page_data)
        progress_bar(n+1, npages)
        drawing = svg2rlg(f"pages/page{n:04d}.svg")
        renderPDF.drawToFile(drawing, f"pdfs/page{n:04d}.pdf")

def merge_pdfs():
    from PyPDF2 import PdfMerger
    merger = PdfMerger()
    pdfs = os.listdir('pdfs')
    pdfs = natsorted(pdfs)
    for pdf in pdfs:
        merger.append(open(f'pdfs/{pdf}', 'rb'))
    with open('book.pdf', 'wb') as book_pdf:
        merger.write(book_pdf)
download_and_create()
merge_pdfs()
