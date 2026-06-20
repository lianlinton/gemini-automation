from pathlib import Path
from pypdf import PdfReader, PdfWriter

# Input PDF
input_pdf = Path("original.pdf")

# Output folder
output_folder = Path("chunks")
output_folder.mkdir(exist_ok=True)

# Chunk size
CHUNK_SIZE = 10

reader = PdfReader(str(input_pdf))
total_pages = len(reader.pages)

print(f"Total pages: {total_pages}")

chunk_num = 1

for start_page in range(0, total_pages, CHUNK_SIZE):

    end_page = min(start_page + CHUNK_SIZE, total_pages)

    writer = PdfWriter()

    for page_num in range(start_page, end_page):
        writer.add_page(reader.pages[page_num])

    output_filename = (
        f"chunk_{chunk_num:03d}"
        f"_pages_{start_page+1}-{end_page}.pdf"
    )

    output_path = output_folder / output_filename

    with open(output_path, "wb") as output_file:
        writer.write(output_file)

    print(f"Created: {output_filename}")

    chunk_num += 1