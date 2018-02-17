import re

import requests

from django.shortcuts import render

import pydash
from bs4 import BeautifulSoup


def home(request):
    url_prefix = "https://baykoreans.link"
    url = url_prefix + "/index.php"
    headers = {'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36"}

    params = dict(mid='entertain', page="1")
    params.update(**pydash.pick(request.GET, 'mid', 'page'))

    html = requests.get(url, params=params, headers=headers)
    soup = BeautifulSoup(html.content, 'html.parser')
    rows = soup.select('table.boardList tr td.title > a:nth-of-type(1)')
    query_set = {"{}={}".format(k, v) for k, v in request.GET.items()}
    current = None
    pagination = []

    for anchor in soup.find("ul", class_="pagination").find_all('a'):
        page = re.search(r'page=(\d+)', anchor.get('href'))
        page = page[1] if page else 1
        pagination.append(dict(
            text=anchor.text,
            active=params['page'] == anchor.text,
            query="mid={}&page={}".format(params['mid'], page))
        )

    content_list = []
    for row in rows:
        content = dict(title=row.text, query=row.get('href').split('?')[-1])
        content['query_set'] = set(content['query'].split('&'))
        content['is_current'] = query_set == content['query_set']
        if content['is_current']:
            current = content

        content_list.append(content)

    if current:
        content_id = next((query.split('=')[-1] for query in current['query'].split('&')
                           if query.startswith('document_srl=')))
        html = requests.get("{}/{}".format(url_prefix, content_id))
        soup = BeautifulSoup(html.content, 'html.parser')

        fonts = soup.select("font:nth-of-type(2)")
        body = fonts[0].text.strip() if fonts else ''
        if ' 팝업광고창' in body:
            body = ''

        link_element = soup.find(string="링크모음 보러가기")
        if link_element:
            url = url_prefix + link_element.find_parent('a').get('href')
            html = requests.get(url)
            soup = BeautifulSoup(html.content, 'html.parser')

        links = soup.find_all("span", string=re.compile("(SHOW|MOVIE) LINK \| "))
        links = [str(link.find_parent('a')) for link in links]
        current.update(body=body, links=links)

    context = dict(
        mid_list=['entertain', 'movie'],
        mid_param=params['mid'],
        content_list=content_list,
        current=current,
        pagination=pagination
    )

    return render(request, 'home.html', context)
