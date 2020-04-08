import re
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from pydash import py_

from django.shortcuts import render


def home(request):
    url_prefix = "https://dongyoungsang.club"
    url = url_prefix + "/bbs/board.php"
    headers = {'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36"}

    category_key = 'bo_table'
    params = {category_key: 'en', 'page': "1"}
    params.update(**{k: v for k, v in request.GET.items()})

    html = requests.get(url, params=params, headers=headers)
    soup = BeautifulSoup(html.content, 'html.parser')

    # pagination
    pagination = []
    for anchor in soup.find("ul", class_="pagination").find_all('a'):
        href = anchor.get('href')
        if not href or anchor.find('i'):
            continue

        pagination.append(dict(
            text=anchor.text,
            active=params['page'] == anchor.text,
            query=href.split('?')[-1],
            blank_url=url_prefix + href if '이전자료검색' in anchor.text else None
        ))

    # menu
    menu_anchor = py_.find(soup.select('div#nt_body a.list-group-item'), lambda a: a.text == '다시보기')
    menu_list = py_(menu_anchor.find_next_siblings('a')).map(
        lambda a: (a.get('href').strip('/'), a.text)
    ).filter(
        # TODO: include movie/ani
        lambda m: '/' not in m[0]
    ).value()

    # content list
    rows = soup.select('ul.bo_list a#link')
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

    # current content
    if current:
        body = str(soup.select_one('div#bo_v_con > div:nth-of-type(2)') or '')

        content_anchor = soup.select_one('section#bo_v_atc > div:nth-of-type(2) > a.btn')
        content_href = content_anchor.get('href')
        content_url = url_prefix + content_href

        response = requests.get(content_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        links = soup.select('section#bo_v_atc a.btn')
        re_link = re.compile(r'(href=[\'"])(https?://[^?]+\?(https?://[^\'"]+))')

        links = py_.map(links, lambda a: re_link.sub(r'\1\3', str(a)))
        current.update(body=body, links=links, source=content_url)

    context = dict(
        menu_list=menu_list,
        category_key=category_key,
        category=params.get(category_key) or '',
        content_list=content_list,
        current=current,
        pagination=pagination
    )
    return render(request, 'home.html', context)
