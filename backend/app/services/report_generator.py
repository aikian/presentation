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

_FONT_PAIRS = [
    (Path("C:/Windows/Fonts/malgun.ttf"), Path("C:/Windows/Fonts/malgunbd.ttf")),
    (Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"), Path("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf")),
]
_MALGUN, _MALGUN_BOLD = next(
    ((regular, bold) for regular, bold in _FONT_PAIRS if regular.exists()),
    _FONT_PAIRS[0],
)
if _MALGUN.exists():
    pdfmetrics.registerFont(TTFont("KR", str(_MALGUN)))
    if _MALGUN_BOLD.exists():
        pdfmetrics.registerFont(TTFont("KR-Bold", str(_MALGUN_BOLD)))
    else:
        pdfmetrics.registerFont(TTFont("KR-Bold", str(_MALGUN)))
    pdfmetrics.registerFontFamily("KR", normal="KR", bold="KR-Bold", italic="KR", boldItalic="KR-Bold")
    fm.fontManager.addfont(str(_MALGUN))
    plt.rcParams["font.family"] = fm.FontProperties(fname=str(_MALGUN)).get_name()
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


def _make_chart(gaze, tilt, gestures, gesture_score=None) -> bytes:
    """지표 가로 막대. None(측정 실패)은 0으로 그리지 않고 뺀다."""
    labels = (
        ["시선 이탈률 (%)", "어깨 기울기 (도)", "제스처 빈도 (회/분)"]
        if _KR == "KR"
        else ["Gaze away (%)", "Shoulder tilt (deg)", "Gestures / min"]
    )
    triples = []
    if gaze is not None:
        triples.append((labels[0], round(gaze * 100, 1),
                        "#ef4444" if gaze > 0.3 else "#f59e0b" if gaze > 0.15 else "#22c55e"))
    if tilt is not None:
        triples.append((labels[1], round(tilt, 1),
                        "#ef4444" if tilt > 15 else "#f59e0b" if tilt > 8 else "#22c55e"))
    if gestures is not None:
        triples.append((labels[2], gestures,
                        "#94a3b8" if gesture_score is None else
                        "#22c55e" if gesture_score >= 70 else
                        "#f59e0b" if gesture_score >= 50 else "#ef4444"))
    if not triples:
        triples = [("측정 없음" if _KR == "KR" else "N/A", 0, "#94a3b8")]
    labels = [t[0] for t in triples]
    values = [t[1] for t in triples]
    fig, ax = plt.subplots(figsize=(5.5, 2.6))
    bars = ax.barh(labels, values, color=[t[2] for t in triples], height=0.45)
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
    # 측정하지 못한 항목(None)은 0점으로 그리지 않고 차트에서 뺀다.
    # 0은 "최악"이라는 뜻이라, 목표 시간을 안 정했을 뿐인데 시간 0점으로 보이면 오해를 부른다.
    all_labels = (["시선", "자세", "제스처", "음성", "시간"] if _KR == "KR"
                  else ["Gaze", "Pose", "Gesture", "Voice", "Time"])
    all_keys = ["score_gaze", "score_pose", "score_gesture", "score_voice", "score_time"]
    pairs = [(l, scores.get(k)) for l, k in zip(all_labels, all_keys) if scores.get(k) is not None]
    if not pairs:
        pairs = [("측정 없음" if _KR == "KR" else "N/A", 0)]
    labels = [p[0] for p in pairs]
    values = [p[1] for p in pairs]
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


def _fmt_detail(value, suffix: str = "", digits: int = 1) -> str:
    if value is None:
        return "측정 안 됨"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}{suffix}"
    return f"{value}{suffix}"


