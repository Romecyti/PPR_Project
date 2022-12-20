def LectureConfigArray(path):
    file = open(path, "r")
    lines = file.read().split("\n")
    values = {}

    for line in lines:
        key_values = line.split(":")
        values[key_values[0]] = CsvSplit(key_values[1], ",")

    return values

def LectureConfigString(path):
    file = open(path, "r")
    lines = file.read().split("\n")
    values = {}

    for line in lines:
        key_values = line.split(":")
        values[key_values[0]] = key_values[1]

    return values
    
def WriteConfigString(path, str):
    file = open(path, "w")
    file.write(str)

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