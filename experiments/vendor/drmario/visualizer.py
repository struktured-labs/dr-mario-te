"""Interactive Dr. Mario game visualizer with playback controls."""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib import colors as mcolors
from typing import List, Dict, Any


def show_game_animation(frames: List[np.ndarray], rows=16, cols=8, interval=200):
    """
    Simple matplotlib animation of Dr. Mario gameplay.
    Works reliably in notebooks without ipywidgets.
    
    Args:
        frames: List of board state arrays
        rows: Board height
        cols: Board width
        interval: Milliseconds between frames
    """
    from matplotlib.animation import FuncAnimation
    from IPython.display import HTML
    
    viz = DrMarioVisualizer(rows, cols)
    fig, ax = plt.subplots(figsize=(5, 10))
    fig.patch.set_facecolor('#000000')
    
    def update(frame_idx):
        viz.render_frame(frames[frame_idx], ax=ax, 
                        title=f"Frame {frame_idx+1}/{len(frames)}")
        return ax,
    
    anim = FuncAnimation(fig, update, frames=len(frames), 
                        interval=interval, repeat=True, blit=False)
    plt.close()  # Don't show static figure
    return HTML(anim.to_jshtml())


def show_key_frames(frames: List[np.ndarray], rows=16, cols=8, n_frames=6):
    """
    Show evenly-spaced key frames in a grid.
    Reliable fallback that always works.
    
    Args:
        frames: List of board state arrays
        rows: Board height  
        cols: Board width
        n_frames: Number of frames to show
    """
    viz = DrMarioVisualizer(rows, cols)
    n_frames = min(n_frames, len(frames))
    
    # Calculate indices for evenly-spaced frames
    if n_frames == 1:
        indices = [0]
    else:
        indices = [int(i * (len(frames) - 1) / (n_frames - 1)) for i in range(n_frames)]
    
    # Create grid layout
    cols_grid = 3
    rows_grid = (n_frames + cols_grid - 1) // cols_grid
    
    fig, axes = plt.subplots(rows_grid, cols_grid, figsize=(4*cols_grid, 8*rows_grid))
    if rows_grid == 1 and cols_grid == 1:
        axes = np.array([[axes]])
    elif rows_grid == 1 or cols_grid == 1:
        axes = axes.reshape(rows_grid, cols_grid)
    
    axes = axes.flatten()
    
    for idx, frame_idx in enumerate(indices):
        grid = frames[frame_idx]
        viz.render_frame(grid, ax=axes[idx], 
                        title=f"Frame {frame_idx+1}/{len(frames)}")
    
    # Hide unused subplots
    for idx in range(len(indices), len(axes)):
        axes[idx].set_visible(False)
    
    plt.tight_layout()
    plt.show()
    print(f"\nShowing {n_frames} key frames from {len(frames)} total frames")


class DrMarioVisualizer:
    """Renders Dr. Mario board states with color-coded cells."""
    
    # Color scheme: 0=empty(black), 1=red, 2=blue, 3=yellow, 10+c=virus
    COLORS = {
        0: '#1a1a1a',   # empty (dark gray)
        1: '#ff4444',   # red capsule
        2: '#4444ff',   # blue capsule
        3: '#ffff44',   # yellow capsule
        11: '#aa0000',  # red virus (darker)
        12: '#0000aa',  # blue virus (darker)
        13: '#aaaa00',  # yellow virus (darker)
    }
    
    def __init__(self, rows=16, cols=8):
        self.rows = rows
        self.cols = cols
        
    def render_frame(self, grid: np.ndarray, ax=None, title: str = ""):
        """Render a single board state."""
        if ax is None:
            fig, ax = plt.subplots(figsize=(4, 8))
        else:
            ax.clear()
            
        # Set up the grid
        ax.set_xlim(0, self.cols)
        ax.set_ylim(0, self.rows)
        ax.set_aspect('equal')
        ax.invert_yaxis()
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Draw grid lines
        for i in range(self.rows + 1):
            ax.axhline(i, color='#333333', linewidth=0.5)
        for j in range(self.cols + 1):
            ax.axvline(j, color='#333333', linewidth=0.5)
        
        # Draw cells
        for r in range(self.rows):
            for c in range(self.cols):
                val = int(grid[r, c])
                if val == 0:
                    continue
                
                # Get color
                if val <= 3:
                    color = self.COLORS[val]
                    marker = 'o'  # capsule piece
                elif val >= 10:
                    color = self.COLORS[val]
                    marker = 'X'  # virus
                else:
                    color = '#666666'
                    marker = 's'
                
                # Draw cell
                rect = Rectangle((c, r), 1, 1, 
                               facecolor=color, 
                               edgecolor='#000000',
                               linewidth=1)
                ax.add_patch(rect)
                
                # Add marker for viruses
                if val >= 10:
                    ax.plot(c + 0.5, r + 0.5, marker, 
                           color='white', markersize=8, 
                           markeredgecolor='black', markeredgewidth=1)
        
        if title:
            ax.set_title(title, color='white', fontsize=10)
        ax.set_facecolor('#000000')
        
        return ax
    
    def create_rollout_frames(self, trajectory: List[Dict[str, Any]]) -> List[np.ndarray]:
        """Extract board states from trajectory for visualization."""
        frames = []
        for step_data in trajectory:
            if 'grid' in step_data:
                frames.append(step_data['grid'].copy())
        return frames


