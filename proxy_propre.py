#!usr/bin/python3

#copyright 2022 : written by MARCHAND Célestin, PIERRET Alexandre and COQUERON Solal 

#scrypt décrivant un proxy créé dans le cadre du projet de la matière "protocole et programmation réseaux" de la 1ère année du master ISICG à L'université de Limoges


import socket
import re

#fonction qui créait la socket principale du proxy
def CreateProxysSocket(adresse_ip_proxy, port_socket_proxy) :
    tsap_proxy = (adresse_ip_proxy, port_socket_proxy)

    #création et paramétrisation de la socket
    socket_proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1) #permet de ne pas attendre pour pouvoir réutiliser ce port
    socket_proxy.bind(tsap_proxy) #accroche la socket au numro du port de la machine concernée
    socket_proxy.listen(1)

    return socket_proxy

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
            ligne_courante += caractere_courant #sinon c'est caractere lambda
        
    return (requete, probleme_lecture)

#fonction qui lit une entete TCP et qui retourne la taille des données qui suivent cette entete
def LectureEnteteTCP(socket_tcp):
    entete, probleme_lecture = LectureRequete(socket_tcp)

    if probleme_lecture :
        return entete, None, probleme_lecture
    else :
        #s'il n'y a pas de problème de lecture de l'entete TCP
        #alors on va chercher la taille des données qui suivent cette entete
        lignes_entete = entete.decode().split("\n")

        tailleinformation = None

        for e in lignes_entete :
            if re.match(r"Content-Length:[\s\S]*", e, re.IGNORECASE) :
                tailleinformation = re.search(r"Content-Length: (?P<tailleinformation>[0-9]+)?", e).group('tailleinformation')

        if tailleinformation != None :
            tailleinformation = int(tailleinformation)
        else :
            tailleinformation = 0

        return (entete, tailleinformation, probleme_lecture)

#fonction qui traite l'entete d'une requete et retourne une entete nettoyer des parametre proxy ainsi que le numéro de port du serveur web et de son nom
def TraitementRequete(requete) :
    requete = requete.decode().split("\n") #sépare l'entete de la requête selon les lignes
    nom_serveur = re.match(r"([^\s]+) ([^\s]+)", requete[1]).group(2)

    #on vient récupérer les informations importante situé sur la première ligne
    (serveur_methode_requete, num_port_serveur, serveur_file_access) = re.match(r"(?P<method>[^\s]+) ([^\s]+"+nom_serveur+r")(:(?P<num_Port>\d+))?(?P<file_access>[^\s]+) ([^\s]+)",requete[0]).group('method','num_Port','file_access')
    if num_port_serveur == None:
        num_port_serveur = "80"

    #on nettoye la première ligne en la reformattant au format http (version 1.0)
    requete[0] = serveur_methode_requete + " " + serveur_file_access + " HTTP/1.0\r"

    #on enleve maintenant les lignes ne concernant que le proxy :
    proxys_request = []
    for e in requete :
        if not re.match(r"Connection: Keep-Alive[\s\S]*|Proxy-Connection: Keep-Alive[\s\S]*|Accept-Encoding: gzip[\s\S]*", e, flags=re.IGNORECASE) :
            proxys_request.append(e)
    
    requete = "\n".join(proxys_request)
    requete = requete.encode()

    return (requete, num_port_serveur, nom_serveur)

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



#fonction décrivant le proxy
def main(adresse_ip_proxy = "", port_socket_proxy = 8080) :
    socket_proxy = CreateProxysSocket(adresse_ip_proxy, port_socket_proxy)

    #début d'écoute des requêtes faites au proxy
    while 1 :
        (socket_requete, tsap_requete) = socket_proxy.accept() #retourne une socket et le tsap associé a celle-ci (inutile ici) lorsqu'une connexion à lieu sur le port
        (requete, probleme_requete) = LectureRequete(socket_requete)

        #on regarde si la lecture de la requete s'est déroulé normalement
        if not probleme_requete :
            #dans ce cas, on peut faire notre traitement
            #on va d'abord regarder quel est le protocole (http ou https)
            if (re.search('CONNECT', requete.decode())) :
                #dans ce cas, c'est le porotocole https
                #pour le moment, on ne le traite pas 
                print("requete https : \n", requete, "\n\n")
            else :
                #dans ce cas, c'est une requete http

                #on va faire les traitements nécessaires pour nettoyer la requete et enlever les infos inutile pour le serveur 
                #ainsi que récupérer les informations nécessaire a l'envoie de la requete au serveur web
                requete, num_port_serveur, nom_serveur = TraitementRequete(requete)
                suite_requete = b'' #si la requette est une requete POST, alors il y aura des arguments suplémentaire 

                #on regarde maintenant si c'est une requete GET ou POST
                if re.search('POST', requete.decode(), flags=re.IGNORECASE) :
                    #dans ce cas, c'est une requete POST et l'on doit donc lire les arguments supplémentaire de la requête
                    #ceux-ci se trouvent dans un bloc supplémentaire de la même forme qu'une requête
                    suite_requete, probleme_requete = LectureRequete
                #end if

                #on regarde s'il y a eu un problème dans la lecture des arguments de la requete POST
                #(si jamais on avait une requete GET, alors cela ne changera pas la requete de base)
                if not probleme_requete :
                    requete += suite_requete
                    socket_serveur, probleme_creation_socket_serveur = CreationSocketServeur(num_port_serveur, nom_serveur)

                    #on regarde si la socket vers le serveur à pu être créée
                    if not probleme_creation_socket_serveur :
                        #si oui, alors on va envoyer la requete au serveur
                        socket_serveur.sendall(requete)

                        #on lit ensuite l'entete de la réponse du serveur
                        entete_reponse, taille_reponse, probleme_lecture_entete_reponse = LectureEnteteTCP(socket_serveur)

                        if not probleme_lecture_entete_reponse :
                            #s'il n'y a pas eu de problème lors de la lecture de l'entete de réponse, on peut continuer la lecture de la réponse
                            reponse = entete_reponse
                            while taille_reponse > 0:
                                reponse += socket_serveur.recv(1)
                                taille_reponse -= 1
                            #end while
                            #on envoie ensuite toute la réponse au navigateur
                            socket_requete.sendall(reponse)
                        else :
                            print("problème lecture entete réponse\n\n")
                        #end if
                    else :
                        print("problème création socket serveur\n\n")
                    #end if
                #end if
            #end if
        #end if
        #le traitement de la requete est finit, on peut fermer la socket et reccomencer la boucle
        socket_requete.close()

    socket_proxy.close()

    #end while

    return 0


#on appelle le main si jamais le script à bien été lancé en scrypt principale
if __name__ == "__main__" :
    main()