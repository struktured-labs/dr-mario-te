from __future__ import annotations
import torch, torch.nn as nn
import numpy as np

class FiLM(nn.Module):
    def __init__(self, hidden, cond_dim):
        super().__init__()
        self.fc = nn.Linear(cond_dim, hidden*2)
    def forward(self, x, cond):
        gb = self.fc(cond)
        gamma, beta = gb.chunk(2, dim=-1)
        return x*(1+gamma) + beta

class PolicyValueNet(nn.Module):
    def __init__(self, obs_dim, n_actions, cond_dim=4, hidden=256,
                 in_channels=11, board_h=16, board_w=8):
        super().__init__()
        # Derive in_channels from obs_dim if board dims are known, in case env config differs.
        if obs_dim != in_channels * board_h * board_w:
            assert obs_dim % (board_h * board_w) == 0, (
                f"obs_dim={obs_dim} not divisible by board_h*board_w={board_h*board_w}"
            )
            in_channels = obs_dim // (board_h * board_w)
        self.in_channels = in_channels
        self.board_h = board_h
        self.board_w = board_w
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=3, padding=1), nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, padding=1), nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, padding=1), nn.ReLU(),
        )
        conv_out = 64 * board_h * board_w
        self.fc = nn.Sequential(
            nn.Linear(conv_out, hidden), nn.ReLU(),
        )
        self.film = FiLM(hidden, cond_dim)
        self.pi = nn.Linear(hidden, n_actions)
        self.v = nn.Linear(hidden, 1)

    def _trunk(self, obs):
        # obs comes in flat as (B, C*H*W). Reshape back to (B, C, H, W).
        B = obs.shape[0]
        x = obs.view(B, self.in_channels, self.board_h, self.board_w)
        x = self.conv(x)
        x = x.view(B, -1)
        return self.fc(x)

    def forward(self, obs, cond, temperature=1.0):
        h = self._trunk(obs); h = self.film(h, cond)
        logits = self.pi(h); value = self.v(h).squeeze(-1)
        # Support temperature as: None | scalar (int/float) | torch.Tensor (B,) or (B,1) | numpy scalar
        if temperature is None:
            return logits, value
        # Convert to a tensor on the same device/dtype as logits for safe broadcasting
        if not torch.is_tensor(temperature):
            # handles Python/numpy scalars
            temp_t = torch.as_tensor(float(temperature), dtype=logits.dtype, device=logits.device)
        else:
            temp_t = temperature.to(dtype=logits.dtype, device=logits.device)
        # Clamp to avoid divide-by-zero and ensure correct shape for broadcasting
        temp_t = torch.clamp(temp_t, min=1e-6)
        if temp_t.dim() == 0:
            scale = temp_t
        else:
            # Expect shape (B,) or (B,1); expand to (B,1) for broadcasting over action dimension
            if temp_t.dim() == 1:
                temp_t = temp_t.unsqueeze(-1)
            scale = temp_t
        return logits / scale, value
