import os
import glob
from pdf2image import convert_from_path
import pytesseract
#my directory during my data analytics internship
pdfdirectory = "/home/llmadmin/bevan_llm/pdfs_to_convert"
outputdirectory = "/home/llmadmin/bevan_llm/ocr_text"
os.makedirs(outputdirectory, exist_ok=True)

files = glob.glob(os.path.join(pdfdirectory, "*.pdf"))
print("Found ", len(files), " PDF(s) to process.\n")
processed = 0
skipped = 0
failed = 0

for pdfpath in files:
    name = os.path.splitext(os.path.basename(pdfpath))[0]
    txtname = name + ".txt"
    textpath = os.path.join(outputdirectory, txtname)
    if os.path.exists(textpath):
        print("Skipping ", name, " (already processed)")
        skipped += 1
        continue
    print("Processing: ", pdfpath, " → ", textpath)
    try:
        images = convert_from_path(pdfpath, dpi=300)
    except Exception as e:
        print("  ERROR converting ", pdfpath, ": ", e)
        failed += 1
        continue

    alltext = []
    for i, image in enumerate(images):
        print("  OCR page ", i+1, "/", len(images), "...")
        text = pytesseract.image_to_string(image, lang='eng')
        alltext.append("--- Page " + str(i+1) + " ---\n" + text)

    fulltext = "\n".join(alltext)

    with open(textpath, "w", encoding="utf-8") as txtfile:
        txtfile.write(fulltext)

    print("Saved to ", textpath)
    processed += 1
print("=" * 40)
print("Summary:")
print("  Processed : ", processed)
print("  Skipped   : ", skipped, " (already existed)")
print("  Failed    : ", failed)
print("  Total     : ", len(files))
print("=" * 40)
