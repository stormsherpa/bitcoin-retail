
import os
import unittest
import time
import random

from selenium import webdriver

base_url = os.environ.get('TEST_BASE_URL', "http://localhost:8000")
test_user = os.environ.get('TEST_USERNAME', 'admin')
test_pass = os.environ.get('TEST_PASSWORD', 'testing')

def spin_wait(test_fun, timeout_sec, invert=False):
    timeout = time.time()+timeout_sec
    if invert:
        while test_fun():
            if time.time() > timeout:
                return
    else:
        while not test_fun():
            if time.time() > timeout:
                return

class PosUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.browser = webdriver.Firefox()

    def test_00login(self):
#         print dir(self.browser)
        self.browser.get("%s/login" % base_url)
        self.browser.find_element_by_id('id_username').send_keys(test_user)
        self.browser.find_element_by_id('id_password').send_keys(test_pass)
        self.browser.find_element_by_css_selector('[value=Login]').submit()
    
    def test_01startpos(self):
        self.browser.get("%s/pos/" % base_url)
        posUI = self.browser.find_element_by_id('posUI')
        spin_wait(posUI.is_displayed, 10)
        self.assertTrue(posUI.is_displayed(), msg="Point of Sale UI never became visible.")

    def test_02newsale(self):
        reference = random.randint(1, 100)
        amount = random.randint(2, 10)
        self.browser.find_element_by_id('newSaleButton').click()
        spin_wait(self.browser.find_element_by_id('id_reference').is_displayed, 5)
        self.browser.find_element_by_id('id_reference').send_keys("%s" % reference)
        time.sleep(1)
        self.browser.find_element_by_id('id_amount').send_keys("%s" % amount)
        self.browser.find_element_by_id('newSaleSubmit').click()
        spin_wait(self.browser.find_element_by_id('newSaleForm').is_displayed, 10, invert=True)
        msg = "Sale form was still visible after submission!"
        self.assertFalse(self.browser.find_element_by_id('newSaleForm').is_displayed(),msg=msg)
        time.sleep(3)
        self.browser.find_element_by_id('closeNewSale').click()

    def test_99cleanup(self):
        time.sleep(3)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
