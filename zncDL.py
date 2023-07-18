import requests, os, shutil, json
from bs4 import BeautifulSoup
import fitz

'''
HOW TO USE:
    - open the book in zanichelli reader
    - inspect the page
    - find toc.xml and get the cookie ('copy value' is fine)
    - save what u just copied into "cookies.txt"
    - copy the toc.xml url
    - run the script
    - paste the url
    - wait ;)
'''

def parse_cookies(cookie_string):
    keys = ["CloudFront-Policy", "CloudFront-Signature", "CloudFront-Key-Pair-Id", "myz_session", "token", "myz_token", "lastVisitedHosts"]
    cookie_dict = {key: None for key in keys}
    cookies = cookie_string.split("; ")
    for cookie in cookies:
        key_value = cookie.split("=", 1)
        if key_value[0] in keys:
            try:
                cookie_dict[key_value[0]] = json.loads(key_value[1])
            except json.JSONDecodeError:
                cookie_dict[key_value[0]] = key_value[1]
                
    return cookie_dict

with open('cookies.txt', 'r') as f: cookie = f.readline()
cookie = parse_cookies(cookie)
COOKIE = {'Cookie': cookie}
SESSION = requests.Session()
SESSION.headers.update(COOKIE)
BASE_URL = input('[+] Enter book URL (search toc.xml): \n').removesuffix('/toc.xml')

toc_req = SESSION.get(f'{BASE_URL}/content.opf')
soup = BeautifulSoup(toc_req.content, 'xml')
npages = int(soup.select('itemref')[-1]['idref'].removeprefix('page'))
book_title = soup.find('dc:title').text
book_desc = soup.find('dc:description').text
book_author = soup.find('dc:author').text
book_isbn = soup.find('dc:identifier').text.split(':')[2]

def get_toc():
    soup = BeautifulSoup(SESSION.get(f'{BASE_URL}/toc.xhtml').content, 'html.parser')
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

    return tocify(dictify(ol))

def get_pdf():
    pdf_file = fitz.Document()
    progress_bar(0, npages)
    for page in range(1,npages):
        svg = fitz.open(stream=SESSION.get(f'{BASE_URL}/images/page{page:04d}.svgz').text.replace("data:image/jpg;base64", "data:image/jpeg;base64").encode(), filetype="svg")
        pdf_file.insert_pdf(fitz.open(stream=svg.convert_to_pdf()))
        progress_bar(page, npages)

    pdf_file.set_toc(get_toc())
    pdf_file.save(f"{book_title}.pdf")

def progress_bar(progress, total):
    percent = 100 * (progress / float(total))
    bar = '█' * int(percent) + '-' * (100 - int(percent))
    print(f'\r[+] Downloading book... |{bar}| {percent:.2f}%', end='\r')

print(f'''
[+] Book Found:
    - title: {book_title}
    - description: {book_desc}
    - author: {book_author}
    - isbn: {book_isbn}
    - pages: {npages}
''')
get_pdf()
print('\nDone :)')
