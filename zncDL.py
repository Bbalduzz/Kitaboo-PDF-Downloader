import requests, os, shutil, json
from bs4 import BeautifulSoup
from natsort import natsorted
import cairosvg
import fitz

'''
HOW TO USE:
    - open the book in zanichelli reader
    - inspect the page
    - find toc.xml and get the cookie ('copy value' is fine)
    - save what u just copied into "cookies.txt"
    - search content.opf and copy the url from the inspect element console
    - run the script
    - paste the url
    - wait ;)
'''

try:
    os.mkdir('pages')
    os.mkdir('pdfs')
except:
    pass

with open('cookies.txt', 'r') as f: cookie = f.readline()
COOKIE = {'Cookie': cookie}
BASE_URL = input('[+] Enter book URL (search toc.xml): \n').removesuffix('/toc.xml')

def get_library():
    lib_req = requests.get('https://api-catalogo.zanichelli.it/v3/dashboard/licenses/real', headers=COOKIE).json()
    for book in lib_req['realLicenses']:
        meta = book['volume']
        isbn = meta['isbn']
        title = meta['opera']['title']+meta['title']
        webreader_url = meta['ereader_url']


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

data = requests.get(f'{BASE_URL}/toc.xhtml', headers=COOKIE).content
soup = BeautifulSoup(data, 'html.parser')
ol  = soup.find('ol')
def dictify(ol):
    result = {}
    for li in ol.find_all("li", recursive=False):
        page = int(li.a['href'][5:-6])
        key = next(li.stripped_strings)
        result[key] = [page, dictify(li.find("ol")) if li.find("ol") else None]
    return result

def tocify(toc_dict):
    toc = []
    for key, value in toc_dict.items():
        toc.append([1, key, value[0]])
        if value[1]:
            toc.extend([2, sub_key, sub_value[0]] for sub_key, sub_value in value[1].items())
    return toc

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
    pdf = fitz.Document(f'{book_title}.pdf')
    pdf.set_toc(tocify(dictify(ol)))
    pdf.save(f'{book_title}_.pdf')

def help():
    print(__name__.__doc__)

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
