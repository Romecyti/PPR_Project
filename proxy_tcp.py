import re
import socket

#fonction qui lit une requete (que ce soit une entete de réponse TCP ou une requete TCP)
def LectureRequete(socket_tcp):
    requete = b""
    probleme_lecture = False

    ligne_courante = b""
    #boucle de lecture de l'entete
    while 1:
        caractere_courant = socket_tcp.recv(1)
        if not caractere_courant :
            probleme_lecture = True
            break
        if caractere_courant == b'\r' :
            ligne_courante += caractere_courant
            caractere_courant = socket_tcp.recv(1)
            if caractere_courant == b'\n' :
                ligne_courante += caractere_courant
                requete += ligne_courante
                if ligne_courante == b'\r\n' :
                    break #fin de l'entete
                else :
                    ligne_courante = b'' #si ce n'est pas la fin, on remet la ligne courante à zéro
            else :
                ligne_courante += caractere_courant
        else :
            ligne_courante += caractere_courant #sinon c'est caractere lambda
        
    return (requete, probleme_lecture)

#fonction qui créer une socket de connexion à un serveur d'après son numéro de port et son nom et retourne cette socket ainsi que la réussite de la création
def CreationSocketServeur(num_port_serveur, nom_serveur) :
    probleme_creation_socket_serveur = False
    serveur_adresse_ip = socket.gethostbyname(nom_serveur)
    socket_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try :
        socket_serveur.connect((serveur_adresse_ip, int(num_port_serveur)))
    except Exception as e :
        print(e.args)
        probleme_creation_socket_serveur = True

    return (socket_serveur, probleme_creation_socket_serveur)

#fonction qui lit une entete TCP et qui retourne la taille des données qui suivent cette entete
def LectureEnteteTCP(socket_tcp):
    entete, probleme_lecture = LectureRequete(socket_tcp)

    if probleme_lecture :
        return entete, None, probleme_lecture
    else :
        #s'il n'y a pas de problème de lecture de l'entete TCP
        #alors on va chercher la taille des données qui suivent cette entete
        lignes_entete = entete.decode().split("\n")
        taille_information = None

        for e in lignes_entete :
            if re.match(r"Content-Length:[\s\S]*", e, re.IGNORECASE) :
                taille_information = re.search(r"Content-Length: (?P<tailleinformation>[0-9]+)?", e).group('tailleinformation')
         
        if taille_information != None :
            taille_information = int(taille_information)
        else :
            taille_information = 0

        return (entete, taille_information, probleme_lecture)