class InteractivePlayer:
    """Interactive playback widget for Dr. Mario games."""
    
    def __init__(self, frames: List[np.ndarray], rows=16, cols=8):
        self.frames = frames
        self.current_frame = 0
        self.playing = False
        self.speed = 1  # frames per update
        self.visualizer = DrMarioVisualizer(rows, cols)
        
    def show(self):
        """Display the interactive player in a notebook."""
        try:
            from ipywidgets import Button, IntSlider, HBox, VBox, Output, Play, IntText, interact
            from IPython.display import display, clear_output
        except ImportError:
            print("⚠️  ipywidgets not available. Showing static frames instead.")
            self._show_static()
            return
        
        # Set matplotlib backend
        import matplotlib
        matplotlib.use('module://matplotlib_inline.backend_inline')
        
        # Create output widget for the plot
        output = Output()
        
        # Create figure once
        self.fig, self.ax = plt.subplots(figsize=(5, 10))
        self.fig.patch.set_facecolor('#000000')
        
        # Frame slider
        frame_slider = IntSlider(
            value=0,
            min=0,
            max=len(self.frames) - 1,
            step=1,
            description='Frame:',
            continuous_update=False
        )
        
        # Speed control
        speed_slider = IntSlider(
            value=1,
            min=1,
            max=10,
            step=1,
            description='Speed:',
            continuous_update=True
        )
        
        # Play control
        play_button = Play(
            value=0,
            min=0,
            max=len(self.frames) - 1,
            step=1,
            interval=100,  # ms
            description="Press play",
            disabled=False
        )
        
        # Navigation buttons
        btn_first = Button(description='⏮ First', button_style='info')
        btn_back10 = Button(description='⏪ -10', button_style='info')
        btn_back1 = Button(description='◀ -1', button_style='info')
        btn_next1 = Button(description='▶ +1', button_style='info')
        btn_next10 = Button(description='⏩ +10', button_style='info')
        btn_last = Button(description='⏭ Last', button_style='info')
        
        # Event handlers
        def update_frame(change):
            self.current_frame = change['new']
            with output:
                clear_output(wait=True)
                self._render_current_frame()
                display(self.fig)
        
        def btn_first_click(b):
            frame_slider.value = 0
            play_button.value = 0
        
        def btn_back10_click(b):
            new_val = max(0, self.current_frame - 10)
            frame_slider.value = new_val
            play_button.value = new_val
        
        def btn_back1_click(b):
            new_val = max(0, self.current_frame - 1)
            frame_slider.value = new_val
            play_button.value = new_val
        
        def btn_next1_click(b):
            new_val = min(len(self.frames) - 1, self.current_frame + 1)
            frame_slider.value = new_val
            play_button.value = new_val
        
        def btn_next10_click(b):
            new_val = min(len(self.frames) - 1, self.current_frame + 10)
            frame_slider.value = new_val
            play_button.value = new_val
        
        def btn_last_click(b):
            new_val = len(self.frames) - 1
            frame_slider.value = new_val
            play_button.value = new_val
        
        def speed_change(change):
            self.speed = change['new']
            play_button.interval = max(10, int(100 / self.speed))
        
        # Link events
        frame_slider.observe(update_frame, names='value')
        play_button.observe(update_frame, names='value')
        speed_slider.observe(speed_change, names='value')
        
        btn_first.on_click(btn_first_click)
        btn_back10.on_click(btn_back10_click)
        btn_back1.on_click(btn_back1_click)
        btn_next1.on_click(btn_next1_click)
        btn_next10.on_click(btn_next10_click)
        btn_last.on_click(btn_last_click)
        
        # Initial render
        with output:
            self._render_current_frame()
            display(self.fig)
        
        # Layout
        nav_buttons = HBox([btn_first, btn_back10, btn_back1, btn_next1, btn_next10, btn_last])
        controls = VBox([
            HBox([play_button, speed_slider]),
            frame_slider,
            nav_buttons
        ])
        
        display(VBox([output, controls]))
    
    def _show_static(self):
        """Fallback: show key frames in a static grid."""
        n_frames = min(6, len(self.frames))
        indices = [int(i * (len(self.frames) - 1) / (n_frames - 1)) for i in range(n_frames)]
        
        fig, axes = plt.subplots(2, 3, figsize=(12, 16))
        axes = axes.flatten()
        
        for idx, frame_idx in enumerate(indices):
            grid = self.frames[frame_idx]
            self.visualizer.render_frame(grid, ax=axes[idx], 
                                        title=f"Frame {frame_idx+1}/{len(self.frames)}")
        
        plt.tight_layout()
        plt.show()
        print(f"\nShowing {n_frames} key frames from {len(self.frames)} total frames")
    
    def _render_current_frame(self):
        """Render the current frame."""
        if 0 <= self.current_frame < len(self.frames):
            grid = self.frames[self.current_frame]
            title = f"Frame {self.current_frame + 1} / {len(self.frames)}"
            self.visualizer.render_frame(grid, ax=self.ax, title=title)
