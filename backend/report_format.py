"""Parse a small, non-executable Markdown subset for report layout."""
import re


def report_blocks(value):
    value=str(value)
    # Older answers sometimes put an entire pipe table on one line.
    separator=re.compile(r'\|(?:\s*:?-{3,}:?\s*\|)+')
    normalized=[]
    for line in value.splitlines():
        match=separator.search(line)
        if match and line[:match.start()].strip():
            first=line.index('|')
            if line[:first].strip():normalized.append(line[:first].strip())
            normalized.append(line[first:match.start()].strip())
            normalized.append(match.group())
            normalized.extend(re.split(r'\|\s+\|',line[match.end():].strip()))
        else:normalized.append(line)
    lines=normalized
    blocks=[]
    def cells(line):return [c.strip() for c in line.strip().strip('|').split('|')]
    i=0
    while i<len(lines):
        if i+1<len(lines) and '|' in lines[i] and re.fullmatch(r'\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*',lines[i+1]):
            headers=cells(lines[i]);i+=2;values=[]
            while i<len(lines) and '|' in lines[i]:
                row=cells(lines[i])
                if len(row)!=len(headers):break
                values.append(row);i+=1
            blocks.append({'type':'table','headers':headers,'rows':values})
        else:
            if lines[i].strip():blocks.append({'type':'text','text':lines[i].strip()})
            i+=1
    return blocks
