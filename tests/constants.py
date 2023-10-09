from pathlib import Path

SIGNED_DOCUMENT_PDF = "signed_document.pdf"
ESIGN_PDF = "esign.pdf"
VOID2_PDF = "void_2.pdf"
FILE_FAKE = "file.fake"
VOID1_PDF = "void_1.pdf"
FORM_PDF = "form.pdf"
ACORD_FORM_PDF = "acord_25.pdf"
FOOTER_HTML = "footer.html"
INVOICE_HTML = "invoice.html"
GOOGLE_PDF = "google.pdf"
TEMPLATE1_DOCX = "template_1.docx"
TEMPLATE2_DOCX = "template_2.docx"
TEMPLATE3_DOCX = "template_3.docx"
TEMPLATE4_DOCX = "template_4.docx"
SIGNATURE_IMAGE = "dan_signature.png"

LIST_FILES_TO_UPLOAD = (
    TEMPLATE1_DOCX,
    TEMPLATE2_DOCX,
    TEMPLATE3_DOCX,
    TEMPLATE4_DOCX,
    GOOGLE_PDF,
    INVOICE_HTML,
    FOOTER_HTML,
    FORM_PDF,
    ACORD_FORM_PDF,
    FILE_FAKE,
    VOID1_PDF,
    VOID2_PDF,
    ESIGN_PDF,
    SIGNED_DOCUMENT_PDF,
)

DATA_CONTAINER_PATH = Path("./minio/data")