def _detail_table(rows: list[tuple[str, str]], width: float, body_s: ParagraphStyle):
    data = [
        [Paragraph(f"<b>{escape(str(label))}</b>", body_s), Paragraph(escape(str(value)), body_s)]
        for label, value in rows
    ]
    table = Table(data, colWidths=[width * 0.42, width * 0.58])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _KR),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _PANEL]),
        ("BOX", (0, 0), (-1, -1), 0.6, _BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, _BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _habit_count(section: dict, *paths: str) -> int:
    total = 0
    for path in paths:
        value = section.get(path) or []
        total += len(value) if isinstance(value, list) else 0
    return total


def _detail_appendix(details: dict, width: float, section_s: ParagraphStyle, body_s: ParagraphStyle):
    """한 번의 PDF 다운로드에 결과 화면의 모든 탭 요약을 포함한다."""
    if not isinstance(details, dict) or not details:
        return []

    summary = details.get("summary") or {}
    audio = (details.get("audio") or {}).get("summary") or {}
    habits = details.get("habits") or {}
    heatmap = details.get("x_gaze_heatmap") or {}
    rolemodel = details.get("x_rolemodel") or {}
    flow = [PageBreak(), Paragraph("상세 분석 · 전체 탭", section_s)]

    flow.append(Paragraph("시각 분석", section_s))
    smile = summary.get("smile_ratio")
    expression_change = summary.get("expression_change_std")
    visual_rows = [
        ("시선 이탈률", _fmt_detail(summary.get("gaze_away_ratio") * 100 if summary.get("gaze_away_ratio") is not None else None, "%")),
        ("어깨 기울기 평균", _fmt_detail(summary.get("posture_tilt_avg_deg"), "도")),
        ("제스처 빈도", _fmt_detail(summary.get("gesture_per_min"), "회/분", 2)),
        ("미소 비율", _fmt_detail(smile * 100 if smile is not None else None, "%")),
        ("표정 변화량", _fmt_detail(expression_change, "", 3)),
    ]
    flow.append(_detail_table(visual_rows, width, body_s))

    grid = heatmap.get("grid")
    if isinstance(grid, list) and len(grid) == 3 and all(isinstance(row, list) and len(row) == 3 for row in grid):
        labels = ["좌상", "상", "우상", "좌", "기준 시선", "우", "좌하", "하", "우하"]
        cells = []
        for label, value in zip(labels, [item for row in grid for item in row]):
            pct = _fmt_detail(value * 100 if isinstance(value, (int, float)) else None, "%")
            cells.append(Paragraph(f"<b>{escape(label)}</b><br/>{escape(pct)}", body_s))
        heatmap_table = Table([cells[:3], cells[3:6], cells[6:]], colWidths=[width / 3] * 3)
        heatmap_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _INDIGO_SOFT),
            ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#c7d2fe")),
            ("BOX", (0, 0), (-1, -1), 0.6, _BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.6, _BORDER),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        flow.extend([Spacer(1, 0.25 * cm), Paragraph("시선 히트맵", section_s), heatmap_table])
    else:
        flow.extend([
            Spacer(1, 0.25 * cm),
            Paragraph("시선 히트맵", section_s),
            Paragraph("얼굴을 충분히 검출하지 못해 시선 히트맵을 만들 수 없습니다.", body_s),
        ])

    flow.extend([
        Spacer(1, 0.2 * cm),
        Paragraph(
            "※ 자세 기울기는 카메라 화면의 어깨선을 기준으로 하므로 발표자가 비스듬히 서거나 "
            "카메라가 기울어진 경우 실제 자세보다 크게 측정될 수 있습니다.",
            body_s,
        ),
        Paragraph(
            "※ 기준 시선은 영상 내 시선의 중앙값입니다. 한 방향만 계속 본 영상에서는 기준 자체가 "
            "치우칠 수 있으므로 근거 장면과 함께 해석해야 합니다.",
            body_s,
        ),
    ])

    flow.append(PageBreak())
    flow.append(Paragraph("음성 분석", section_s))
    audio_rows = [
        ("말 속도", _fmt_detail(audio.get("spm_avg"), "음절/분")),
        ("군말", f"{audio.get('filler_count', 0)}회 ({_fmt_detail(audio.get('filler_per_min'), '회/분', 2)})"),
        ("침묵 비율", _fmt_detail(audio.get("silence_ratio") * 100 if audio.get("silence_ratio") is not None else None, "%")),
        ("2초 이상 끊김", f"{len((details.get('audio') or {}).get('silences') or [])}회"),
        ("억양 폭(표준편차)", _fmt_detail(audio.get("pitch_std"), " Hz")),
        ("억양 단조로움", _fmt_detail(audio.get("monotone_ratio") * 100 if audio.get("monotone_ratio") is not None else None, "%")),
    ]
    flow.append(_detail_table(audio_rows, width, body_s))
    filler_detail = audio.get("x_filler_detail") or {}
    filler_text = ", ".join(f"{key} {value}회" for key, value in filler_detail.items()) or "없음"
    flow.extend([
        Spacer(1, 0.2 * cm),
        Paragraph(f"<b>자주 쓴 군말:</b> {escape(filler_text)}", body_s),
        Paragraph(
            "※ 단독 ‘그’는 ‘그 이유는’처럼 정상적인 지시어 용법과 구분하기 어려워 군말 집계에서 제외합니다.",
            body_s,
        ),
    ])

    gaze_habit = habits.get("gaze") or {}
    posture_habit = habits.get("posture") or {}
    gesture_habit = habits.get("gesture") or {}
    filler_habit = habits.get("filler") or {}
    monotone_habit = habits.get("monotone") or {}
    flow.append(Paragraph("발표 습관 · 타임라인 요약", section_s))
    habit_rows = [
        ("반복 시선 습관", f"{_habit_count(gaze_habit.get('habits') or {}, 'repeated')}개"),
        ("지속 시선 습관", f"{_habit_count(gaze_habit.get('habits') or {}, 'persistent')}개"),
        ("자세 문제 구간", f"{_habit_count(posture_habit, 'segments')}개"),
        ("제스처 부족 구간", f"{_habit_count(gesture_habit, 'segments')}개"),
        ("반복 군말 종류", f"{_habit_count(filler_habit, 'repeated')}개"),
        ("단조로운 억양 구간", f"{_habit_count(monotone_habit, 'persistent')}개"),
    ]
    flow.append(_detail_table(habit_rows, width, body_s))

    metrics = rolemodel.get("metrics") or []
    if metrics:
        speaker = rolemodel.get("speaker") or {}
        speaker_title = speaker.get("name") or "선택 연사"
        flow.append(PageBreak())
        flow.append(Paragraph(f"연사 비교 · {escape(str(speaker_title))}", section_s))
        if speaker.get("source") or speaker.get("title"):
            source = " · ".join(str(item) for item in (speaker.get("source"), speaker.get("title")) if item)
            flow.append(Paragraph(escape(source), body_s))
            flow.append(Spacer(1, 0.2 * cm))
        role_rows = []
        for metric in metrics:
            label = metric.get("label") or metric.get("key") or "항목"
            value = metric.get("value")
            target = metric.get("target")
            verdict = metric.get("verdict") or ""
            role_rows.append((label, f"나 {_fmt_detail(value)} / 연사 {_fmt_detail(target)} · {verdict}"))
        flow.append(_detail_table(role_rows, width, body_s))

    return flow


