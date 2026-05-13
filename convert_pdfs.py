import fitz
import os

pdf_dir = os.path.join(os.path.dirname(__file__), "frontend", "figmasample")
out_dir = os.path.join(pdf_dir, "images")
os.makedirs(out_dir, exist_ok=True)

for fname in os.listdir(pdf_dir):
    if fname.endswith(".pdf"):
        doc = fitz.open(os.path.join(pdf_dir, fname))
        for i, page in enumerate(doc):
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            out_name = fname.replace(".pdf", f"_p{i+1}.png")
            pix.save(os.path.join(out_dir, out_name))
        doc.close()
        print(f"Done: {fname}")
print("All done")
