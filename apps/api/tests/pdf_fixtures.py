"""PDF fixtures built in code with pikepdf, so tests don't depend on binary files."""

import io

import pikepdf
from pikepdf import Array, Dictionary, Name, String


def _page(pdf: pikepdf.Pdf) -> pikepdf.Page:
    content = pdf.make_stream(b"BT /F1 12 Tf 72 720 Td (Experience) Tj ET")
    page = pdf.add_blank_page(page_size=(612, 792))
    page.obj["/Contents"] = content
    page.obj["/Resources"] = Dictionary(
        Font=Dictionary(F1=Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica))
    )
    return page


def _save(pdf: pikepdf.Pdf, **kwargs: object) -> bytes:
    out = io.BytesIO()
    pdf.save(out, **kwargs)  # type: ignore[arg-type]
    return out.getvalue()


def plain_pdf(pages: int = 1) -> bytes:
    pdf = pikepdf.new()
    for _ in range(pages):
        _page(pdf)
    return _save(pdf)


def encrypted_pdf(*, user_password: str = "secret") -> bytes:
    """Needs a password to open, or (with `user_password=""`) opens but stays encrypted."""
    pdf = pikepdf.new()
    _page(pdf)
    return _save(pdf, encryption=pikepdf.Encryption(owner="owner", user=user_password))


def hostile_pdf() -> bytes:
    """A one-page PDF with every kind of active content `sanitise_pdf` removes, plus a web link
    and an internal link that must survive."""
    pdf = pikepdf.new()
    page = _page(pdf)
    javascript = Dictionary(Type=Name.Action, S=Name.JavaScript, JS=String("app.alert(1)"))
    pdf.Root.OpenAction = pdf.make_indirect(javascript)
    pdf.Root.AA = Dictionary(WC=Dictionary(S=Name.JavaScript, JS=String("app.alert(2)")))
    embedded = pdf.make_stream(b"MZ not really an exe")
    embedded["/Type"] = Name.EmbeddedFile
    filespec = Dictionary(Type=Name.Filespec, F=String("payload.exe"), EF=Dictionary(F=embedded))
    named_script = pdf.make_indirect(Dictionary(S=Name.JavaScript, JS=String("x")))
    pdf.Root.Names = Dictionary(
        JavaScript=Dictionary(Names=Array([String("init"), named_script])),
        EmbeddedFiles=Dictionary(Names=Array([String("payload.exe"), pdf.make_indirect(filespec)])),
    )
    page.obj["/AA"] = Dictionary(O=Dictionary(S=Name.JavaScript, JS=String("app.alert(3)")))

    def link(action: Dictionary) -> Dictionary:
        return Dictionary(Type=Name.Annot, Subtype=Name.Link, Rect=[0, 0, 10, 10], A=action)

    page.obj["/Annots"] = pdf.make_indirect(
        Array(
            [
                pdf.make_indirect(link(Dictionary(S=Name.Launch, F=String("cmd.exe")))),
                pdf.make_indirect(link(Dictionary(S=Name.URI, URI=String("javascript:alert(4)")))),
                pdf.make_indirect(
                    link(
                        Dictionary(
                            S=Name.URI,
                            URI=String("https://example.com"),
                            Next=Dictionary(S=Name.JavaScript, JS=String("x")),
                        )
                    )
                ),
                pdf.make_indirect(
                    link(Dictionary(S=Name.URI, URI=String("https://linkedin.com/in/x")))
                ),
                pdf.make_indirect(link(Dictionary(S=Name.GoTo, D=Array([page.obj, Name.Fit])))),
                pdf.make_indirect(
                    Dictionary(
                        Type=Name.Annot,
                        Subtype=Name.FileAttachment,
                        Rect=[0, 0, 10, 10],
                        FS=filespec,
                    )
                ),
            ]
        )
    )
    pdf.Root.AcroForm = Dictionary(Fields=Array(), XFA=pdf.make_stream(b"<xdp/>"))
    return _save(pdf)


def _escape(text: str) -> bytes:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("latin-1")


def text_pdf(*pages: list[tuple[float, float, str]]) -> bytes:
    """A PDF with text placed at (x, y) points from the top-left of a US Letter page, one list of
    placements per page, so tests can lay out single-column, two-column or table-like résumés."""
    pdf = pikepdf.new()
    for placements in pages:
        stream = b"".join(
            b"BT /F1 10 Tf %.1f %.1f Td (%s) Tj ET\n" % (x, 792 - y, _escape(text))
            for x, y, text in placements
        )
        page = pdf.add_blank_page(page_size=(612, 792))
        page.obj["/Contents"] = pdf.make_stream(stream)
        page.obj["/Resources"] = Dictionary(
            Font=Dictionary(
                F1=Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica)
            )
        )
    return _save(pdf)
