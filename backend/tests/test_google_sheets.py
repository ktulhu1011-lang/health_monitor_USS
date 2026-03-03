import unittest
from unittest.mock import patch

from app.services.google_sheets import derive_studio_code, parse_sheet_rows


class DummyResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class GoogleSheetsParsingTests(unittest.TestCase):
    def test_derive_studio_code_cyrillic(self):
        self.assertEqual(derive_studio_code('УСС-НовГУ'), 'USS_NOVGU')

    @patch('app.services.google_sheets.requests.get')
    def test_parse_rows_with_cyrillic_studio_and_dot_period_no_missing_studio(self, mock_get):
        csv_text = (
            '\ufeffОтметка времени,Электронная почта,Название УСС,Отчетный период,Операционные расходы за период (руб)\n'
            '27.02.2026 10:00:00,test@example.com,УСС-НовГУ,2026.02,12345\n'
        )
        mock_get.return_value = DummyResponse(csv_text)

        result = parse_sheet_rows()
        issue_codes = {issue['issue_code'] for issue in result['issues']}

        self.assertNotIn('missing_studio', issue_codes)
        self.assertNotIn('invalid_period', issue_codes)
        self.assertTrue(result['rows'])

        first = result['rows'][0]
        self.assertEqual(first['studio_name'], 'УСС-НовГУ')
        self.assertEqual(first['studio_code'], 'USS_NOVGU')
        self.assertEqual(first['period_code'], '2026-02')

    @patch('app.services.google_sheets.requests.get')
    def test_parse_rows_with_month_dot_year_period(self, mock_get):
        csv_text = (
            'Timestamp,Email Address,Название УСС,Отчетный период,Операционные расходы за период (руб)\n'
            '2026-03-01T10:00:00Z,test@example.com,УСС-НовГУ,2.2026,100\n'
        )
        mock_get.return_value = DummyResponse(csv_text)
        result = parse_sheet_rows()
        self.assertTrue(result['rows'])
        self.assertEqual(result['rows'][0]['period_code'], '2026-02')


if __name__ == '__main__':
    unittest.main()
