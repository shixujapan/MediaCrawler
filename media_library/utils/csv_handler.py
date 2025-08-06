import csv
import os

class CSVHandler:
    """Handles CSV file operations."""

    @staticmethod
    def get_existing_indexes_and_headers(csv_file_path):
        """Reads an existing CSV file and returns the set of existing unique_video_id values and header mapping."""
        existing_indexes = set()
        header_mapping = {}

        if os.path.exists(csv_file_path):
            with open(csv_file_path, "r", encoding="utf-8-sig") as file:
                reader = csv.reader(file)
                headers = next(reader, [])
                if headers:
                    header_mapping = {col: idx for idx, col in enumerate(headers)}
                    for row in reader:
                        if row:
                            existing_indexes.add(row[header_mapping["unique_video_id"]])  # Ensure we use `unique_video_id`

        return existing_indexes, header_mapping

    @staticmethod
    def write_to_csv(csv_file_path, header_mapping, rows):
        """Writes rows to a CSV file inside the `data/` directory."""
        
        # Check if file is empty or missing
        file_is_empty = not os.path.exists(csv_file_path) or os.stat(csv_file_path).st_size == 0

        with open(csv_file_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if file_is_empty:  # Write headers only if file is empty
                writer.writerow([col for col in header_mapping])
            writer.writerows(rows)
