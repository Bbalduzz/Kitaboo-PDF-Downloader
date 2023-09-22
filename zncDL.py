import fitz  # PyMuPDF
import requests
from tqdm import tqdm
from Crypto.Cipher import AES
from dataclasses import dataclass
from bs4 import BeautifulSoup
from Crypto.Cipher import Blowfish
from Crypto.Util.Padding import unpad
import base64
import os, re

'''
what you need:
- cookies
- encryption_key: on console -> window.angularComponentRef.render.settings.encResource
- ebook_id
'''

@dataclass
class Book:
    title: str
    pages: int
    description: str
    author: str
    isbn: str

class Znc:
    def __init__(self, ebook_id):
        self.session = requests.Session()
        self.session.headers.update(self.parse_cookies())
        self.encryption_key = ""
        self.ebook_id = ebook_id

    @staticmethod
    def parse_cookies():
        with open('cookies.txt', 'r') as f: cookie_string = f.readline()
        keys = ["CloudFront-Policy", "CloudFront-Signature", "CloudFront-Key-Pair-Id", "myz_session", "token", "myz_token", "lastVisitedHosts"]
        result = []
        for key in keys:
            pattern = f'{key}=([^;]*)'
            if match := re.search(pattern, cookie_string):
                result.append(f'{key}={match[1]}')
        return {'Cookie': '; '.join(result)}

    def get_toc(self):
        soup = BeautifulSoup(self.session.get(f'https://webreader.zanichelli.it/{self.ebook_id}/html5/{self.ebook_id}/OPS/toc.xml').content, 'html.parser')
        def dictify(node):
            result = {}
            for child_node in node.find_all("node", recursive=False):
                page_id = child_node['id']
                page = -1 if any(char.isalpha() for char in page_id) else int(page_id)
                key = child_node['title']
                result[key] = [page, dictify(child_node) if child_node.find("node") else None]
            return result

        def tocify(toc_dict):
            toc = []
            for key, value in toc_dict.items():
                toc.append([1, key, value[0]])
                if value[1]:
                    toc.extend([2, sub_key, sub_value[0]] for sub_key, sub_value in value[1].items())
            return toc

        return tocify(dictify(soup.toc))


    def get_page(self, url):
        response = self.session.get(url)
        if response.headers.get('X-Amz-Server-Side-Encryption') == 'AES256':
            cipher = AES.new(self.encryption_key.encode('utf-8'), AES.MODE_CBC, iv=self.encryption_key.encode('utf-8'))
            decrypted_bytes = cipher.decrypt(base64.b64decode(response.text))
            decrypted_text = decrypted_bytes.rstrip(b"\x01...\x0F").decode('utf-8')
            return decrypted_text.replace("data:image/jpg;base64", "data:image/jpeg;base64").encode()
        return response.text.replace("data:image/jpg;base64", "data:image/jpeg;base64").encode()

    def download_ebook(self):
        response = self.session.get(f'https://webreader.zanichelli.it/{self.ebook_id}/html5/{self.ebook_id}/OPS/content.opf')
        soup = BeautifulSoup(response.text, 'lxml')
        book = Book(title=soup.find('dc:title').text, pages=int(soup.select('itemref')[-1]['idref'].removeprefix('page')), description=soup.find('dc:description').text, author=soup.find('dc:author').text, isbn=soup.find('dc:identifier').text.split(':')[2])
        print(f'''
[+] Book Found:
    - title: {book.title}
    - author: {book.author}
    - isbn: {book.isbn}
    - pages: {book.pages}
''')
        items = {}
        for item in soup.find_all('item'):
            media_type = item.get('media-type')
            if media_type in ['image/svg+xml', 'image/png', 'image/jpeg']:
                items[item.get('id')] = item.get('href')

        pdf_file = fitz.Document()
        itemrefs = soup.find_all('itemref')
        for itemref in tqdm(itemrefs, desc="Downloading", ncols=100):
            idref = itemref.get('idref')
            img_url = f'https://webreader.zanichelli.it/{self.ebook_id}/html5/{self.ebook_id}/OPS/{items.get(f"images{idref}svgz", items.get(f"images{idref}png", items.get(f"images{idref}jpg")))}'
            if 'svgz' in img_url:
                svg = fitz.open(stream=self.get_page(img_url), filetype="svg")
                pdf_file.insert_pdf(fitz.open(stream=svg.convert_to_pdf()))
            else: # any other
                pix = fitz.Pixmap(img_data)
                pdf_file.insert_image((0, 0, pdf_file[0].rect.width, pdf_file[0].rect.height), pixmap=pix)

        try: toc = self.get_toc()
        except: pass
        pdf_file.set_toc(toc)
        pdf_file.save(f"{book.title}.pdf")


if __name__ == "__main__":
    BOOKID = ""
    znc_instance = Znc(BOOKID)
    znc_instance.download_ebook()
