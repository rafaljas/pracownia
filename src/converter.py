
import pprint

def extract(lines):
    #pprint.pprint(lines[:5])
    records = {}
    sr = ""
    s_type = {
        'w' : 'wieczorowe',
        'd' : 'stacjonarne'
        }
    for l in lines[1:]:
        
        l = l.strip().split(";")
        person = {}
        person['indx'] =      l[1].strip()
        person['year'] =      l[2].strip()
        person['s:type'] =    s_type[l[3].strip()]
        person['pers:lname']= convert_line(l[5].strip()).decode("cp1250").encode("UTF-8")
        person['pers:name'] = convert_line(l[6].strip()).decode("cp1250").encode("UTF-8")
        for k in ['ad:main', 'as:addi', 'phone', 'e-mail', 'pers:desc']:
            person[k] = ""
        person['univ'] = "Uniwersytet Wrocławski"
        person['faculty'] = "WNHiP"
        person['rent'] = [] # to nie może być nadpisane!
        
#),(" Nr. indeksu: ", 'indx'),(" Rok:", 'year'
        #pprint.pprint( person )
##        for key in ['imie', 'nazwisko']:
##            for c in person[key]:
##                i = ord(c)
##                if i > 122 or i < 65 or (i >90 and i <97):
##                    #if i not in [45, 157, 158, 229, 237]:
##                    print c, i, person[key], convert_line(person[key])
##        r = person['imie'] + " " + person['nazwisko']
##        add = False
##        #add = True
##        for c in r:
##            i = ord(c)
##            if i > 122 or i < 65 or (i >90 and i <97):
##                if i not in [32, 45, 229, 188, 0x9e, 0xd7, 0xe6, 0xc5, 0x8e, 0x9d, 0x9c]:
##                    add = True
##                    print c, i
##                    break
##        if add:         
##            print [r]
##            print [convert_line(r)]
        if not person['indx'] in records.keys():
            records[person['indx']] = person
    #pprint.pprint[records]  
    return records
        
        
        


def convert_line(line):
    convert_list = [
            ('\xe5', chr(179)), # ł
            ('\x9c', chr(140)), # Ś
            ('\xbc', chr(241)), # ń
            ('\x9e', chr(191)), # ż
            ('\xd7', chr(156)), # ś
            ('\xe6', chr(185)), # ą
            ('\x8e', chr(159)), # ź
            ('\xc5', chr(234)), # ę
            ('\x9d', chr(163)), # Ł
            ('\xed', chr(175)), # Ż
            ('\x8f', chr(230)), # ć            
        ]
        # dobre: _ - ó
    for ch in convert_list:
        line = line.replace(ch[0], ch[1])

    return line




#read_csv("nazwiska.csv")




