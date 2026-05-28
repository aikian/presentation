import base64
import io
import json
import re
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image as RLImage, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

_MALGUN = Path("C:/Windows/Fonts/malgun.ttf")
_MALGUN_BOLD = Path("C:/Windows/Fonts/malgunbd.ttf")
if _MALGUN.exists():
    pdfmetrics.registerFont(TTFont("KR", str(_MALGUN)))
    if _MALGUN_BOLD.exists():
        pdfmetrics.registerFont(TTFont("KR-Bold", str(_MALGUN_BOLD)))
    else:
        pdfmetrics.registerFont(TTFont("KR-Bold", str(_MALGUN)))
    pdfmetrics.registerFontFamily("KR", normal="KR", bold="KR-Bold", italic="KR", boldItalic="KR-Bold")
    fm.fontManager.addfont(str(_MALGUN))
    plt.rcParams["font.family"] = "Malgun Gothic"
    _KR = "KR"
else:
    pdfmetrics.registerFont(UnicodeCIDFont("HYGothic-Medium"))
    pdfmetrics.registerFontFamily(
        "HYGothic-Medium",
        normal="HYGothic-Medium",
        bold="HYGothic-Medium",
        italic="HYGothic-Medium",
        boldItalic="HYGothic-Medium",
    )
    _KR = "HYGothic-Medium"

_NAVY = colors.HexColor("#1e293b")
_SLATE = colors.HexColor("#64748b")
_BODY = colors.HexColor("#374151")
_INDIGO = colors.HexColor("#6366f1")
_GREEN = colors.HexColor("#22c55e")
_AMBER = colors.HexColor("#f59e0b")
_RED = colors.HexColor("#ef4444")
_BORDER = colors.HexColor("#e2e8f0")
_PANEL = colors.HexColor("#f8fafc")
_INDIGO_SOFT = colors.HexColor("#eef2ff")


def _make_chart(gaze: float, tilt: float, gestures: int) -> bytes:
    labels = (
        ["시선 이탈률 (%)", "어깨 기울기 (도)", "제스처 횟수 (회)"]
        if _KR == "KR"
        else ["Gaze away (%)", "Shoulder tilt (deg)", "Gestures"]
    )
    values = [round(gaze * 100, 1), round(tilt, 1), gestures]
    bar_colors = [
        "#ef4444" if gaze > 0.3 else "#f59e0b" if gaze > 0.15 else "#22c55e",
        "#ef4444" if tilt > 15 else "#f59e0b" if tilt > 8 else "#22c55e",
        "#f59e0b" if gestures < 5 or gestures > 50 else "#22c55e",
    ]
    fig, ax = plt.subplots(figsize=(5.5, 2.6))
    bars = ax.barh(labels, values, color=bar_colors, height=0.45)
    ax.bar_label(bars, fmt="%.1f", padding=4, fontsize=9)
    ax.set_xlim(0, max(values) * 1.35 + 1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=9)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _make_score_chart(scores: dict) -> bytes:
    labels = ["시선", "자세", "제스처", "시간"] if _KR == "KR" else ["Gaze", "Pose", "Gesture", "Time"]
    keys = ["score_gaze", "score_pose", "score_gesture", "score_time"]
    values = [scores.get(k, 0) for k in keys]
    bar_colors = ["#22c55e" if v >= 70 else "#f59e0b" if v >= 50 else "#ef4444" for v in values]

    fig, ax = plt.subplots(figsize=(5.5, 2.2))
    bars = ax.bar(labels, values, color=bar_colors, width=0.5)
    ax.bar_label(bars, fmt="%d", padding=3, fontsize=10)
    ax.set_ylim(0, 115)
    ax.set_ylabel("점수" if _KR == "KR" else "Score", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=9)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _score_color(val: int):
    if val >= 70:
        return _GREEN
    if val >= 50:
        return _AMBER
    return _RED


def _markdown_inline(text: str) -> str:
    safe = escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)


