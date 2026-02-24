import os
import glob
from pdf2image import convert_from_path  # converts PDF pages into images
import pytesseract  # reads text from images (OCR)
# my directory during data science internship
# pdfs were likely documents fed into an LLM (large language model) called bevan_llm
pdfdirectory = "/home/llmadmin/bevan_llm/pdfs_to_convert"
# directory where the extracted text files will be saved
outputdirectory = "/home/llmadmin/bevan_llm/ocr_text"
# create the output folder if it doesn't already exist
os.makedirs(outputdirectory, exist_ok=True)
# find all PDF files in the pdf directory (glob.glob haha)
files = glob.glob(os.path.join(pdfdirectory, "*.pdf"))
print("Found ", len(files), " PDF(s) to process.\n")

# counters to track what happened to each file
processed = 0
skipped = 0
failed = 0

for pdfpath in files:
    # get just the filename without the .pdf extension, used to name the output .txt file
    name = os.path.splitext(os.path.basename(pdfpath))[0]
    txtname = name + ".txt"
    textpath = os.path.join(outputdirectory, txtname)
                # if a .txt file already exists for this PDF, skip it to avoid repeating work
    if os.path.exists(textpath):
        print("skipping ", name, " (already processed)")
        skipped += 1
        continue

    print("processing: ", pdfpath, " → ", textpath)
    try:
                                                    # convert each page of the PDF into an image at 300 DPI for better OCR accuracy
        images = convert_from_path(pdfpath, dpi=300)
    except Exception as e:
        # if the PDF is corrupted or unreadable, log the error and move on
        print("  ERROR converting ", pdfpath, ": ", e)
        failed += 1
        continue

    alltext = []
    for i, image in enumerate(images):
        print("  OCR page ", i+1, "/", len(images), "...")
        # extract text from the image using tesseract OCR
        text = pytesseract.image_to_string(image, lang='eng')
        # label each page so you know where each page starts in the output file
        alltext.append("--- Page " + str(i+1) + " ---\n" + text)

    # join all pages into one single block of text
    fulltext = "\n".join(alltext)

    # write the extracted text to a .txt file
    with open(textpath, "w", encoding="utf-8") as txtfile:
        txtfile.write(fulltext)

    print("save to ", textpath)
    processed += 1

# print a summary of the run
print("=" * 40)
print("Summary:")
print("  process : ", processed)
print("  skip   : ", skipped, " (already existed)")
print("  fail    : ", failed)
print("  total     : ", len(files))
print("=" * 40)
