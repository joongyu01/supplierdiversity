import unittest
from scripts.watch_policy_changes import SOURCES, classify, parse_listing, safe


class PolicyChangesTests(unittest.TestCase):
    def test_hearing_and_quarterly_snapshot_are_not_final_cancellations(self):
        self.assertEqual(classify('여성기업 확인 취소 청문 사전통지'), (['women'], 'prior_notice'))
        self.assertEqual(classify('장애인기업 확인 취소 공고'), (['disabled'], 'cancellation_notice'))
        self.assertEqual(classify('여성기업 확인서 반납 공고'), (['women'], 'surrender_notice'))
        self.assertEqual(classify('장애인표준사업장 분기 현황', '취소사업장.xlsx'), (['standard'], 'status_update'))
        self.assertIsNone(classify('장애인표준사업장 판로 지원 공고'))

    def test_layout_failure_is_not_an_empty_success(self):
        with self.assertRaises(ValueError):
            parse_listing('<html>오류</html>', SOURCES[0])

    def test_mss_identity_date_and_prior_notice(self):
        html = '''<table><tbody><tr onclick="doBbsFView('146','12345','')">
          <td><a href="#view">여성기업 확인 취소 청문 공고</a></td><td>2026.09.18</td>
          </tr></tbody></table>'''
        notices = parse_listing(html, SOURCES[0])
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]['publishedAt'], '2026-09-18')
        self.assertEqual(notices[0]['kind'], 'prior_notice')
        self.assertIn('bcIdx=12345', notices[0]['url'])
        self.assertEqual(parse_listing(html.replace('2026.09.18', '2025.09.18'), SOURCES[0]), [])

    def test_untrusted_urls_are_rejected(self):
        for url in ['http://www.mss.go.kr/a', 'https://www.mss.go.kr.example.com/a', 'https://user@www.mss.go.kr/a']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                safe(url)
