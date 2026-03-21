import socket
from bs4 import BeautifulSoup
import re
import sys
import ssl
import os
import hashlib


def parse_url(url):
    scheme = url.split("://")[0]
    if scheme == "http":
        port = 80
    elif scheme == "https":
        port = 443
    else:
        raise ValueError("Unsupported URL scheme")
    rest = url.split("://")[1]

    if "/" in rest:
        host, path = rest.split("/", 1)
        path = "/" + path
    else:
        host = rest
        path = "/"

    return port, host, path

def get_cache_key(url):
    return hashlib.md5(url.encode()).hexdigest()

def check_cache(url):
    key = get_cache_key(url)
    path = f"cache/{key}"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None

def save_to_cache(url, body):
    os.makedirs("cache", exist_ok=True)
    key = get_cache_key(url)
    path = f"cache/{key}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)

def make_request(url):

    ##first check the cache, then save if not there
    cached = check_cache(url)
    if cached is not None:
        print("Getting from cache...")
        return cached

    print("Getting from web...")
    port, host, path = parse_url(url)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))

    if port == 443:
        context = ssl.create_default_context()
        s = context.wrap_socket(s, server_hostname=host)

    request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\n"
            f"Accept: text/html\r\n"
            f"Accept-Language: en-US,en;q=0.9\r\n"
            f"Connection: close\r\n\r\n"
        )      
    s.sendall(request.encode())

    response  = b""
    while True:
        data = s.recv(4096)
        if not data:
            break
        response += data
        
    s.close()
    headers, body = response.decode().split("\r\n\r\n", 1)
    body = handle_redirection(headers, body)

    save_to_cache(url, body)

    return body

def handle_redirection(headers, body):

    # handle 301/302
    if get_status(headers) in (301, 302, 303, 307, 308):
        # print("Redirection detected, following...")
        headers_lines = headers.split("\r\n")
        for line in headers_lines:
            if line.lower().startswith("location:"):
                new_url = line.split(": ", 1)[1].strip()
        return make_request(new_url)

    # handle JS/meta redirects
    if 'window.parent.location.replace' in body or "http-equiv='refresh'" in body.lower():
        soup_redirect = BeautifulSoup(body, "html.parser")
        meta = soup_redirect.find("meta", attrs={"http-equiv": lambda x: x and x.lower() == "refresh"})
        if meta:
            content = meta.get("content", "")
            new_url = content.split("URL=")[-1].strip('"\'')
            # print("JS redirect detected, following...")
        return make_request(new_url)
    return body
    
def get_status(headers):
    first_line = headers.split("\r\n")[0]
    return int(first_line.split(" ")[1])
     

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: go2web -h for help")
        sys.exit(1)
   
    if sys.argv[1] == "-h":
        print("Usage:")
        print("  go2web -u <URL>         # make an HTTP request and print the response")
        print("  go2web -s <search-term> # search and print top 10 results")
        print("  go2web -h               # show this help")
    
    elif sys.argv[1] == "-u":
        if len(sys.argv) < 3:
            print("Error:  -u requires a URL")
            sys.exit(1)
        url = sys.argv[2]
        body = make_request(url)

        body = re.sub(r'^[0-9a-fA-F]+\r?\n', '', body, flags=re.MULTILINE)
        soup = BeautifulSoup(body, "html.parser")
        print(soup.get_text(separator="\n", strip=True))

    elif sys.argv[1] == "-s":
        if len(sys.argv) < 3:
            print("Error:  -s requires a search term")
            sys.exit(1)
        search_term = " ".join(sys.argv[2:])

        url = f"https://html.duckduckgo.com/html/?q={search_term.replace(' ', '+')}"
        body = make_request(url)
        
        body = re.sub(r'^[0-9a-fA-F]+\r?\n', '', body, flags=re.MULTILINE)
        soup = BeautifulSoup(body, "html.parser")
        results = soup.find_all("a", class_="result__a")[:10]

        for i, result in enumerate(results, 1):
            title = result.get_text(strip=True)
            url = result.get("href")
            if url.startswith("//"):
                url = "https:" + url
            print(f"{i}. {title}")
            print(f"   {url}")
            print()

        print("Enter a number to fetch a result (0 to exit): ", end="")
        choice = int(input().strip())
        if choice > 0 and choice <= 10:
            selected_url = results[choice - 1].get("href")
            print(selected_url)
            if selected_url.startswith("//"):
                selected_url = "https:" + selected_url

            print(f"Fetching: {selected_url}")
            body = make_request(selected_url)    

            body = re.sub(r'^[0-9a-fA-F]+\r?\n', '', body, flags=re.MULTILINE)
            soup = BeautifulSoup(body, "html.parser")
            print(soup.get_text(separator="\n", strip=True))

    else:
        print("Unknown flag. Use go2web -h for help")
        sys.exit(1)
