import gspread
from google.oauth2.service_account import Credentials
from core.config import settings
from typing import Protocol
from gspread.utils import ValueInputOption


class SheetServiceInputClass(Protocol):
    def to_sheet_row(self) -> list[str | int | float]: ...


class SheetService:
    def __init__(self, credentials_path: str, sheet_name: str):
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]

        creds = Credentials.from_service_account_file(
            filename=credentials_path, scopes=scope
        )
        self.client = gspread.authorize(creds)
        self.sheet = self.get_sheet(sheet_name)

    def get_sheet(self, sheet_name: str) -> gspread.Worksheet:
        try:
            return self.client.open(sheet_name).sheet1
        except gspread.SpreadsheetNotFound:
            raise ValueError(f"Spreadsheet '{sheet_name}' not found.")

    def append_row(self, row: SheetServiceInputClass):
        row_data = row.to_sheet_row()
        print(row_data)
        return self.sheet.append_row(
            row_data, value_input_option=ValueInputOption.user_entered
        )


expense_sheet = SheetService(
    credentials_path=settings.EXPENSE_SHEETS_CREDENTIALS_PATH,
    sheet_name=settings.EXPENSE_SHEET_NAME,
)
