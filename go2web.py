import socket
from bs4 import BeautifulSoup
import re


host = "example.com"
port = 80


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))

request = f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
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
