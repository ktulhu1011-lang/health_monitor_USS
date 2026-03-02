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
    def test_parse_rows_with_bom_header_and_cyrillic_studio(self, mock_get):
        csv_text = (
            '\ufeffОтметка времени,Электронная почта,Название УСС,Отчетный период,Операционные расходы за период (руб)\n'
            '27.02.2026 10:00:00,test@example.com,УСС-НовГУ,Февраль 2026,12345\n'
        )
        mock_get.return_value = DummyResponse(csv_text)

        result = parse_sheet_rows()

        self.assertEqual(result['issues'], [])
        self.assertTrue(result['rows'])
        first = result['rows'][0]
        self.assertEqual(first['studio_name'], 'УСС-НовГУ')
        self.assertEqual(first['studio_code'], 'USS_NOVGU')
        self.assertEqual(first['period_code'], '2026-02')


if __name__ == '__main__':
    unittest.main()
