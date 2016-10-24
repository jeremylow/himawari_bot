# encoding: utf-8
import datetime
import unittest

import himawari_lowres as hl


class LowResTests(unittest.TestCase):
    def test_time_rounding(self):
        dt = datetime.datetime(2016, 10, 23, 8, 29, 30)
        rounded_dt = hl.round_time_10(dt)
        expected_dt = datetime.datetime(2016, 10, 23, 8, 10)
        self.assertEqual(rounded_dt, expected_dt)

    def test_date_to_filename(self):
        dt = datetime.datetime(2016, 10, 23, 8, 10)
        fn = hl.date_to_jma_filename(dt)
        expected_fn = "2016/10/23/081000_0_0.png"
        self.assertEqual(fn, expected_fn)

    def test_get_jma_images(self):
        dt = datetime.datetime(2016, 10, 23, 8, 29, 30)
        images = hl.get_jma_images(start_time=dt)
        self.assertTrue(isinstance(images, list))
        self.assertEqual(images[0], "2016/10/23/081000_0_0.png")
        self.assertEqual(images[1], "2016/10/23/080000_0_0.png")
