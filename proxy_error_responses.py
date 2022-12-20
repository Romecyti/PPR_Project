from enum import IntEnum, unique
from socket import socket


#definition d'un enum class pour enregistrer les différentes valeur de codes http traitées par la fonction si dessous
#@verify(UNIQUE)
@unique
class HTTPERRORCODE(IntEnum) :
    code400 = 400, #"400 Bad Request"
    code403 = 403, #"403 Forbidden",
    code415 = 415, #"415 Unsupported Media Type",
    code503 = 503, #"503 Service Unavailable"

    #redéfinition de str pour mettre les codes erreurs associés
    def __str__(self):
        if self == HTTPERRORCODE.code503 :
            return "503 Service Unavailable"
        elif self == HTTPERRORCODE.code415 :
            return "415 Unsupported Media Type"
        elif self == HTTPERRORCODE.code403 :
            return "403 Forbidden"
        elif self == HTTPERRORCODE.code400 :
            return "400 Bad Request"

#fonction qui renvoie un message d'erreur sur la socket selon le code passer en argument
def ErrorResponse(aim_socket : socket, code : HTTPERRORCODE) :
    message = b''
    match code :
        case HTTPERRORCODE.code503 :
            message += (b'HTTP/1.0 ' + str(HTTPERRORCODE.code503).encode() + b'\r\n')
        case HTTPERRORCODE.code415 :
            message += (b'HTTP/1.0 ' + str(HTTPERRORCODE.code415).encode() + b'\r\n')
        case HTTPERRORCODE.code403 :
            message += (b'HTTP/1.0 ' + str(HTTPERRORCODE.code403).encode() + b'\r\n')
        case _: #the case HTTPERRORCODE.code400 : is the same as default
            message += (b'HTTP/1.0 ' + str(HTTPERRORCODE.code400).encode() + b'\r\n')

    #on complete maintenant la réponse avec le reste de l'entete

    message += b'Server : Proxy server\r\n'
    message += b'\r\n'

    aim_socket.sendall(message)
