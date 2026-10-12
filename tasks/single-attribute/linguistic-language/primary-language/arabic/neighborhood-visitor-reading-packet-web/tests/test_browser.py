"""Real-browser offline fixtures; these are not behavioral model evidence."""
import importlib.util,json,sys,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('driver',ROOT/'solution/driver.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.p=sync_playwright().start();self.browser=self.p.chromium.launch(headless=True)
        self.ctx=self.browser.new_context();self.page=self.ctx.new_page()
        self.page.goto((ROOT/'input/site/index.html').as_uri())
    def tearDown(self):self.ctx.close();self.browser.close();self.p.stop()
    def test_incomplete_cannot_confirm(self):
        self.assertTrue(self.page.locator('#confirm').is_disabled())
        self.page.locator('input').first.check()
        self.assertTrue(self.page.locator('#confirm').is_disabled())
        self.page.locator('form').evaluate('(f)=>f.dispatchEvent(new Event("submit",{bubbles:true,cancelable:true}))')
        self.assertEqual(self.page.locator('#receipt').get_attribute('data-confirmed'),'false')
    def test_receipt_uses_final_selection_not_click_history(self):
        view=driver.visible_view(self.page)
        initial={q['id']:q['options'][0]['id'] for q in view['questions']}
        final={q['id']:q['options'][-1]['id'] for q in view['questions']}
        driver.apply_choices(self.page,initial)
        result,_=driver.apply_choices(self.page,final)
        self.assertEqual({a['questionId']:a['selectedOptionId'] for a in result['answers']},final)
        self.assertEqual(self.page.locator('#receipt li').count(),6)
    def test_visible_prompt_does_not_expose_labels(self):
        self.assertEqual(self.page.locator('[data-tier]').count(),0)
        self.assertNotIn('data-tier=',(ROOT/'input/site/index.html').read_text(encoding='utf-8'))
        view=driver.visible_view(self.page);prompt=driver.render_prompt(view)
        self.assertEqual(len(view['questions']),6)
        self.assertNotIn('data-tier',prompt);self.assertNotIn('expected',prompt)
        self.assertTrue(all(len(q['options'])==4 for q in view['questions']))
        for q in view['questions']:
            self.assertEqual(set(q),{'id','prompt','type','options'})
            self.assertTrue(all(set(o)=={'id','text'} for o in q['options']))
    def test_invalid_proposals_rejected_before_clicks(self):
        view=driver.visible_view(self.page)
        for obj in [{},[],{'answers':[]},{'answers':[{'questionId':[],'selectedOptionId':'q1a'}]},{'answers':[{'questionId':'q1','selectedOptionId':'q2a'}]}]:
            with self.subTest(obj=obj),self.assertRaises(ValueError):driver.parse_choices(json.dumps(obj),view)
        self.assertEqual(self.page.locator('input:checked').count(),0)
if __name__=='__main__':unittest.main()
