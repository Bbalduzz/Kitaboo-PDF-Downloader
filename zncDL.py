import json
import requests
import time
import re
from bs4 import BeautifulSoup
from base64 import b64decode, b64encode
import fitz
import xml.etree.ElementTree as et

'''
HOW TO USE:
- copy link of the "Leggi il libro online" hyperlink
- paste it once run the script
'''

clientid = b64encode("ZanichelliAdapter".encode())

def progress_bar(progress, total):
    percent = 100 * (progress / float(total))
    bar = '█' * int(percent) + '-' * (100 - int(percent))
    print(f'\r[+] Downloading book... |{bar}| {percent:.2f}%', end='\r')

def downloadbook(url):
	session = requests.Session()
	index = session.get(url, allow_redirects=False)
	myz_session = re.findall("value='(.*?)'",str(list(index.cookies)))[0]
	location = index.headers["Location"]
	params = {i.split("=")[0]: i.split("=")[1] for i in location.split("?")[-1].split("&")}
	tokenvalidation = session.get("https://zanichelliservices.kitaboo.eu/DistributionServices/services/api/reader/user/123/pc/validateUserToken", params={"usertoken": params["usertoken"], "t": int(time.time()), "clientID": clientid}).json()
	usertoken = tokenvalidation["userToken"]
	bookdetails = requests.get("https://zanichelliservices.kitaboo.eu/DistributionServices/services/api/reader/distribution/123/pc/book/details", params={"bookID": params["bookID"], "t": int(time.time())}, headers={"usertoken": usertoken}).json()
	book = bookdetails["bookList"][0]

	if book["encryption"]:
		print("Encrypted books unsupported!")

	ebookid = book["book"]["ebookID"]
	bookid = book["book"]["id"]
	auth = session.get("https://webreader.zanichelli.it/ContentServer/mvc/authenticatesp", params={"packageId": ebookid, "ut": usertoken, "ds": "y", "t": int(time.time())})
	bearer = auth.headers["Authorization"]
	token = bearer.replace('Bearer ', '')

	session.cookies.update({
	    'myz_session': myz_session,
	    'token': token
	})
	session.headers.update({
	    'usertoken': usertoken,
	})
	params = {'state': 'online'}
	response = session.get(
	    f'https://webreader.zanichelli.it/downloadapi/auth/contentserver/book/123234234/HTML5/{bookid}/downloadBook',
	    params=params,
	)
	baseurl = json.loads(response.content.decode())['responseMsg'].split('?')[0]
	cfkeypairid, cfpolicy, cfsignature = re.findall("value='(.*?)'", str(list(response.cookies)))

	COOKIE = {
		'CloudFront-Policy': cfpolicy,
		'CloudFront-Signature': cfsignature,
		'CloudFront-Key-Pair-Id': cfkeypairid,
		'myz_session': myz_session
	}

	def get_toc():
		soup = BeautifulSoup(requests.get(f'https://webreader.zanichelli.it/{ebookid}/html5/{ebookid}/OPS/toc.xhtml', cookies=COOKIE).content, 'html.parser')
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
		npages = book['book']['pages']
		progress_bar(0, npages)
		for page in range(1,npages):
			svg = fitz.open(stream=session.get(f'https://webreader.zanichelli.it/{ebookid}/html5/{ebookid}/OPS/images/page{page:04d}.svgz').text.replace("data:image/jpg;base64", "data:image/jpeg;base64").encode(), filetype="svg")
			pdf_file.insert_pdf(fitz.open(stream=svg.convert_to_pdf()))
			progress_bar(page, npages)

		pdf_file.set_toc(get_toc())
		pdf_file.save(f"{book['book']['title']}.pdf")

	print(f'''
[+] Book Found:
    - title: {book['book']['title']}
    - description: {book['book']['description']}
    - author: {book['book']['author']}
    - isbn: {book['book']['isbn']}
    - pages: {str(book['book']['pages'])}
''')
	get_pdf()

book_link = input('Enter the book link:\n')
downloadbook(book_link)
