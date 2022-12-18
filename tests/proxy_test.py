#!usr/bin/python3

#copyright 2022 : written by MARCHAND Célestin, PIERRET Alexandre and COQUERON Solal 

#scrypt décrivant un proxy créé dans le cadre du projet de la matière "protocole et programmation réseaux" de la 1ère année du master ISICG à L'université de Limoges


import socket
import re


# lis une entete de message tcp (se finit toujours par une ligne vide)
def lectureEntete(socket_reponse):
    entete = b""
    probleme = False

    lignecourante = b""

    while 1 :
        caractere_courant = socket_reponse.recv(1)
        if not caractere_courant :
            probleme = True
            break
        if caractere_courant == b'\r' :
            lignecourante += caractere_courant
            caractere_courant = socket_reponse.recv(1)
            if caractere_courant == b'\n' :
                lignecourante += caractere_courant
                entete += lignecourante
                if lignecourante == b'\r\n' :
                    break #fin de l'entete
                else :
                    lignecourante = b'' #on passe à une nouvelle ligne
        else :
            lignecourante += caractere_courant   

    #on va venir chercher la taille des informations qui suivent l'entete
    tailleinformation = re.match(r"[\s\S]*(Content-Length: (?P<ContentLength>[0-9]+))?[\s\S]*",entete.decode(), flags= re.IGNORECASE).group('ContentLength')

    if tailleinformation != None :
        tailleinformation = int(tailleinformation)
    return entete, tailleinformation



#création du serveur
adresse_IP = "" #adresse de la machine (pas besoin de préciser, elle sera mise à défault sur une adresse en 127.)
port_serveur = 8080 #port du proxy (ici on en met un qui est public)
tsap_serveur = (adresse_IP,port_serveur)

socket_configuration = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP) #création de la socket d'attente de connexion
socket_configuration.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1) #permet de ne pas attendre pour réutiliser le numéro de port
socket_configuration.bind(tsap_serveur) #accroche le numéro de port à la socket

socket_configuration.listen(1) #ici on limite le nombre de connexion à 1 car le serveur ne fera des requête que 1 à 1

while 1:
    (socket_navigateur, tsap_client) = socket_configuration.accept() #on attend un connexion de la part du navigateur

    requete = socket_navigateur.recv(1000) #on s'attend à une requête composée de moins de 1000 caractères
    if requete :
        #print("requete origine : \n", requete, "\n")
        requete = requete.decode().split("\n")  # à modifier pour lire uniquement l'entete car post renvoie des infos en plus (notamment des caractère non utf-8)
        #on va regarder si la requete est en http ou https
        if(re.search('CONNECT',requete[0])) :
            #cas d'une requête https
            print("CONNECT requete :\n",requete)
        else :
            #cas d'une requête http
            #on va d'abord chercher le nom du site 
            serveur_web_name = re.match(r"([^\s]+) ([^\s]+)", requete[1]).group(2)
            #on récupère ensuite les informations nécessaire à la requête
            (navigateur_serveur_methode_requete, navigateur_serveur_complete_name, navigateur_serveur_num_port, navigateur_serveur_file_access) = re.match(r"(?P<method>[^\s]+) (?P<Complete_Serveur_Name>[^\s]+"+serveur_web_name+r")(:(?P<num_Port>\d+))?(?P<file_access>[^\s]+) (?P<HTTP_Version>[^\s]+)",requete[0]).group('method','Complete_Serveur_Name','num_Port','file_access')
            if navigateur_serveur_num_port == None:
                navigateur_serveur_num_port = "80"
            
            #on va maintenant créer une socket qui va se connecter au serveur demandé par le navigateur
            navigateur_serveur_adresse_ip = socket.gethostbyname(serveur_web_name)
            navigateur_serveur_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            try :
                navigateur_serveur_socket.connect((navigateur_serveur_adresse_ip, int(navigateur_serveur_num_port)))
            except Exception as e :
                print(e.args)
                break
            
            #maintenant que la socket est créée, on peut envoyer les données au serveur
            #on va d'abord enlever les données inutile
            requete[0] = navigateur_serveur_methode_requete + " "+ navigateur_serveur_file_access + " HTTP/1.0\r" #on vient s'assurer d'envoyer les requetes en version 1.0 du HTTP
            proxys_request = []
            for e in requete :
                if not re.match(r"Connection: Keep-Alive[\s\S]*|Proxy-Connection: Keep-Alive[\s\S]*|Accept-Encoding: gzip[\s\S]*", e, flags=re.IGNORECASE) :
                    proxys_request.append(e)

           # print("requete proxy :\n",proxys_request,"\n\n")
            real_proxys_request = ""
            for e in proxys_request :
                if(e != "") :
                    real_proxys_request += e+"\n"

            real_proxys_request = real_proxys_request.encode()

            #print("requete proxy :\n",real_proxys_request, "\n\n")

            navigateur_serveur_socket.sendall(real_proxys_request)
            #on attends ensuite la réponse du serveur (on va d'abord lire l'entête)
            message, content_length = lectureEntete(navigateur_serveur_socket)

            if content_length != None :
                while content_length > 2048:
                    message += navigateur_serveur_socket.recv(2048)
                    content_length -= 2048
                message += navigateur_serveur_socket.recv(content_length)

            socket_navigateur.sendall(message)

            #on peut désormais tuer la socket 
            navigateur_serveur_socket.close()
            
    socket_navigateur.close() #on ferme la socket de connexion du navigateur pour permettre une nouvelle requête

socket_configuration.close() #on ferme la socket d'attente de connexion