import asyncio
import re
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from pydash import py_

from django.shortcuts import render


def home(request):
    url_prefix = "https://dongyoungsang.net"
    url = url_prefix + "/index.php"
    headers = {'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36"}

    # search_target=title&search_keyword=무한도전
    params = dict(mid='entertain', page="1")
    params.update(**{k: v for k, v in request.GET.items()})

    html = requests.get(url, params=params, headers=headers)
    soup = BeautifulSoup(html.content, 'html.parser')
    pagination = []

    for anchor in soup.find("ul", class_="pagination").find_all('a'):
        pagination.append(dict(
            text=anchor.text,
            active=params['page'] == anchor.text,
            query=anchor.get('href').split('?')[-1]
        ))

    menu_anchor = next((a for a in soup.select("div.container div.list-group a") if a.text == '다시보기'))
    menu_list = [(anchor.get('href').split('/')[-1], anchor.text) for anchor in menu_anchor.find_next_siblings('a')]

    rows = soup.select('table.boardList tr td.title > a:nth-of-type(1)')
    query_set = {f"{k}={quote_plus(v)}" for k, v in request.GET.items()}
    current = None
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

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def request_async():
            futures = [
                loop.run_in_executor(
                    None,
                    requests.get,
                    f"{url_prefix}/ooo/{int(content_id) + i}"
                ) for i in range(2)
            ]
            return await asyncio.gather(*futures)

        responses = loop.run_until_complete(request_async())
        loop.close()

        response = py_(responses).map(
            lambda r: dict(soup=BeautifulSoup(r.content, 'html.parser'), url=r.url)
        ).find(
            lambda r: r['soup'].title.text.endswith(current['title'].strip())
        ).value()

        soup = response['soup']
        fonts = soup.select("font:nth-of-type(2)")
        body = fonts[0].text.strip() if fonts else ''
        if ' 팝업광고창' in body:
            body = ''

        link_element = soup.find(string="링크모음 보러가기")
        if link_element:
            url = url_prefix + link_element.find_parent('a').get('href')
            html = requests.get(url)
            soup = BeautifulSoup(html.content, 'html.parser')

        links = soup.find_all("span", string=re.compile("(SHOW|MOVIE|DRAMA)(.*)? LINK \| "))
        links = [str(link.find_parent('a')) for link in links]
        current.update(body=body, links=links, source=response['url'])

    context = dict(
        menu_list=menu_list,
        mid_param=params['mid'],
        content_list=content_list,
        current=current,
        pagination=pagination
    )

    return render(request, 'home.html', context)