def _markdown_lines_to_flowables(lines: list[str], body_s: ParagraphStyle):
    flowables = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            flowables.append(Spacer(1, 0.08 * cm))
            continue

        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        if bullet:
            flowables.append(Paragraph(f"• {_markdown_inline(bullet.group(1))}", body_s))
            continue

        numbered = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if numbered:
            flowables.append(Paragraph(f"{numbered.group(1)}. {_markdown_inline(numbered.group(2))}", body_s))
            continue

        flowables.append(Paragraph(_markdown_inline(stripped), body_s))

    return flowables


def _parse_markdown_sections(text: str):
    sections = []
    current_title = "한줄 요약"
    current_lines = []

    for line in text.splitlines():
        heading = re.match(r"^#{1,3}\s+(.+)$", line.strip())
        if heading:
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = heading.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    return sections


def _markdown_to_flowables(text: str, heading_s: ParagraphStyle, body_s: ParagraphStyle):
    flowables = []
    for title, lines in _parse_markdown_sections(text):
        flowables.append(Paragraph(_markdown_inline(title), heading_s))
        flowables.extend(_markdown_lines_to_flowables(lines, body_s))
    return flowables


def _metric_card(title: str, value: str, status: str, value_s: ParagraphStyle, label_s: ParagraphStyle):
    palette = {
        "good": colors.HexColor("#ecfdf5"),
        "warn": colors.HexColor("#fffbeb"),
        "bad": colors.HexColor("#fff1f2"),
    }
    border = {
        "good": colors.HexColor("#a7f3d0"),
        "warn": colors.HexColor("#fde68a"),
        "bad": colors.HexColor("#fecdd3"),
    }
    card = Table(
        [[Paragraph(value, value_s)], [Paragraph(title, label_s)]],
        colWidths=[4.8 * cm],
    )
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), palette[status]),
        ("BOX", (0, 0), (-1, -1), 0.8, border[status]),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return card


def _coaching_cards(text: str, width: float, title_s: ParagraphStyle, body_s: ParagraphStyle):
    cards = []
    for title, lines in _parse_markdown_sections(text):
        content = [Paragraph(_markdown_inline(title), title_s)]
        content.extend(_markdown_lines_to_flowables(lines, body_s))
        card = Table([[content]], colWidths=[width])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.8, _BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        cards.append(KeepTogether([card, Spacer(1, 0.18 * cm)]))
    return cards


def _normalize_problem_frames(value):
    if not value:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = []

    frames = []
    for index, frame in enumerate(value if isinstance(value, list) else []):
        if isinstance(frame, str):
            frames.append({"type": None, "label": f"문제 장면 {index + 1}", "image": frame})
        elif isinstance(frame, dict) and frame.get("image"):
            frames.append({
                "type": frame.get("type"),
                "label": frame.get("label") or f"문제 장면 {index + 1}",
                "sec": frame.get("sec"),
                "score": frame.get("score"),
                "value": frame.get("value"),
                "image": frame.get("image"),
            })
    return frames


def _select_problem_frame(frames: list[dict], frame_type: str):
    typed = [frame for frame in frames if frame.get("type") == frame_type]
    if typed:
        return sorted(typed, key=lambda frame: float(frame.get("score") or 0), reverse=True)[0]

    legacy = [frame for frame in frames if not frame.get("type")]
    if frame_type == "gaze" and legacy:
        return legacy[0]
    if frame_type == "pose" and len(legacy) > 3:
        return legacy[3]
    return None


def _image_from_b64(data: str, max_width: float, max_height: float):
    if data.startswith("data:"):
        data = data.split(",", 1)[-1]
    raw = base64.b64decode(data)
    image_io = io.BytesIO(raw)
    reader = ImageReader(image_io)
    img_w, img_h = reader.getSize()
    scale = min(max_width / img_w, max_height / img_h)
    image_io.seek(0)
    return RLImage(image_io, width=img_w * scale, height=img_h * scale)


