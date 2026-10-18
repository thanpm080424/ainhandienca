"""Xuất báo cáo PDF giám sát bể cá từ telemetry_logs.

Tác giả đồ án: Lê Quốc Trí (DH52201621) và Phạm Minh Thân (DH52201428).
"""

from __future__ import annotations

import argparse
import io
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import history_logger

AUTHORS = "Lê Quốc Trí (DH52201621) và Phạm Minh Thân (DH52201428)"
TITLE = "BÁO CÁO GIÁM SÁT MÔI TRƯỜNG THỦY SINH & NHẬN DIỆN CÁ CẢNH"


def _find_fonts() -> tuple[Path, Path]:
    """Tìm TrueType font có đủ glyph tiếng Việt trên Windows, Linux hoặc macOS."""
    font_pairs = [
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
        (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
        (Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"), Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf")),
        (Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"), Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf")),
        (Path("/System/Library/Fonts/Supplemental/Arial.ttf"), Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")),
    ]
    for regular, bold in font_pairs:
        if regular.is_file() and bold.is_file():
            return regular, bold
    # Một vài bản Linux chỉ cài DejaVu ở vị trí local hoặc NotoSansCJK.
    for root in (Path("/usr/share/fonts"), Path.home() / ".fonts"):
        if root.is_dir():
            regular_matches = list(root.rglob("DejaVuSans.ttf"))
            bold_matches = list(root.rglob("DejaVuSans-Bold.ttf"))
            if regular_matches and bold_matches:
                return regular_matches[0], bold_matches[0]
    raise FileNotFoundError(
        "Không tìm thấy font TrueType hỗ trợ tiếng Việt. Cài DejaVu Sans (Linux) "
        "hoặc dùng máy có Arial (Windows), rồi chạy lại báo cáo."
    )


def _register_fonts() -> tuple[str, str]:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    regular_path, bold_path = _find_fonts()
    regular_name, bold_name = "FishReportSans", "FishReportSans-Bold"
    if regular_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(regular_name, str(regular_path)))
    if bold_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(bold_name, str(bold_path)))
    return regular_name, bold_name


def _text(value: Any, fallback: str = "-", max_chars: int = 120) -> str:
    rendered = str(value if value is not None and value != "" else fallback)
    if len(rendered) > max_chars:
        rendered = rendered[:max_chars - 1] + "…"
    return escape(rendered).replace("\n", "<br/>")


