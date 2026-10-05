"""Catalogue/visible DOM agreement; no API calls."""
from html.parser import HTMLParser
from pathlib import Path
import unittest
import yaml

ROOT=Path(__file__).resolve().parents[1]

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[];self.option=None;self.legend=False
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='fieldset':self.rows.append({'id':attrs['data-question'],'prompt':'','options':[],'type':'single_choice'})
        if tag=='legend':self.legend=True
        if tag=='label':
            self.option={'id':attrs['data-id'],'text':''};self.rows[-1]['options'].append(self.option)
    def handle_data(self,text):
        if self.legend:self.rows[-1]['prompt']+=text
        if self.option is not None:self.option['text']+=text
    def handle_endtag(self,tag):
        if tag=='legend':self.legend=False
        if tag=='label':self.option=None

class SurfaceTests(unittest.TestCase):
    def test_catalogue_matches_actual_dom_including_order(self):
        parser=Page();parser.feed((ROOT/'input/site/index.html').read_text(encoding='utf-8'))
        self.assertEqual(parser.rows,yaml.safe_load((ROOT/'tests/catalogue.yaml').read_text(encoding='utf-8'))['questions'])

if __name__=='__main__':unittest.main()
