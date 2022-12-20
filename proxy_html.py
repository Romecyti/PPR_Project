def ReadHTMLFile(path, dict):
    file = open(path, "r")
    html = file.read()

    for i in dict:
        html = html.replace("{{" + i + "}}", dict[i])
    
    return html

def SendHTMLToClient(path, socket_client, dict):
    html = ReadHTMLFile(path, dict)
    encoded_html = html.encode()
    
    reponse = "HTTP/1.1 200 OK\n"\
              "Connection: Keep-Alive\n"\
              "Content-Length: " + str(len(encoded_html)) + "\n"\
              "Content-Type: text/html; charset=utf-8\n\n"
    reponse += html

    socket_client.sendall(reponse.encode())