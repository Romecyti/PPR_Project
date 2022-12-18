def ReadHTMLFile(path, dict):
    file = open(path, "r")
    html = file.read()

    for i in dict:
        html = html.replace("{{" + i + "}}", dict[i])

    return html

def SendHTMLToClient(path, socket_client, dict):
    html = ReadHTMLFile(path, dict)
    reponse = "HTTP/1.1 200 OK\r\n"\
              "Connection: Keep-Alive\r\n"\
              "Content-Length: " + str(len(html)) + "\r\n"\
              "Content-Type: text/html; charset=utf-8\r\n"\
              "\n"
    reponse += html
    socket_client.sendall(reponse.encode())