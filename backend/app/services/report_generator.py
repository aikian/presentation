import io
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image as RLImage, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

_MALGUN = Path("C:/Windows/Fonts/malgun.ttf")
if _MALGUN.exists():
    pdfmetrics.registerFont(TTFont("KR", str(_MALGUN)))
    fm.fontManager.addfont(str(_MALGUN))
    plt.rcParams["font.family"] = "Malgun Gothic"
    _KR = "KR"
else:
    _KR = "Helvetica"

_NAVY = colors.HexColor("#1e293b")
_SLATE = colors.HexColor("#64748b")
_BODY = colors.HexColor("#374151")
_INDIGO = colors.HexColor("#6366f1")
_GREEN = colors.HexColor("#22c55e")
_AMBER = colors.HexColor("#f59e0b")
_RED = colors.HexColor("#ef4444")


def _make_chart(gaze: float, tilt: float, gestures: int) -> bytes:
    labels = ["시선 이탈률 (%)", "어깨 기울기 (도)", "제스처 횟수 (회)"]
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
    labels = ["시선", "자세", "제스처", "시간"]
    keys = ["score_gaze", "score_pose", "score_gesture", "score_time"]
    values = [scores.get(k, 0) for k in keys]
    bar_colors = ["#22c55e" if v >= 70 else "#f59e0b" if v >= 50 else "#ef4444" for v in values]

    fig, ax = plt.subplots(figsize=(5.5, 2.2))
    bars = ax.bar(labels, values, color=bar_colors, width=0.5)
    ax.bar_label(bars, fmt="%d", padding=3, fontsize=10)
    ax.set_ylim(0, 115)
    ax.set_ylabel("점수", fontsize=9)
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


def generate_report(record: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
        topMargin=2.5 * cm, bottomMargin=2.5 * cm,
    )

    title_s = ParagraphStyle("T", fontName=_KR, fontSize=22, spaceAfter=6,
                              alignment=TA_CENTER, textColor=_NAVY)
    subtitle_s = ParagraphStyle("ST", fontName=_KR, fontSize=11, spaceAfter=4,
                                 alignment=TA_CENTER, textColor=_SLATE)
    section_s = ParagraphStyle("S", fontName=_KR, fontSize=13, spaceBefore=14, spaceAfter=6,
                                textColor=_NAVY, leading=18)
    body_s = ParagraphStyle("B", fontName=_KR, fontSize=10, leading=17, textColor=_BODY)
    metric_s = ParagraphStyle("M", fontName=_KR, fontSize=10, leading=15, textColor=_BODY)
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
    coaching = (record.get("coaching") or "코칭 없음").replace("\n", "<br/>")
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
    story.append(Paragraph("AI 코칭 피드백", section_s))
    story.append(Paragraph(coaching, body_s))

    doc.build(story)
    buf.seek(0)
    return buf.read()
