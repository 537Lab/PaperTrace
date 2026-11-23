"""Local synthetic preview for the E research-history panel.

FR-E-01/02, SEC-01. This is an optional developer entry point, never a public
application. It imports the reusable component absolutely from
:mod:`papertrace.reports.view`, keeps Streamlit imports inside functions so the
core package never needs Streamlit, and refuses to run unless the caller passes
an explicit ``--synthetic-input`` record file and an explicit ``--history-root``
directory. It never calls a model, never reads private papers, never issues a
real export grant and never pretends to be product assembly.

Run only on loopback, e.g.::

    streamlit run src/papertrace/reports/preview.py --server.address 127.0.0.1 \
        -- --synthetic-input <synthetic-record.json> --history-root <history-dir>
"""

from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Sequence
from pathlib import Path

from papertrace.reports import HistoryStore, InvalidRecord, ResearchRecord, parse_record
from papertrace.reports.view import render_reports_panel

__all__ = ["main", "parse_args"]

SYNTHETIC_WARNING = (
    "合成预览（synthetic preview）：输入是用户显式选择的合成记录，不是真实人审、"
    "真实模型输出或真实论文；本页面可以写入你指定的合成历史目录，"
    "但不授予发布权或导出许可。"
)
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost"})


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Require explicit synthetic input and history root; refuse implicit defaults."""
    parser = argparse.ArgumentParser(
        prog="papertrace-reports-preview",
        description="Local synthetic preview of the E research-history panel.",
    )
    parser.add_argument(
        "--synthetic-input",
        required=True,
        help="Path to a synthetic ResearchRecord JSON file you explicitly chose.",
    )
    parser.add_argument(
        "--history-root",
        required=True,
        help="Explicit directory for synthetic history records.",
    )
    return parser.parse_args(None if argv is None else list(argv))


def _load_pending(path: Path) -> ResearchRecord:
    """Parse a synthetic package through the closed envelope; never repair it."""
    try:
        raw = path.read_bytes()
    except OSError:
        raise InvalidRecord("synthetic input file is unreadable") from None
    return parse_record(raw)


def _configured_server_address() -> str | None:
    """Read the configured Streamlit server bind address, or ``None`` if unset.

    Only the Streamlit config API is consulted; this never binds a socket itself.
    Any failure or missing value is treated as unset so the caller fails closed.
    """
    try:
        st_config = importlib.import_module("streamlit").config
    except Exception:  # noqa: BLE001 - Streamlit availability is checked by caller
        return None
    try:
        address = st_config.get_option("server.address")
    except Exception:  # noqa: BLE001 - unknown option or config error fails closed
        return None
    return address if isinstance(address, str) else None


def _is_loopback(address: str | None) -> bool:
    """Fail closed: only an explicitly configured loopback host is accepted."""
    if address is None:
        return False
    return address.strip().lower() in LOOPBACK_HOSTS


def main(argv: Sequence[str] | None = None) -> int:
    """Render the panel inside Streamlit, or explain the local-only invocation."""
    try:
        st = importlib.import_module("streamlit")
    except Exception:  # noqa: BLE001 - Streamlit is an optional local convenience
        sys.stderr.write(
            "This preview needs a local Streamlit install; "
            "the core papertrace.reports package does not depend on it.\n"
        )
        return 2

    args = parse_args(argv)
    pending_path = Path(args.synthetic_input)
    history_root = Path(args.history_root)

    address = _configured_server_address()
    if not _is_loopback(address):
        st.error(
            "预览已拒绝运行：必须显式把 Streamlit server.address 配置为 127.0.0.1 "
            "或 localhost（当前未配置或非本机地址）。"
        )
        return 1

    st.warning(SYNTHETIC_WARNING)
    st.info(
        "本地合成预览：仅绑定本机回环地址运行；会写入你显式指定的合成历史目录，"
        "但不授予发布权或导出许可。公共入口由装配负责人提供，本文件不是产品应用。"
    )

    pending: ResearchRecord | None
    try:
        pending = _load_pending(pending_path)
    except InvalidRecord:
        st.error("合成输入无法通过校验，已阻止预览。")
        pending = None

    current_snapshot_id = (
        pending.snapshot.snapshot_id if pending is not None else None
    )
    render_reports_panel(
        st,
        store=HistoryStore(history_root),
        pending_record=pending,
        current_snapshot_id=current_snapshot_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
