def LectureConfig(path):

    file = open(path, "r")
    lines = file.read().split("\n")
    values = {}

    for line in lines:
        key_values = line.split(":")
        values[key_values[0]] = CsvSplit(key_values[1], ",")

    return values

def ReadHTMLFile(path, dict):
    file = open(path, "r")
    html = file.read()

    for i in dict:
        html = html.replace("{{" + i + "}}", dict[i])

    return html

def CsvSplit(str, sep):

    array = []
    current = ""
    str += '\n'

    for i in range(len(str)):
    
        if str[i - 1] == '\\' and str[i] == sep:
            current += sep
        elif str[i - 1] != '\\' and str[i] == sep:
            array.append(current)
            current = ""
        elif i + 1 < len(str) and str[i] == '\\' and str[i + 1] == sep:
            continue
        elif str[i] == '\n':
            array.append(current)
            current = ""
        else:
            current += str[i]

    return array

dico = {"configuration_port": "80", 
        "configuration_words_to_replace": "test,test3", 
        "configuration_url_blacklist": "minecraft.fr", 
        "configuration_resources_blacklist": "text/html"}

print(ReadHTMLFile("../html/admin.html", dico))
print(LectureConfig("../options.config"))
