import argparse
from base64 import b64encode
from collections import defaultdict
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import requests

from inlineweb.http import HTTP


def inline_audio(soup, http):
    sources = soup.select("source[src]")
    for source in sources:
        r = http.get(source.attrs["src"])
        if r is not None:
            source.attrs["href"] = f"data:{r.mime};base64," + b64encode(r.content).decode('utf-8')


def inline_css(soup, http):
    links = soup.select("link[rel*=stylesheet]")
    for link in links:
        r = http.get(link.attrs["href"])
        if r is not None:
            style = soup.new_tag("style")
            style.string = r.content.decode("utf-8")
            link.replaceWith(style)


def inline_favicon(soup, http):
    links = soup.select("link[rel*=icon]")
    for link in links:
        r = http.get(link.attrs["href"])

        if r is not None:
            link.attrs["href"] = f"data:{r.mime};base64," + b64encode(r.content).decode('utf-8')


def inline_images(soup, http):
    imgs = soup.select("img[src]")

    raws = defaultdict(list)
    mime = defaultdict(str)

    for i, img in enumerate(imgs):
        img_id = f"base64_{i}"
        img.attrs["id"] = img_id

        r = http.get(img.attrs["src"])
        if r is not None:
            del img.attrs["src"]
            raws[r.content].append(img_id)
            mime[r.content] = r.mime

    script_src = "'use strict';\n"
    for i, (raw, img_ids) in enumerate(raws.items()):
        img_src = f"data:{mime[raw]};base64," + b64encode(raw).decode("utf-8")

        var = f"__base64_{i}"
        script_src += f"const {var} = '{img_src}'\n"

        for img_id in img_ids:
            script_src += f"document.getElementById('{img_id}').setAttribute('src', {var});\n"

        script_src += "\n"

    script = soup.new_tag("script")
    script.string = script_src
    soup.body.append(script)


def inline_scripts(soup, http):
    scripts = soup.select("script[src]")
    for script in scripts:
        script.string = requests.get(script.attrs['src']).text
        del script.attrs["src"]


def remove_scripts(soup):
    scripts = soup.select("script")
    for script in scripts:
        script.decompose()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str)
    parser.add_argument("-o", "--output", dest="output", default="./inline.html")
    parser.add_argument("--allow-cors", dest="allow_cors", action="store_true")
    parser.add_argument("--max-size", dest="max_size")
    parser.add_argument("--no-script", dest="allow_script", action="store_false")

    args = parser.parse_args()

    http = None
    try:
        http = HTTP(args.url,
                    allow_cors=args.allow_cors,
                    max_size=args.max_size,
                    )
    except ValueError:
        print(f"Bad argument: '{args.url}'",)

    r = http.get(args.url)
    if r is None:
        print("ERROR")
        exit(1)

    soup = BeautifulSoup(r.text, "lxml")

    # make all(?) urls absolute
    for el in soup.select("[href], [src]"):
        if "href" in el.attrs:
            href = el.attrs["href"]
            el.attrs["href"] = urljoin(args.url, href)

        if "src" in el.attrs:
            src = el.attrs["src"]
            el.attrs["src"] = urljoin(args.url, src)


    if args.allow_script:
        inline_scripts(soup, http)
    else:
        remove_scripts(soup)

    inline_audio(soup, http)
    inline_css(soup, http)
    inline_favicon(soup, http)
    inline_images(soup, http)

    with open(args.output, "w+") as f:
        f.write(soup.prettify())


if __name__ == "__main__":
    main()
