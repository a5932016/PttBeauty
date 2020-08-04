import requests
import time
import bs4
import os
import re
import urllib.request
import json
import winreg
import datetime

PTT_URL = 'https://www.ptt.cc'

def get_desktop():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, \
                         r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders', )
    return winreg.QueryValueEx(key, "Desktop")[0]

date = time.strftime("%Y%m%d")
tree = get_desktop().replace('\\', '/') + '/' + date
os.makedirs(tree)

def get_web_page(url):
    resp = requests.get(
        url=url,
        cookies={'over18': '1'}
    )
    if resp.status_code != 200:
        print('Invalid url:', resp.url)
        return None
    else:
        return resp.text

def get_articles(dom, date):
    soup = bs4.BeautifulSoup(dom, 'html5lib')

    paging_div = soup.find('div', 'btn-group btn-group-paging')
    prev_url = paging_div.find_all('a')[1]['href']

    articles = []
    divs = soup.find_all('div', 'r-ent')
    for d in divs:
        if d.find('div', 'date').text.strip() == date:

            push_count = 0
            push_str = d.find('div', 'nrec').text
            if push_str:
                try:
                    push_count = int(push_str)
                except ValueError:
                    if push_str == '爆':
                        push_count = 99
                    elif push_str.startswith('X'):
                        push_count = -10

            if d.find('a'):
                href = d.find('a')['href']
                title = d.find('a').text
                author = d.find('div', 'author').text if d.find('div', 'author') else ''
                articles.append({
                    'title': title,
                    'href': href,
                    'push_count': push_count,
                    'author': author
                })
    return articles, prev_url

def parse(dom):
    soup = bs4.BeautifulSoup(dom, 'html.parser')
    links = soup.find(id='main-content').find_all('a')
    img_urls = []
    for link in links:
        if re.match(r'^https?://(i.)?(m.)?imgur.com', link['href']):
            img_urls.append(link['href'])
    return img_urls

def save(img_urls, title):
    if img_urls:
        try:
            dname = title.strip()
            dname = tree + '/' + dname
            os.makedirs(dname)
            for img_url in img_urls:
                if img_url.split('//')[1].startswith('m.'):
                    img_url = img_url.replace('//m.', '//i.')
                if not img_url.split('//')[1].startswith('i.'):
                    img_url = img_url.split('//')[0] + '//i.' + img_url.split('//')[1]
                if not img_url.endswith('.jpg'):
                    if not img_url.endswith('.gif'):
                        img_url += '.jpg'
                fname = img_url.split('/')[-1]
                urllib.request.urlretrieve(img_url, os.path.join(dname, fname))
        except Exception as e:
            print(e)

if __name__ == '__main__':
    current_page = get_web_page(PTT_URL + '/bbs/Beauty/index.html')
    if current_page:
        articles = []
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%m/%d").lstrip('0')
        today = time.strftime("%m/%d").lstrip('0')

        for date in [today, yesterday]:
            current_articles, prev_url = get_articles(current_page, date)
            while current_articles:
                articles += current_articles
                current_page = get_web_page(PTT_URL + prev_url)
                current_articles, prev_url = get_articles(current_page, date)

            for article in articles:
                print('Processing', article)
                page = get_web_page(PTT_URL + article['href'])
                if page:
                    img_urls = parse(page)
                    save(img_urls, article['title'])
                    article['num_image'] = len(img_urls)

            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=2, sort_keys=True, ensure_ascii=False)