def generate_report(record: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        topMargin=1.7 * cm, bottomMargin=1.7 * cm,
    )

    title_s = ParagraphStyle("T", fontName=_KR, fontSize=22, leading=30, spaceAfter=10,
                              alignment=TA_CENTER, textColor=_NAVY)
    subtitle_s = ParagraphStyle("ST", fontName=_KR, fontSize=11, leading=16, spaceAfter=4,
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
    gestures = ((record.get("details") or {}).get("summary") or {}).get("gesture_per_min")
    gesture_score = record.get("score_gesture")
    coaching = record.get("coaching") or "코칭 없음"
    problem_frames = _normalize_problem_frames(record.get("problem_frames"))
    score_total = record.get("score_total")
    has_scores = score_total is not None

    # 얼굴 미검출 등으로 지표가 None일 수 있다. 0으로 표기하면 "완벽/최악"으로 읽히므로
    # 측정하지 못했다는 사실을 그대로 적는다.
    if gaze is None:
        gaze_line = "• 시선 이탈률: 측정 안 됨 (얼굴 미검출)"
    else:
        gaze_status = "좋음" if gaze <= 0.15 else "주의" if gaze <= 0.3 else "개선 필요"
        gaze_line = f"• 시선 이탈률: {gaze * 100:.0f}%  ({gaze_status})"

    if tilt is None:
        tilt_line = "• 어깨 기울기: 측정 안 됨"
    else:
        tilt_status = "좋음" if tilt <= 8 else "주의" if tilt <= 15 else "개선 필요"
        tilt_line = f"• 어깨 기울기: {tilt:.1f}도  ({tilt_status})"

    if gestures is None:
        gesture_line = "• 제스처 횟수: 측정 안 됨"
    else:
        gesture_status = "점수 측정 안 됨" if gesture_score is None else "좋음" if gesture_score >= 70 else "주의" if gesture_score >= 50 else "개선 필요"
        gesture_line = f"• 제스처 빈도: {gestures:.2f}회/분  ({gesture_status})"

    metrics_text = gaze_line + "<br/>" + tilt_line + "<br/>" + gesture_line

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
        # 측정 실패(None)는 0%가 아니라 "측정 안 됨"으로 적는다
        _metric_card("시선 이탈률",
                     "측정 안 됨" if gaze is None else f"{gaze * 100:.0f}%",
                     "warn" if gaze is None else ("good" if gaze <= 0.15 else "warn" if gaze <= 0.3 else "bad"),
                     metric_value_s, metric_label_s),
        _metric_card("어깨 기울기",
                     "측정 안 됨" if tilt is None else f"{tilt:.1f}도",
                     "warn" if tilt is None else ("good" if tilt <= 8 else "warn" if tilt <= 15 else "bad"),
                     metric_value_s, metric_label_s),
        _metric_card("제스처 빈도",
                     "측정 안 됨" if gestures is None else f"{gestures:.2f}회/분",
                     "warn" if gesture_score is None else ("good" if gesture_score >= 70 else "warn" if gesture_score >= 50 else "bad"),
                     metric_value_s, metric_label_s),
    ]], colWidths=[doc.width / 3] * 3)
    metric_cards.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(metric_cards)
    story.append(Spacer(1, 0.35 * cm))

    chart_png = _make_chart(gaze, tilt, gestures, gesture_score)
    chart_img = RLImage(io.BytesIO(chart_png), width=12 * cm, height=5.8 * cm)
    story.append(chart_img)
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(metrics_text, metric_s))

    if has_scores:
        story.append(Paragraph("항목별 점수", section_s))

        scores_dict = {
            "score_gaze": record.get("score_gaze"),
            "score_pose": record.get("score_pose"),
            "score_gesture": record.get("score_gesture"),
            "score_voice": record.get("score_voice"),
            "score_time": record.get("score_time"),
        }
        score_chart_png = _make_score_chart(scores_dict)
        score_img = RLImage(io.BytesIO(score_chart_png), width=12 * cm, height=5.2 * cm)
        story.append(score_img)

        def _fmt_score(v):
            return "측정 안 됨" if v is None else f"{v}점"

        # 가중치는 AHP v2 (score_calculator.AHP_WEIGHTS와 같은 값).
        # 시간 점수는 목표 시간을 정한 발표에만 있고 종합점수에 들어가지 않는다.
        tbl_data = [
            ["항목", "점수", "가중치"],
            ["시선", _fmt_score(scores_dict["score_gaze"]), "35.1%"],
            ["자세", _fmt_score(scores_dict["score_pose"]), "18.9%"],
            ["제스처", _fmt_score(scores_dict["score_gesture"]), "10.9%"],
            ["음성", _fmt_score(scores_dict["score_voice"]), "35.1%"],
            ["시간 관리", _fmt_score(scores_dict["score_time"]), "별도"],
            ["종합", _fmt_score(score_total), "100%"],
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
    story.append(Paragraph("AI 코칭 피드백", section_s))
    story.extend(_coaching_cards(coaching, doc.width, card_title_s, body_s))

    evidence = _problem_frame_cards(problem_frames, doc.width, card_title_s, body_s)
    if evidence:
        story.append(PageBreak())
        story.append(Paragraph("근거 장면 · 부록", section_s))
        story.extend(evidence)

    story.extend(_detail_appendix(record.get("details") or {}, doc.width, section_s, body_s))

    doc.build(story)
    buf.seek(0)
    return buf.read()
