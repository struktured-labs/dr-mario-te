"""Matplotlib visualization for the *faithful* Dr. Mario engine.

Renders :class:`~drmario.faithful_game.FaithfulBoard` states so we can watch
agents play. Styling matches the existing toy ``visualizer.py`` (dark
background, colored cells, grid lines) but is adapted to the faithful board's
representation (``.color`` HxW int8 + separate ``.is_virus`` boolean mask)
rather than the toy's "10+c" virus encoding.

Pill halves vs. viruses are made visually distinct:

  * **Pill halves**: bright rounded cells in the base color.
  * **Viruses**: a *darker* shade of the same color drawn as a circular blob
    with two white "eyes" (and pupils) plus a dark outline -- unmistakably a
    little critter rather than a capsule fragment.

A headless Agg backend is forced at import time so this is safe to run on
servers / in tests without a display.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # headless: must precede pyplot import

import warnings
from typing import List, Optional, Sequence

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch

from .faithful_game import FaithfulBoard, EMPTY, RED, YELLOW, BLUE

# ---------------------------------------------------------------- color palette
# Base capsule colors are kept consistent with visualizer.py.
EMPTY_COLOR = "#1a1a1a"
GRID_COLOR = "#333333"
BG_COLOR = "#000000"

PILL_COLORS = {
    RED: "#ff4444",
    YELLOW: "#ffff44",
    BLUE: "#4444ff",
}
# Viruses: darker variants of the same hue so color identity is preserved while
# value/brightness signals "this is a virus, not a pill".
VIRUS_COLORS = {
    RED: "#aa0000",
    YELLOW: "#aaaa00",
    BLUE: "#0000aa",
}


def _as_board(board) -> FaithfulBoard:
    """Accept either a FaithfulBoard or a (color, is_virus) pair / dict snapshot.

    ``rollout_frames`` stores lightweight snapshots; this lets every renderer
    transparently consume them as well as live boards.
    """
    if isinstance(board, FaithfulBoard):
        return board
    if isinstance(board, dict):
        color = np.asarray(board["color"])
        is_virus = np.asarray(board["is_virus"])
    else:  # assume a (color, is_virus) tuple/list
        color, is_virus = board
        color = np.asarray(color)
        is_virus = np.asarray(is_virus)
    rows, cols = color.shape
    b = FaithfulBoard(rows, cols)
    b.color = color.astype(np.int8)
    b.is_virus = is_virus.astype(bool)
    return b


def render_board(board, ax=None, title: str = ""):
    """Draw a single :class:`FaithfulBoard` (or snapshot) onto ``ax``.

    Returns the axes used. Pill halves are rounded bright cells; viruses are
    darker blobs with eyes so the two are immediately distinguishable.
    """
    b = _as_board(board)
    rows, cols = b.rows, b.cols

    if ax is None:
        _, ax = plt.subplots(figsize=(cols * 0.55, rows * 0.55))
    else:
        ax.clear()

    ax.set_xlim(0, cols)
    ax.set_ylim(0, rows)
    ax.set_aspect("equal")
    ax.invert_yaxis()  # row 0 at the top, like the NES playfield
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_facecolor(BG_COLOR)

    # grid lines
    for i in range(rows + 1):
        ax.axhline(i, color=GRID_COLOR, linewidth=0.5)
    for j in range(cols + 1):
        ax.axvline(j, color=GRID_COLOR, linewidth=0.5)

    for r in range(rows):
        for c in range(cols):
            val = int(b.color[r, c])
            if val == EMPTY:
                continue
            if b.is_virus[r, c]:
                _draw_virus(ax, r, c, VIRUS_COLORS.get(val, "#888888"))
            else:
                _draw_pill_half(ax, r, c, PILL_COLORS.get(val, "#888888"))

    if title:
        ax.set_title(title, color="white", fontsize=10)
    return ax


def _draw_pill_half(ax, r: int, c: int, color: str) -> None:
    """A bright rounded square = one half of a capsule."""
    pad = 0.08
    box = FancyBboxPatch(
        (c + pad, r + pad),
        1 - 2 * pad,
        1 - 2 * pad,
        boxstyle="round,pad=0,rounding_size=0.28",
        facecolor=color,
        edgecolor="#000000",
        linewidth=1.0,
        mutation_aspect=1.0,
    )
    ax.add_patch(box)


def _draw_virus(ax, r: int, c: int, color: str) -> None:
    """A darker circular blob with two eyes = a virus (clearly not a pill)."""
    cx, cy = c + 0.5, r + 0.5
    # body
    ax.add_patch(
        Circle((cx, cy), 0.40, facecolor=color, edgecolor="#000000", linewidth=1.2)
    )
    # eyes (whites + pupils) -- the unmistakable "virus" tell
    eye_dx, eye_dy = 0.15, 0.06
    for sign in (-1, 1):
        ex = cx + sign * eye_dx
        ey = cy - eye_dy
        ax.add_patch(Circle((ex, ey), 0.105, facecolor="white", edgecolor="#000000", linewidth=0.6))
        ax.add_patch(Circle((ex, ey), 0.045, facecolor="#000000"))


def _frame_indices(n_total: int, n: int) -> List[int]:
    if n_total <= 0:
        return []
    n = max(1, min(n, n_total))
    if n == 1:
        return [n_total - 1]
    return [int(round(i * (n_total - 1) / (n - 1))) for i in range(n)]


def render_key_frames(boards: Sequence, n: int = 9, save_path: Optional[str] = None):
    """Grid of ``n`` evenly-spaced snapshots from ``boards``.

    Returns the matplotlib Figure. If ``save_path`` is given the figure is
    written there (and closed).
    """
    boards = list(boards)
    if not boards:
        raise ValueError("render_key_frames: empty board list")

    indices = _frame_indices(len(boards), n)
    n_show = len(indices)
    ncols = min(3, n_show)
    nrows = (n_show + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(3.2 * ncols, 5.5 * nrows))
    fig.patch.set_facecolor(BG_COLOR)
    axes = np.atleast_1d(axes).flatten()

    for slot, fi in enumerate(indices):
        render_board(boards[fi], ax=axes[slot], title=f"step {fi}/{len(boards) - 1}")
    for slot in range(n_show, len(axes)):
        axes[slot].set_visible(False)

    fig.tight_layout()
    if save_path is not None:
        fig.savefig(save_path, facecolor=BG_COLOR, dpi=110, bbox_inches="tight")
        plt.close(fig)
    return fig


def save_gif(boards: Sequence, path: str, fps: int = 8) -> str:
    """Write an animated GIF of ``boards`` to ``path``.

    Tries imageio first (fast, no matplotlib animation machinery), then
    matplotlib's PillowWriter. If both fail, falls back to writing a key-frames
    PNG next to ``path`` and prints a warning. Returns the path actually
    written (the GIF, or the PNG fallback).
    """
    boards = list(boards)
    if not boards:
        raise ValueError("save_gif: empty board list")

    # ----- attempt 1: imageio (render each frame to an RGB array) ------------
    try:
        import imageio.v2 as imageio  # type: ignore

        frames = [_board_to_rgb(b) for b in boards]
        imageio.mimsave(path, frames, fps=fps, loop=0)
        return path
    except Exception as e:  # imageio missing or failed -> try matplotlib
        warnings.warn(f"save_gif: imageio path unavailable ({e}); trying PillowWriter")

    # ----- attempt 2: matplotlib FuncAnimation + PillowWriter ---------------
    try:
        from matplotlib.animation import FuncAnimation, PillowWriter

        b0 = _as_board(boards[0])
        fig, ax = plt.subplots(figsize=(b0.cols * 0.55, b0.rows * 0.55))
        fig.patch.set_facecolor(BG_COLOR)

        def _update(i):
            render_board(boards[i], ax=ax, title=f"step {i}/{len(boards) - 1}")
            return (ax,)

        anim = FuncAnimation(fig, _update, frames=len(boards), blit=False)
        anim.save(path, writer=PillowWriter(fps=fps), savefig_kwargs={"facecolor": BG_COLOR})
        plt.close(fig)
        return path
    except Exception as e:  # final fallback: static key-frames PNG
        warnings.warn(
            f"save_gif: no working GIF writer ({e}); writing key-frames PNG fallback"
        )

    fallback = path
    if fallback.lower().endswith(".gif"):
        fallback = fallback[:-4] + "_keyframes.png"
    else:
        fallback = fallback + "_keyframes.png"
    render_key_frames(boards, n=9, save_path=fallback)
    return fallback


def _board_to_rgb(board) -> np.ndarray:
    """Render one board to an HxWx3 uint8 array (for imageio)."""
    b = _as_board(board)
    fig, ax = plt.subplots(figsize=(b.cols * 0.55, b.rows * 0.55))
    fig.patch.set_facecolor(BG_COLOR)
    render_board(b, ax=ax)
    fig.tight_layout(pad=0.2)
    fig.canvas.draw()
    # buffer_rgba works across matplotlib backends/versions; drop alpha.
    buf = np.asarray(fig.canvas.buffer_rgba())
    rgb = buf[..., :3].copy()
    plt.close(fig)
    return rgb


def _snapshot(board: FaithfulBoard) -> dict:
    """Lightweight copy of the rendered state (color + virus mask)."""
    return {"color": board.color.copy(), "is_virus": board.is_virus.copy()}


def rollout_frames(env, policy: str = "random", max_steps: int = 200, seed: int = 0) -> List[dict]:
    """Run one episode, collecting a board snapshot after each step.

    Returns a list of snapshot dicts (consumable by every renderer here). For
    ``policy="random"`` legal actions are sampled from ``env.action_masks()``.
    The initial (post-reset) board is included as the first frame.
    """
    if policy != "random":
        raise ValueError(f"rollout_frames: unsupported policy {policy!r}")

    rng = np.random.default_rng(seed)
    env.reset(seed=seed)
    frames = [_snapshot(env.board)]

    for _ in range(max_steps):
        mask = env.action_masks()
        legal = np.flatnonzero(mask)
        if legal.size == 0:
            break
        action = int(rng.choice(legal))
        _, _, terminated, truncated, _ = env.step(action)
        frames.append(_snapshot(env.board))
        if terminated or truncated:
            break

    return frames
