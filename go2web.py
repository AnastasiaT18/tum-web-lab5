import socket
from bs4 import BeautifulSoup
import re
import sys
import ssl



host = "example.com"
port = 80

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
        port, host, path = parse_url(url)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))

        if port == 443:
            context = ssl.create_default_context()
            s = context.wrap_socket(s, server_hostname=host)

        request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        s.sendall(request.encode())

        response  = b""
        while True:
            data = s.recv(4096)
            if not data:
                break
            response += data
        
        s.close()
        headers, body = response.decode().split("\r\n\r\n", 1)

        body = re.sub(r'^[0-9a-fA-F]+\r?\n', '', body, flags=re.MULTILINE)
        soup = BeautifulSoup(body, "html.parser")
        print(soup.get_text(separator="\n", strip=True))

    elif sys.argv[1] == "-s":
        if len(sys.argv) < 3:
            print("Error:  -s requires a search term")
            sys.exit(1)
        search_term = " ".join(sys.argv[2:])
        print(search_term)

        url = f"https://html.duckduckgo.com/html/?q={search_term.replace(' ', '+')}"
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
        headers, body = response.decode("utf-8", errors="ignore").split("\r\n\r\n", 1)
        
        body = re.sub(r'^[0-9a-fA-F]+\r?\n', '', body, flags=re.MULTILINE)
        soup = BeautifulSoup(body, "html.parser")
        results = soup.find_all("a", class_="result__a")[:10]

        for i, result in enumerate(results, 1):
            title = result.get_text(strip=True)
            url = result.get("href")
            print(f"{i}. {title}")
            print(f"   {url}")
            print()

    else:
        print("Unknown flag. Use go2web -h for help")
        sys.exit(1)
