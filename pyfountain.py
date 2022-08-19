"""PyFountain by Troy Fullwood

based on the Fountain FastFountainDoc at:
github.com/nyousefi/Fountain/blob/master/Fountain/FastFountainDoc.m
"""
import re
import logging
from dataclasses import dataclass

INLINE_PATTERN = "^([^\\t\\s][^:]+):\\s*([^\\t\\s].*$)"
DIRECTIVE_PATTERN = "^([^\\t\\s][^:]+):([\\t\\s]*$)"
CONTENT_PATTERN = ''


def range_replace(source: str, start: int, end: int, new: str) -> str:
    """Replace all text in the given range of the source string with the new
    string, returning the modified string.

    >>> range_replace('foobarfoo', 3, 3+3, 'foo')
    'foofoofoo'
    """
    return source[:start] + new + source[end:]


@dataclass
class FountainElem:
    """A single element in a parsed Fountain document."""
    type: str
    text: str
    centered: bool = False
    scene_num: str | None = None
    is_dual_dialog: bool = False
    section_depth: int = 0


@dataclass
class FountainDoc:
    """Parser for the Fountain screenplay format."""
    elements: list[FountainElem]
    title_page: list[dict[str, list[str]]]

    def __init__(self, source: str) -> None:
        self.elements: list[FountainElem] = []
        self.title_page: list[dict[str, list[str]]] = []

        self._parse_contents(source)

    def _parse_contents(self, contents: str):
        """Parse the fountain source text."""
        contents = contents.lstrip() + '\n\n'

        firstblank: int = contents.index('\n\n')
        top = contents[:firstblank]

        self._title(top)
        self._body('\n' + contents[firstblank:])

    def _body(self, contents: str):
        """Parse the function body."""
        lines = contents.splitlines()
        nl_before: int = 0
        index: int = -1
        comment_block: bool = False
        indialog: bool = False
        comment_text: str = ''

        for line in lines:
            index += 1

            if len(line) > 0 and line[0] == '~':
                if self.elements:
                    lastelem = self.elements[-1]
                else:
                    lastelem = None
                if lastelem is None:
                    element = FountainElem('Lyrics', line)
                    self.elements.append(element)
                    nl_before = 0
                    continue
                if lastelem.type == 'Lyrics' and nl_before > 0:
                    self.elements.append(FountainElem('Lyrics', ' '))
                self.elements.append(FountainElem('Lyrics', line))
                nl_before = 0
                continue

            if len(line) > 0 and line[0] == '!':
                self.elements.append(FountainElem('Action', line))
                nl_before = 0
                continue

            if len(line) > 0 and line[0] == '@':
                self.elements.append(FountainElem('Character', line))
                nl_before = 0
                indialog = True
                continue

            if re.match(r'^\s{2}$', line):
                if indialog:
                    nl_before = 0
                    prevelem = self.elements[-1]
                    if prevelem.type == 'Dialogue':
                        prevelem.text = f'{prevelem.text}\n{line}'
                    else:
                        self.elements.append(FountainElem('Dialogue', line))
                    continue
                else:
                    self.elements.append('Action', line)
                    nl_before = 0
                    continue

            if line == '' and not comment_block:
                indialog = False
                nl_before += 1
                continue

            if line.startswith('/*'):
                if re.match(r'\*\/\s*$', line):
                    text = line.replace('/*', '').replace('*/', '')
                    comment_block = False
                    self.elements.append(FountainElem('Boneyard', text))
                    nl_before = 0
                else:
                    comment_block = True
                    comment_text += '\n'
                continue
            if re.match(r'\*\/\s*$', line):
                text = line.replace('*/', '')
                if (not text) or re.match(text, r'^\s*$'):
                    comment_text += text.strip()
                comment_block = False
                self.elements.append(FountainElem('Boneyard', comment_text))
                comment_text = ''
                nl_before = 0
                continue

            if comment_block:
                comment_text += 'line' + '\n'
                continue

            if re.match(r'^={3,}\s*$', line):
                self.elements.append(FountainElem('Page Break', line))
                nl_before = 0
                continue

            if len(line.strip()) > 0 and line.strip()[0] == '=':
                match = re.match(r'^\s*={1}', line)
                assert match is not None
                markup = match.span(0)
                text = range_replace(line, markup[0], markup[1], '')
                self.elements.append(FountainElem('Synopsis', text))
                continue

            if nl_before > 0 and (
                    match := re.match(r'^\s*\[{2}\s*([^\]\n])+\s*\]{2}\s*$',
                                      line)):
                text = line.replace('[[', '').replace(']]', '').strip()
                self.elements.append(FountainElem('Comment', text))
                continue

            if len(line.strip()) > 0 and line.strip()[0] == '#':
                nl_before = 0
                match = re.match(r'^\s*#+', line)
                assert match is not None
                markup = match.span(0)
                depth = markup[1] - markup[0]

                text = line[markup[1]:]
                if (not text) or text == '':
                    logging.log(1, 'Error in Section Heading')
                    continue

                element = FountainElem(
                    'Section Heading', text, section_depth=depth)
                self.elements.append(element)
                continue

            if len(line) > 1 and line[0] == '.' and line[1] != '.':
                nl_before = 0
                scene_num = None
                text = ''
                if match := re.match(r'#([^\n#]*?)#\s*$', line):
                    scene_num = match[1]
                    text = text[:match.span()[0]]
                    text = text[1:match.span()[0]].strip()
                else:
                    text = line[1:].strip()
                element = FountainElem('Scene Heading', text)
                if scene_num is not None:
                    element.scene_num = scene_num
                self.elements.append(element)
                continue

            if nl_before > 0 and re.search(
                "^(INT|EXT|EST|(I|INT)\\.?\\/(E|EXT)\\.?)[\\.\\-\\s][^\\n]+$",
                line,
                re.IGNORECASE
            ):
                nl_before = 0
                scene_num = None
                text = None
                if match := re.match("#([^\\n#]*?)#\\s*$", line):
                    scene_num = match[1]
                    text = re.sub("#([^\\n#]*?)#\\s*$", '', line)
                else:
                    text = line
                element = FountainElem('Scene Heading', text)
                if scene_num is not None:
                    element.scene_num = scene_num
                self.elements.append(element)
                continue

            if re.match("[^a-z]*TO:$", line):
                nl_before = 0
                self.elements.append(FountainElem('Transition', line))
                continue

            trimline = line.lstrip()
            transitions = ('FADE OUT.', 'CUT TO BLACK.', 'FADE TO BLACK.')
            if trimline in transitions:
                nl_before = 0
                self.elements.append(FountainElem('Transition', line))
                continue

            if line[0] == '>':
                if len(line) > 1 and line[-1] == '<':
                    text = line[1:-1].strip()
                    element = FountainElem('Action', text)
                    element.centered = True
                    self.elements.append(element)
                    nl_before = 0
                    continue
                else:
                    text = text[1:].strip()
                    self.elements.append(FountainElem('Transition', text))
                    nl_before = 0
                    continue

            if nl_before > 0 and re.match("^[^a-z]+(\\(cont'd\\))?$", line):
                nextindex = index+1
                if nextindex < len(lines):
                    nextline = lines[index+1]
                    if nextline != '':
                        nl_before = 0
                        element = FountainElem('Character', line)

                        if re.match("\\^\\s*$", line):
                            element.is_dual_dialog = True
                            element.text = re.sub("\\s*\\^\\s*$", '',
                                                  element.text)
                            found_prev_char = False
                            subindex = len(self.elements) - 1
                            while subindex >= 0 and not found_prev_char:
                                prevelem = self.elements[subindex]
                                if prevelem.type == 'Character':
                                    prevelem.is_dual_dialog = True
                                    found_prev_char = True
                                subindex -= 1

                        self.elements.append(element)
                        indialog = True
                        continue

            if indialog:
                if nl_before == 0 and re.match("^\\s*\\(", line):
                    self.elements.append(FountainElem('Parenthetical', line))
                    continue
                else:
                    prevelem = self.elements[-1]
                    if prevelem.type == 'Dialogue':
                        prevelem.text = f'{prevelem.text}\n{line}'
                    else:
                        self.elements.append(FountainElem('Dialogue', line))
                    continue

            if nl_before == 0 and len(self.elements) > 0:
                prevelem = self.elements[-1]
                if prevelem.type == 'Scene Heading':
                    prevelem.type = 'Action'

                prevelem.text = f'{prevelem.text}\n{line}'
                nl_before = 0
                continue
            else:
                self.elements.append(FountainElem('Action', line))
                nl_before = 0
                continue

    def _title(self, top: str):
        """Parse the title page."""
        foundtitle: bool = False
        openkey: str = ''
        openvals: list = []
        toplines = top.splitlines()

        for line in toplines:
            if line == '' or re.match(DIRECTIVE_PATTERN, line):
                foundtitle = True
                if openkey != '':
                    self.title_page.append({openkey: openvals})
                if match := re.match(DIRECTIVE_PATTERN, line):
                    openkey = match[1].lower()
                    if openkey == 'author':
                        openkey = 'authors'
            elif match := re.match(INLINE_PATTERN, line):
                foundtitle = True
                if openkey != '':
                    self.title_page.append({openkey: openvals})
                    openkey = ''
                    openvals = []

                key = match[1].lower()
                value = match[2]
                if key == 'author':
                    key = 'authors'
                self.title_page.append({key: [value]})
                openkey = ''
                openvals = []
            elif foundtitle:
                openvals.append(line.strip())
        if foundtitle:
            if not (openkey == '' and len(openvals) == 0 and len(
                    self.title_page) == 0):
                if openkey != '':
                    self.title_page.append({openkey: openvals})
                    openkey = ''
                    openvals = []


if __name__ == "__main__":
    import doctest
    doctest.testmod()
