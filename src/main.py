# -*- coding: utf-8 -*-
from file_processor import FileProcessor


def main():
    file_processor = FileProcessor()
    dp = file_processor.process_files()
    # dp.export_df()
    dp.calculations()
    ...


if __name__ == "__main__":
    main()
