import os
import sys

from pdfminer.high_level import extract_text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from config import PDF_DIRECTORY, MARKDOWN_DIRECTORY


def convert_to_markdown(text):
    lines = text.split("\\\\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.isupper() and len(stripped) < 50:
            lines[i] = f"## {stripped}"
    return "\\\\n".join(lines)

def process_inputs_in_directory():
    for filename in os.listdir(PDF_DIRECTORY):
        if filename.endswith(".pdf"):
            markdown_filename = filename.replace(".pdf", "_markdown.md")
            markdown_path = os.path.join(MARKDOWN_DIRECTORY, markdown_filename)
            
            # Check if the markdown file already exists
            if os.path.exists(markdown_path):
                print(f"Markdown for {filename} already exists. Skipping...")
                continue
            
            pdf_path = os.path.join(PDF_DIRECTORY, filename)
            
            # Extract text from PDF
            extracted_text = extract_text(pdf_path)
            
            # Convert extracted text to markdown
            markdown_text = convert_to_markdown(extracted_text)
            
            # Save the markdown text
            with open(markdown_path, "w") as md_file:
                md_file.write(markdown_text)
            print(f"Processed {filename} and saved Markdown to {markdown_filename}")


if __name__ == "__main__":
    process_inputs_in_directory()