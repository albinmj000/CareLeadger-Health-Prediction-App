"""Visual styling for the CareLedger dashboard (navy, teal, white, light grey)."""

from __future__ import annotations

from html import escape

import streamlit as st

NAVY = "#0B2545"
TEAL = "#0F9D94"
LIGHT_GREY = "#F2F5F9"

_CSS = f"""
<style>
  .block-container {{max-width: 1240px; padding-top: 1.6rem; padding-bottom: 3rem;}}
  h1, h2, h3, h4 {{color: {NAVY}; letter-spacing: -0.01em;}}

  [data-testid="stSidebar"] {{background: {NAVY};}}
  [data-testid="stSidebar"] * {{color: #E6EEF5;}}
  [data-testid="stSidebar"] hr {{border-color: rgba(255,255,255,.18);}}
  .brand {{display:flex; align-items:center; gap:.6rem; margin:.2rem 0 1rem 0;}}
  .brand .logo {{background:{TEAL}; width:2.2rem; height:2.2rem; border-radius:.7rem;
    display:flex; align-items:center; justify-content:center; font-size:1.2rem;}}
  .brand .name {{font-size:1.25rem; font-weight:700; color:#fff;}}
  .brand .tag {{font-size:.75rem; color:#9FB6C9;}}

  .hero {{padding:1.6rem 1.9rem; border-radius:18px; margin-bottom:1.3rem;
    background: linear-gradient(120deg, {NAVY} 0%, #12476B 60%, {TEAL} 135%);
    box-shadow: 0 8px 24px rgba(11,37,69,.18);}}
  .hero h1 {{margin:0 0 .3rem 0; color:#fff; font-size:2rem;}}
  .hero p {{margin:0; color:#CFE3EC; font-size:1rem;}}

  .kpi {{background:#fff; border:1px solid #E1E8F0; border-radius:16px;
    padding:1rem 1.15rem; box-shadow:0 2px 8px rgba(11,37,69,.05); height:100%;}}
  .kpi .icon {{width:2.3rem; height:2.3rem; border-radius:.7rem; display:flex;
    align-items:center; justify-content:center; background:{LIGHT_GREY};
    font-size:1.15rem; margin-bottom:.55rem;}}
  .kpi .label {{font-size:.8rem; color:#5B6B7C; text-transform:uppercase; letter-spacing:.05em;}}
  .kpi .value {{font-size:2rem; font-weight:700; color:{NAVY}; line-height:1.15;}}
  .kpi .note {{font-size:.78rem; color:#6B7A8A; margin-top:.2rem;}}

  .section-title {{display:flex; align-items:center; gap:.5rem; margin:1.4rem 0 .6rem 0;
    font-size:1.2rem; font-weight:700; color:{NAVY};}}
  .section-title .bar {{width:5px; height:1.3rem; background:{TEAL}; border-radius:3px;}}

  .empty {{text-align:center; padding:2.2rem 1rem; border:1.5px dashed #C5D2DF;
    border-radius:16px; background:{LIGHT_GREY}; color:#4A5B6C;}}
  .empty .emoji {{font-size:2.2rem;}}
  .empty .title {{font-weight:700; color:{NAVY}; margin:.3rem 0 .2rem 0;}}

  .notice {{border-left:4px solid {TEAL}; background:#EAF6F5; color:{NAVY};
    padding:.7rem 1rem; border-radius:8px; font-size:.9rem;}}
  .chip {{display:inline-block; padding:.15rem .65rem; border-radius:999px;
    font-size:.78rem; font-weight:600;}}
  .chip.ok {{background:#DDF3EF; color:#0A6B64;}}
  .chip.warn {{background:#FFF1D6; color:#8A5A00;}}

  .stButton > button, [data-testid="stFormSubmitButton"] > button {{
    border-radius:10px; font-weight:600; min-height:2.6rem;}}
  div[data-testid="stForm"] {{border:1px solid #E1E8F0; border-radius:16px;
    padding:1.2rem 1.3rem; background:#fff;}}
  div[data-testid="stDataFrame"] {{border:1px solid #E1E8F0; border-radius:12px;
    overflow-x:auto;}}
  .stTabs [data-baseweb="tab"] {{font-weight:600;}}

  @media (max-width: 640px) {{
    .block-container {{padding-left:.8rem; padding-right:.8rem;}}
    .hero {{padding:1.1rem 1.1rem;}}
    .hero h1 {{font-size:1.5rem;}}
    .kpi .value {{font-size:1.6rem;}}
    div[data-testid="stForm"] {{padding:.8rem;}}
  }}
</style>
"""


def inject_styles() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def brand() -> None:
    st.markdown(
        '<div class="brand"><div class="logo">🩺</div><div>'
        '<div class="name">CareLedger</div>'
        '<div class="tag">Patient health information</div></div></div>',
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="hero"><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def section(icon: str, title: str) -> None:
    st.markdown(
        f'<div class="section-title"><span class="bar"></span>'
        f"<span>{escape(icon)} {escape(title)}</span></div>",
        unsafe_allow_html=True,
    )


def kpi_card(icon: str, label: str, value: str, note: str) -> None:
    st.markdown(
        f'<div class="kpi"><div class="icon">{escape(icon)}</div>'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div>'
        f'<div class="note">{escape(note)}</div></div>',
        unsafe_allow_html=True,
    )


def empty_state(emoji: str, title: str, message: str) -> None:
    st.markdown(
        f'<div class="empty"><div class="emoji">{escape(emoji)}</div>'
        f'<div class="title">{escape(title)}</div><div>{escape(message)}</div></div>',
        unsafe_allow_html=True,
    )


def notice(message: str) -> None:
    st.markdown(f'<div class="notice">{escape(message)}</div>', unsafe_allow_html=True)


def chip(text: str, ok: bool) -> str:
    return f'<span class="chip {"ok" if ok else "warn"}">{escape(text)}</span>'