if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def build_pdf(days: int = 7) -> bytes:
    """Dựng PDF trong bộ nhớ để CLI lưu file và Flask trả trực tiếp cho client."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    stats = history_logger.get_statistics(days)
    regular_font, bold_font = _register_fonts()
    output = io.BytesIO()
    generated = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M %Z")
    page_width, page_height = A4
    navy = colors.HexColor("#12304A")
    teal = colors.HexColor("#147D82")
    pale = colors.HexColor("#EAF4F5")
    muted = colors.HexColor("#526474")
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("VietnameseTitle", parent=styles["Title"], fontName=bold_font,
                                 fontSize=15, leading=20, textColor=navy, alignment=TA_CENTER, spaceAfter=8)
    subtitle_style = ParagraphStyle("VietnameseSubtitle", parent=styles["Normal"], fontName=regular_font,
                                    fontSize=8.5, leading=12, textColor=muted, alignment=TA_CENTER)
    heading_style = ParagraphStyle("VietnameseHeading", parent=styles["Heading2"], fontName=bold_font,
                                   fontSize=11, leading=14, textColor=navy, spaceBefore=8, spaceAfter=5)
    body_style = ParagraphStyle("VietnameseBody", parent=styles["BodyText"], fontName=regular_font,
                                fontSize=8.5, leading=12, textColor=navy)
    cell_style = ParagraphStyle("VietnameseCell", parent=body_style, fontSize=7.1, leading=9)
    header_style = ParagraphStyle("VietnameseHeader", parent=cell_style, fontName=bold_font,
                                  textColor=colors.white, alignment=TA_LEFT)

    def paragraph(value: Any, style: ParagraphStyle = cell_style, fallback: str = "-") -> Paragraph:
        return Paragraph(_text(value, fallback), style)

    def page_decor(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setStrokeColor(teal)
        canvas.setLineWidth(1.2)
        canvas.line(17 * mm, page_height - 14 * mm, page_width - 17 * mm, page_height - 14 * mm)
        canvas.setFont(regular_font, 7)
        canvas.setFillColor(muted)
        canvas.drawString(17 * mm, 10 * mm, "Hệ thống AI nhận diện cá cảnh và giám sát IoT")
        canvas.drawRightString(page_width - 17 * mm, 10 * mm, f"Trang {document.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=17 * mm, leftMargin=17 * mm,
                                 topMargin=20 * mm, bottomMargin=17 * mm,
                                 title=TITLE, author=AUTHORS, subject=f"Báo cáo {days} ngày")
    story: list[Any] = [Spacer(1, 5 * mm), Paragraph(escape(TITLE), title_style),
                        Paragraph(f"Tác giả: {escape(AUTHORS)}", subtitle_style),
                        Paragraph(f"Thời gian lập: {escape(generated)} | Kỳ thống kê: {days} ngày gần nhất", subtitle_style),
                        Spacer(1, 7 * mm)]

    totals = stats["totals"]
    kpi_data = [
        [paragraph("Số lượt nhận diện", header_style), paragraph("Lượt có cảnh báo", header_style),
         paragraph("Cảnh báo lai tạp", header_style), paragraph("Nhiệt độ TB", header_style), paragraph("pH TB", header_style)],
        [paragraph(totals["detections"]), paragraph(totals["alerts"]), paragraph(totals["hybrid_detections"]),
         paragraph(f'{totals["avg_temperature"]} °C' if totals["avg_temperature"] is not None else "N/A"),
         paragraph(totals["avg_ph"] if totals["avg_ph"] is not None else "N/A")],
    ]
    kpi_table = Table(kpi_data, colWidths=[34 * mm, 33 * mm, 33 * mm, 33 * mm, 33 * mm], repeatRows=1)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), navy), ("BACKGROUND", (0, 1), (-1, -1), pale),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.white), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 1), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Paragraph("1. Thống kê số lượt nhận diện theo loài", heading_style))
    species_rows = [[paragraph("Mã loài", header_style), paragraph("Tên hiển thị", header_style),
                     paragraph("Số lượt", header_style)]]
    for item in stats["species_counts"]:
        species_rows.append([paragraph(item["species_key"]), paragraph(item["species_name"]),
                             paragraph(item["detections"])])
    if len(species_rows) == 1:
        species_rows.append([paragraph("Chưa có dữ liệu"), paragraph(""), paragraph(0)])
    species_table = Table(species_rows, colWidths=[47 * mm, 91 * mm, 28 * mm], repeatRows=1, hAlign="LEFT")
    species_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), teal), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, pale]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C8D7DE")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (2, -1), "CENTER"), ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(species_table)

    story.append(Paragraph("2. Số liệu môi trường theo ngày", heading_style))
    daily_rows = [[paragraph("Ngày", header_style), paragraph("Lượt", header_style),
                   paragraph("Nhiệt độ TB (°C)", header_style), paragraph("pH TB", header_style),
                   paragraph("Cảnh báo", header_style)]]
    for item in stats["daily"]:
        daily_rows.append([paragraph(item["day"]), paragraph(item["detections"]),
                           paragraph(round(item["avg_temperature"], 2) if item["avg_temperature"] is not None else "N/A"),
                           paragraph(round(item["avg_ph"], 2) if item["avg_ph"] is not None else "N/A"),
                           paragraph(item["alerts"])])
    if len(daily_rows) == 1:
        daily_rows.append([paragraph("Chưa có dữ liệu"), paragraph(0), paragraph("N/A"), paragraph("N/A"), paragraph(0)])
    daily_table = Table(daily_rows, colWidths=[37 * mm, 22 * mm, 47 * mm, 33 * mm, 27 * mm], repeatRows=1)
    daily_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), teal), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, pale]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C8D7DE")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(daily_table)

    story.append(Paragraph("3. Nhật ký vượt ngưỡng và cảnh báo lai tạp", heading_style))
    alert_rows = [[paragraph("Thời điểm", header_style), paragraph("Thiết bị / loài", header_style),
                   paragraph("Nhiệt độ", header_style), paragraph("pH", header_style),
                   paragraph("Loại cảnh báo", header_style)]]
    for item in stats["alerts"]:
        species_label = f'{item.get("device_id", "-")} / {item.get("species_name") or item.get("species_key") or "Không rõ"}'
        alert_label = item.get("alert_status") or "-"
        if item.get("is_hybrid") and alert_label != "HYBRID_ALERT":
            alert_label += " + HYBRID_ALERT"
        alert_rows.append([paragraph(item.get("timestamp")), paragraph(species_label),
                           paragraph(f'{item["temp_measured"]} °C' if item.get("temp_measured") is not None else "-"),
                           paragraph(item.get("ph_measured") if item.get("ph_measured") is not None else "-"),
                           paragraph(alert_label)])
    if len(alert_rows) == 1:
        alert_rows.append([paragraph("Không có cảnh báo trong kỳ"), paragraph(""), paragraph(""), paragraph(""), paragraph("")])
    alerts_table = Table(alert_rows, colWidths=[32 * mm, 60 * mm, 26 * mm, 20 * mm, 32 * mm], repeatRows=1)
    alerts_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), navy), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, pale]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C8D7DE")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(alerts_table)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Ghi chú: trạng thái mỗi lần lấy mẫu ưu tiên TEMP_WARNING, sau đó PH_WARNING, "
        "rồi HYBRID_ALERT. Ngưỡng môi trường phụ thuộc loài được hệ thống nhận diện.", body_style
    ))
    document.build(story, onFirstPage=page_decor, onLaterPages=page_decor)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description="Xuất báo cáo PDF lịch sử IoT cho phụ lục đồ án.")
    parser.add_argument("--days", type=int, default=7, help="Số ngày thống kê (mặc định: 7; dùng 30 cho tháng gần nhất).")
    parser.add_argument("--output", default=None, help="Đường dẫn file PDF đầu ra; mặc định aquarium_report_<ngày>.pdf.")
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days phải lớn hơn 0")
    output_path = Path(args.output or f"aquarium_report_{datetime.now():%Y%m%d_%H%M%S}.pdf").expanduser().resolve()
    try:
        pdf_bytes = build_pdf(args.days)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pdf_bytes)
    except Exception as exc:
        print(f"Không xuất được báo cáo PDF: {exc}", file=sys.stderr)
        return 1
    print(f"Đã tạo báo cáo PDF ({len(pdf_bytes):,} byte): {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