def _problem_frame_cards(frames: list[dict], width: float, title_s: ParagraphStyle, body_s: ParagraphStyle):
    selected = [
        ("시선 이탈 최대 장면", _select_problem_frame(frames, "gaze")),
        ("자세 기울어짐 최대 장면", _select_problem_frame(frames, "pose")),
    ]
    cards = []
    col_width = (width - 0.4 * cm) / 2

    for title, frame in selected:
        if not frame:
            continue
        try:
            img = _image_from_b64(frame["image"], col_width - 0.5 * cm, 4.2 * cm)
        except Exception:
            continue

        caption_bits = [frame.get("label") or title]
        if frame.get("value"):
            caption_bits.append(str(frame["value"]))
        if frame.get("sec") is not None:
            caption_bits.append(f"{frame['sec']}초")

        content = [
            Paragraph(title, title_s),
            img,
            Spacer(1, 0.12 * cm),
            Paragraph(" · ".join(caption_bits), body_s),
        ]
        card = Table([[content]], colWidths=[col_width])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.8, _BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        cards.append(card)

    if not cards:
        return []
    if len(cards) == 1:
        return [cards[0], Spacer(1, 0.3 * cm)]

    row = Table([cards], colWidths=[col_width, col_width])
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    return [row, Spacer(1, 0.3 * cm)]


