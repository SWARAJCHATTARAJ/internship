import pandas as pd
import os
import glob
from typing import Iterator, Dict, Any
import uuid

class DataLoader:
    def __init__(self, target_path: str):
        """
        Accepts either a single file or a directory.
        If a directory is provided, it recursively scans for .csv and .xlsx files.
        """
        self.target_path = target_path
        self.files = []
        
        if os.path.isfile(self.target_path):
            self.files.append(self.target_path)
        elif os.path.isdir(self.target_path):
            # Recursively find all CSV and XLSX files
            for root, dirs, files in os.walk(self.target_path):
                for file in files:
                    if file.endswith('.csv') or file.endswith('.xlsx'):
                        self.files.append(os.path.join(root, file))
                        
    def _extract_text_from_row(self, row: pd.Series) -> str:
        """
        Dynamically extracts text by finding known text columns, 
        or concatenating all string columns if no known column exists.
        """
        text_cols = ["summary", "text", "diagnosis", "report_text"]
        for col in text_cols:
            if col in row and pd.notna(row[col]) and isinstance(row[col], str):
                return str(row[col])
        
        # Fallback: concatenate all string columns
        string_vals = []
        for val in row.values:
            if isinstance(val, str) and len(val) > 2:
                string_vals.append(val)
        return " | ".join(string_vals)

    def _extract_id(self, row: pd.Series, default_id: str) -> str:
        id_cols = ["report_id", "row_id", "subject_id", "id"]
        for col in id_cols:
            if col in row and pd.notna(row[col]):
                return str(row[col])
        return default_id

    def stream_reports(self, chunk_size: int = 1000, max_records: int = None) -> Iterator[Dict[str, Any]]:
        """
        Streams reports from all discovered files in chunks to avoid blowing up memory.
        Yields dictionaries with 'document_id' and 'text'.
        """
        records_yielded = 0
        
        for file in self.files:
            if max_records and records_yielded >= max_records:
                break
                
            try:
                if file.endswith('.csv'):
                    # Chunking is native to read_csv
                    for chunk in pd.read_csv(file, chunksize=chunk_size, on_bad_lines='skip', low_memory=False):
                        for _, row in chunk.iterrows():
                            if max_records and records_yielded >= max_records:
                                return
                                
                            doc_id = self._extract_id(row, str(uuid.uuid4())[:8])
                            text = self._extract_text_from_row(row)
                            
                            if text.strip():
                                yield {"document_id": doc_id, "text": text}
                                records_yielded += 1
                                
                elif file.endswith('.xlsx'):
                    df = pd.read_excel(file)
                    total_records = len(df)
                    for start_idx in range(0, total_records, chunk_size):
                        end_idx = min(start_idx + chunk_size, total_records)
                        chunk = df.iloc[start_idx:end_idx]
                        
                        for _, row in chunk.iterrows():
                            if max_records and records_yielded >= max_records:
                                return
                                
                            doc_id = self._extract_id(row, str(uuid.uuid4())[:8])
                            text = self._extract_text_from_row(row)
                            
                            if text.strip():
                                yield {"document_id": doc_id, "text": text}
                                records_yielded += 1
            except Exception as e:
                print(f"Failed to process file {file}: {e}")
