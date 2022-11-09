import re

if __name__ == '__main__':
    fPipfile = 'Pipfile'
    fRequirements = 'requirements.txt'
    with open(fPipfile, 'rt') as fP:
        pipfileContents = fP.read()
    rSearch = r"\[packages\]\n[a-zA-Z0-9 =._\-\"\n]*"
    sSearch: list[str] = re.findall(rSearch, pipfileContents)
    requirementsContents = sSearch[0].replace(' = "', '').replace('"\n', '\n').replace('[packages]\n', '')
    with open(fRequirements, 'wt') as fR:
        fR.write(requirementsContents)
