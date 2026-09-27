from __future__ import annotations
import numpy as np, torch, torch.nn as nn, torch.optim as optim
from dataclasses import dataclass
from .models import PolicyValueNet

@dataclass
class PPOConfig:
    gamma: float = 0.99
    lam: float = 0.95
    clip_ratio: float = 0.2
    pi_lr: float = 3e-4
    v_lr: float = 1e-3
    train_iters: int = 10
    minibatch: int = 256
    epochs: int = 50
    steps_per_epoch: int = 4096
    entropy_coef: float = 0.01
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    target_kl: float = 0.02

class PPOAgent:
    def __init__(self, obs_dim, n_actions, device="cpu", cfg: PPOConfig | None = None):
        self.cfg = cfg or PPOConfig()
        self.net = PolicyValueNet(obs_dim, n_actions).to(device)
        # Single optimizer for combined loss (bug fix #1, #2)
        self.opt = optim.Adam(self.net.parameters(), lr=self.cfg.pi_lr)
        self.device = device

    def act(self, obs, params, chaos):
        self.net.eval()
        with torch.no_grad():
            o = torch.as_tensor(obs, dtype=torch.float32, device=self.device).unsqueeze(0)
            p = torch.as_tensor(params, dtype=torch.float32, device=self.device).unsqueeze(0)
            temp = 1.0 + 2.0*chaos
            logits, v = self.net(o, p, temperature=temp)
            dist = torch.distributions.Categorical(logits=logits)
            a = dist.sample(); logp = dist.log_prob(a)
        return int(a.item()), float(v.item()), float(logp.item())

    def compute_logp(self, obs, params, acts, chaos):
        temp = 1.0 + 2.0*chaos
        logits, v = self.net(obs, params, temperature=temp)
        dist = torch.distributions.Categorical(logits=logits)
        return dist.log_prob(acts), dist.entropy(), v

    def update(self, buf, cfg: PPOConfig):
        obs = torch.as_tensor(buf["obs"], dtype=torch.float32, device=self.device)
        params = torch.as_tensor(buf["params"], dtype=torch.float32, device=self.device)
        act = torch.as_tensor(buf["act"], dtype=torch.long, device=self.device)
        adv = torch.as_tensor(buf["adv"], dtype=torch.float32, device=self.device)
        ret = torch.as_tensor(buf["ret"], dtype=torch.float32, device=self.device)
        logp_old = torch.as_tensor(buf["logp"], dtype=torch.float32, device=self.device)
        chaos = torch.as_tensor(buf["chaos"], dtype=torch.float32, device=self.device)

        self.net.train()
        N = obs.shape[0]
        idx = np.arange(N)
        for it in range(cfg.train_iters):
            np.random.shuffle(idx)
            kl_sum = 0.0; kl_count = 0
            for start in range(0, N, cfg.minibatch):
                j = idx[start:start+cfg.minibatch]
                o, p, a, adv_b, ret_b, logp_b, cz = obs[j], params[j], act[j], adv[j], ret[j], logp_old[j], chaos[j]
                new_logp, ent, v = self.compute_logp(o, p, a, cz)
                ratio = torch.exp(new_logp - logp_b)
                clip_adv = torch.clamp(ratio, 1-cfg.clip_ratio, 1+cfg.clip_ratio) * adv_b
                loss_pi = -(torch.min(ratio*adv_b, clip_adv)).mean()
                loss_v = ((v - ret_b)**2).mean()
                loss = loss_pi + cfg.vf_coef*loss_v - cfg.entropy_coef*ent.mean()

                # Approx KL (bug fix #5)
                with torch.no_grad():
                    approx_kl = (logp_b - new_logp).mean().item()
                kl_sum += approx_kl; kl_count += 1

                self.opt.zero_grad()
                loss.backward()
                # Gradient clipping (bug fix #4)
                torch.nn.utils.clip_grad_norm_(self.net.parameters(), cfg.max_grad_norm)
                self.opt.step()

            mean_kl = kl_sum / max(kl_count, 1)
            if mean_kl > cfg.target_kl:
                break

class TrajectoryBuffer:
    def __init__(self, obs_dim, steps):
        import numpy as np
        self.obs = np.zeros((steps, obs_dim), np.float32)
        self.params = np.zeros((steps, 4), np.float32)
        self.act = np.zeros((steps,), np.int64)
        self.rew = np.zeros((steps,), np.float32)
        self.val = np.zeros((steps,), np.float32)
        self.logp = np.zeros((steps,), np.float32)
        self.chaos = np.zeros((steps,), np.float32)
        self.ptr = 0

    def store(self, o, p, a, r, v, logp, chaos):
        i=self.ptr; self.obs[i]=o; self.params[i]=p; self.act[i]=a; self.rew[i]=r
        self.val[i]=v; self.logp[i]=logp; self.chaos[i]=chaos; self.ptr+=1

    def finish(self, gamma, lam, last_val=0.0):
        import numpy as np
        T=self.ptr; adv=np.zeros(T, np.float32); vals=self.val[:T]; rews=self.rew[:T]
        lastgaelam=0.0
        for t in reversed(range(T)):
            nextv = vals[t+1] if t+1<T else last_val
            delta = rews[t] + gamma*nextv - vals[t]
            lastgaelam = delta + gamma*lam*lastgaelam
            adv[t]=lastgaelam
        ret = adv + vals[:T]
        adv = (adv - adv.mean()) / (adv.std()+1e-8)
        return {"obs": self.obs[:T], "params": self.params[:T], "act": self.act[:T],
                "adv": adv, "ret": ret, "logp": self.logp[:T], "chaos": self.chaos[:T]}