def generate_report(record: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        topMargin=1.7 * cm, bottomMargin=1.7 * cm,
    )

    title_s = ParagraphStyle("T", fontName=_KR, fontSize=22, spaceAfter=6,
                              alignment=TA_CENTER, textColor=_NAVY)
    subtitle_s = ParagraphStyle("ST", fontName=_KR, fontSize=11, spaceAfter=4,
                                 alignment=TA_CENTER, textColor=_SLATE)
    section_s = ParagraphStyle("S", fontName=_KR, fontSize=15, spaceBefore=12, spaceAfter=8,
                                textColor=_NAVY, leading=20, wordWrap="CJK")
    card_title_s = ParagraphStyle("CT", fontName=_KR, fontSize=11.5, spaceAfter=6,
                                  textColor=_NAVY, leading=15, wordWrap="CJK")
    body_s = ParagraphStyle("B", fontName=_KR, fontSize=9.5, leading=15, textColor=_BODY,
                            wordWrap="CJK")
    metric_s = ParagraphStyle("M", fontName=_KR, fontSize=10, leading=15, textColor=_BODY)
    metric_value_s = ParagraphStyle("MV", fontName=_KR, fontSize=18, leading=22,
                                    textColor=_NAVY, wordWrap="CJK")
    metric_label_s = ParagraphStyle("ML", fontName=_KR, fontSize=8.5, leading=11,
                                    textColor=_SLATE, wordWrap="CJK")
    score_big_s = ParagraphStyle("SB", fontName=_KR, fontSize=52, alignment=TA_CENTER,
                                  spaceAfter=4, leading=60)
    score_label_s = ParagraphStyle("SL", fontName=_KR, fontSize=13, alignment=TA_CENTER,
                                    textColor=_SLATE)

    try:
        dt = datetime.fromisoformat(record.get("created_at", "").replace("Z", "+00:00"))
        date_str = dt.strftime("%Y년 %m월 %d일 %H:%M")
    except Exception:
        date_str = record.get("created_at", "")

    gaze = record.get("gaze_away_ratio", 0)
    tilt = record.get("shoulder_tilt_avg", 0)
    gestures = record.get("gesture_count", 0)
    coaching = record.get("coaching") or "코칭 없음"
    problem_frames = _normalize_problem_frames(record.get("problem_frames"))
    score_total = record.get("score_total")
    has_scores = score_total is not None

    gaze_status = "좋음" if gaze <= 0.15 else "주의" if gaze <= 0.3 else "개선 필요"
    tilt_status = "좋음" if tilt <= 8 else "주의" if tilt <= 15 else "개선 필요"
    gesture_status = "적절함" if 5 <= gestures <= 50 else "주의"

    metrics_text = (
        f"• 시선 이탈률: {gaze * 100:.0f}%  ({gaze_status})<br/>"
        f"• 어깨 기울기: {tilt:.1f}도  ({tilt_status})<br/>"
        f"• 제스처 횟수: {gestures}회  ({gesture_status})"
    )

    elapsed = record.get("elapsed_sec")
    goal = record.get("goal_sec")
    if elapsed and goal:
        def _fmt(s):
            return f"{int(s)//60}분 {int(s)%60}초"
        metrics_text += f"<br/>• 발표 시간: {_fmt(elapsed)} / 목표 {_fmt(goal)}"

    story = []

    # ── Page 1: 표지 ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("PresentationCoach", title_s))
    story.append(Paragraph("발표 분석 보고서", subtitle_s))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(date_str, subtitle_s))
    story.append(Spacer(1, 2.5 * cm))

    if has_scores:
        total_color = _score_color(score_total)
        story.append(Paragraph(
            f'<font color="{total_color.hexval()}">{score_total}</font>',
            score_big_s,
        ))
        story.append(Paragraph("종합 점수 (100점 만점)", score_label_s))
    else:
        story.append(Spacer(1, 1 * cm))

    story.append(PageBreak())

    # ── Page 2: 지표 + 차트 ──────────────────────────────────────────────────
    story.append(Paragraph("분석 지표", section_s))
    metric_cards = Table([[
        _metric_card("시선 이탈률", f"{gaze * 100:.0f}%", "good" if gaze <= 0.15 else "warn" if gaze <= 0.3 else "bad", metric_value_s, metric_label_s),
        _metric_card("어깨 기울기", f"{tilt:.1f}도", "good" if tilt <= 8 else "warn" if tilt <= 15 else "bad", metric_value_s, metric_label_s),
        _metric_card("제스처 횟수", f"{gestures}회", "good" if 5 <= gestures <= 50 else "warn", metric_value_s, metric_label_s),
    ]], colWidths=[doc.width / 3] * 3)
    metric_cards.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(metric_cards)
    story.append(Spacer(1, 0.35 * cm))

    chart_png = _make_chart(gaze, tilt, gestures)
    chart_img = RLImage(io.BytesIO(chart_png), width=12 * cm, height=5.8 * cm)
    story.append(chart_img)
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(metrics_text, metric_s))

    if has_scores:
        story.append(Paragraph("항목별 점수", section_s))

        scores_dict = {
            "score_gaze": record.get("score_gaze", 0),
            "score_pose": record.get("score_pose", 0),
            "score_gesture": record.get("score_gesture", 0),
            "score_time": record.get("score_time", 0),
        }
        score_chart_png = _make_score_chart(scores_dict)
        score_img = RLImage(io.BytesIO(score_chart_png), width=12 * cm, height=5.2 * cm)
        story.append(score_img)

        tbl_data = [
            ["항목", "점수", "가중치"],
            ["시선", f"{scores_dict['score_gaze']}점", "30%"],
            ["자세", f"{scores_dict['score_pose']}점", "25%"],
            ["제스처", f"{scores_dict['score_gesture']}점", "15%"],
            ["시간 관리", f"{scores_dict['score_time']}점", "30%"],
            ["종합", f"{score_total}점", "100%"],
        ]
        tbl = Table(tbl_data, colWidths=[5 * cm, 3 * cm, 3 * cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), _KR),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ede9fe")),
            ("FONTSIZE", (0, -1), (-1, -1), 11),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(Spacer(1, 0.3 * cm))
        story.append(tbl)

    story.append(PageBreak())

    # ── Page 3: AI 코칭 피드백 ───────────────────────────────────────────────
    evidence = _problem_frame_cards(problem_frames, doc.width, card_title_s, body_s)
    if evidence:
        story.append(Paragraph("주요 문제 장면", section_s))
        story.extend(evidence)

    story.append(Paragraph("AI 코칭 피드백", section_s))
    story.extend(_coaching_cards(coaching, doc.width, card_title_s, body_s))

    doc.build(story)
    buf.seek(0)
    return buf.read()
