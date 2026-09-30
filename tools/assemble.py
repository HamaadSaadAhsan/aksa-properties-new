s=open('index.src.html').read()
m=open('data.json').read().replace('</','<\\/')
body=s.replace('/*MANIFEST*/',m)
open('artifact.html','w').write(body)
head,rest=body.split('<style>',1)
full='<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'+head+'<style>'+rest.replace('</style>\n','</style>\n</head>\n<body>\n',1)+'\n</body>\n</html>\n'
open('index.html','w').write(full)
