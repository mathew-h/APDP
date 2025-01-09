# -*- coding: utf-8 -*-
from tkinter import Tk
from tkinter.filedialog import askopenfilenames
from extractors import extract_csv, extract_mdat
from data_processor import DataProcessor


class FileProcessor:
    """
    This class encompasses the file type objects containing battery data.
    """

    def __init__(self):
        """
        The constructor for the file path list
        """
        self.files = self.select_files()
        self.dp = DataProcessor()

    def __str__(self):
        return f"{[file for file in self.files]}"

    def select_files(self):
        """
        Function for getting files for processing from user input.
        """
        root = Tk()
        root.attributes("-topmost", 1)
        root.withdraw()
        root.update()

        files = list(askopenfilenames(parent=root, title="Choose files"))
        all_files = files.copy()

        root.destroy()
        self.files = all_files

        return self.files

    def process_files(self):
        """
        Loop through file objects requiring processing.
        """
        for file_path in self.files:
            self.process_file(file_path)
        return self.dp

    def process_file(self, file_path):
        """
        Depending on file type, runs logic for extracting relevant fields of data.
        """
        if file_path.endswith(".csv"):
            df = extract_csv(file_path)
            self.dp.fill_df(df)
        elif file_path.endswith(".mdat"):
            df = extract_mdat(file_path)
            self.dp.fill_df(df)
        else:
            raise ValueError("Unsupported file type")
